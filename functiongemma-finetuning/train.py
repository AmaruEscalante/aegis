"""
Fine-tune FunctionGemma-270M for Aegis privacy classification.
Run on Google Colab with T4/A100 GPU.

Usage:
    python train.py                          # train from dataset.jsonl
    python train.py --dataset my_data.jsonl  # custom dataset path
    python train.py --epochs 5               # override epochs
"""

import argparse
import json
import os

from datasets import Dataset
from trl import SFTTrainer, SFTConfig
from unsloth import FastLanguageModel


# ── Config ──────────────────────────────────────────────────────────────────

MODEL_NAME = "google/functiongemma-2b-it"
MAX_SEQ_LENGTH = 512
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
OUTPUT_DIR = "./aegis-adapter"

TRAINING_DEFAULTS = {
    "num_train_epochs": 2,
    "per_device_train_batch_size": 4,
    "gradient_accumulation_steps": 4,
    "learning_rate": 2e-4,
    "warmup_steps": 10,
    "weight_decay": 0.01,
    "lr_scheduler_type": "cosine",
    "logging_steps": 5,
    "save_steps": 50,
    "fp16": True,
    "seed": 42,
}


# ── Format examples into FunctionGemma chat template ────────────────────────

def format_tool_call(tool_call: dict) -> str:
    """Format a tool call into FunctionGemma's special token format.

    Example output:
        call:classify_safe{reason: <escape>no sensitive data<escape>}
    """
    name = tool_call["name"]
    args = tool_call["arguments"]
    # Format arguments as key: <escape>value<escape> pairs
    arg_parts = []
    for key, value in args.items():
        arg_parts.append(f"{key}: <escape>{value}<escape>")
    args_str = ", ".join(arg_parts)
    return f"call:{name}{{{args_str}}}"


def format_example(example: dict) -> dict:
    """Convert a dataset example into FunctionGemma's training text format.

    Input format (from dataset.jsonl):
        {
            "messages": [{"role": "system", ...}, {"role": "user", ...}],
            "tools": [...],
            "expected_tool_call": {"name": "...", "arguments": {...}},
            "category": "..."
        }

    Output format:
        <bos><start_of_turn>user
        You are a privacy classifier. Based on the file summary, call the correct tool.

        File summary:
        {summary}
        <end_of_turn>
        <start_of_turn>model
        <start_function_call>call:classify_safe{reason: <escape>...<escape>}<end_function_call>
        <end_of_turn>
    """
    system_msg = example["messages"][0]["content"]
    user_msg = example["messages"][1]["content"]
    tool_call_str = format_tool_call(example["expected_tool_call"])

    # FunctionGemma merges system prompt into the user turn
    text = (
        f"<bos><start_of_turn>user\n"
        f"{system_msg}\n\n"
        f"{user_msg}\n"
        f"<end_of_turn>\n"
        f"<start_of_turn>model\n"
        f"<start_function_call>{tool_call_str}<end_function_call>\n"
        f"<end_of_turn>"
    )

    return {"text": text}


# ── Load dataset ────────────────────────────────────────────────────────────

def load_dataset(path: str) -> Dataset:
    """Load dataset.jsonl and format for training."""
    examples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            formatted = format_example(raw)
            examples.append(formatted)

    print(f"Loaded {len(examples)} examples from {path}")

    # Show a sample
    print("\n── Sample training text ──")
    print(examples[0]["text"])
    print("── End sample ──\n")

    return Dataset.from_list(examples)


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Fine-tune FunctionGemma for Aegis")
    parser.add_argument("--dataset", default="dataset.jsonl", help="Path to dataset.jsonl")
    parser.add_argument("--epochs", type=int, default=None, help="Override number of epochs")
    parser.add_argument("--batch-size", type=int, default=None, help="Override batch size")
    parser.add_argument("--lr", type=float, default=None, help="Override learning rate")
    parser.add_argument("--output", default=OUTPUT_DIR, help="Output directory for adapter")
    args = parser.parse_args()

    # Resolve dataset path relative to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = os.path.join(script_dir, args.dataset) if not os.path.isabs(args.dataset) else args.dataset

    if not os.path.exists(dataset_path):
        print(f"ERROR: Dataset not found at {dataset_path}")
        print("Run generate_dataset.py first to create the dataset.")
        return

    # ── 1. Load model with Unsloth ──────────────────────────────────────
    print(f"Loading {MODEL_NAME} with Unsloth...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        load_in_4bit=True,
    )

    # ── 2. Add LoRA adapters ────────────────────────────────────────────
    print("Adding LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        bias="none",
        use_gradient_checkpointing="unsloth",
    )

    # Print trainable params
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    print(f"Trainable: {trainable:,} / {total:,} ({100 * trainable / total:.2f}%)")

    # ── 3. Load dataset ─────────────────────────────────────────────────
    dataset = load_dataset(dataset_path)

    # ── 4. Training config ──────────────────────────────────────────────
    training_args = TRAINING_DEFAULTS.copy()
    if args.epochs:
        training_args["num_train_epochs"] = args.epochs
    if args.batch_size:
        training_args["per_device_train_batch_size"] = args.batch_size
    if args.lr:
        training_args["learning_rate"] = args.lr

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        args=SFTConfig(
            output_dir=args.output,
            dataset_text_field="text",
            max_seq_length=MAX_SEQ_LENGTH,
            packing=True,
            **training_args,
        ),
    )

    # ── 5. Train ────────────────────────────────────────────────────────
    print("\nStarting training...")
    stats = trainer.train()
    print(f"\nTraining complete!")
    print(f"  Total steps: {stats.global_step}")
    print(f"  Training loss: {stats.training_loss:.4f}")

    # ── 6. Save adapter ────────────────────────────────────────────────
    print(f"\nSaving LoRA adapter to {args.output}...")
    model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    print("Done!")

    # ── 7. Quick sanity check ───────────────────────────────────────────
    print("\n── Sanity check: inference on a test prompt ──")
    FastLanguageModel.for_inference(model)

    test_prompts = [
        "File summary:\nThis is a public README file for an open-source Python library. It describes installation instructions and usage examples. No sensitive information found.",
        "File summary:\nCSV export containing 500 customer records with full names, email addresses, phone numbers, and home addresses. Multiple SSN fields detected.",
        "File summary:\nConfiguration file containing AWS_SECRET_ACCESS_KEY, database connection strings with passwords, and Stripe API keys in plaintext.",
    ]
    expected = ["classify_safe", "flag_pii", "block_transfer"]

    for prompt, exp in zip(test_prompts, expected):
        input_text = (
            f"<bos><start_of_turn>user\n"
            f"You are a privacy classifier. Based on the file summary, call the correct tool.\n\n"
            f"{prompt}\n"
            f"<end_of_turn>\n"
            f"<start_of_turn>model\n"
        )
        inputs = tokenizer(input_text, return_tensors="pt").to(model.device)
        outputs = model.generate(**inputs, max_new_tokens=64, temperature=0.1)
        result = tokenizer.decode(outputs[0], skip_special_tokens=False)
        # Extract just the model's response
        model_response = result.split("<start_of_turn>model\n")[-1].split("<end_of_turn>")[0].strip()
        status = "OK" if exp in model_response else "MISS"
        print(f"  [{status}] Expected: {exp} | Got: {model_response[:80]}")

    print(f"\nAdapter saved to: {args.output}/")
    print("Next steps:")
    print("  1. Download the adapter folder")
    print("  2. On your Mac, run:")
    print(f"     cactus convert google/functiongemma-270m-it ./aegis-functiongemma --lora {args.output}")
    print("  3. Update FUNCTIONGEMMA_PATH in aegis.py")


if __name__ == "__main__":
    main()
