"""
Fine-tune FunctionGemma-270M for Aegis privacy classification.
Follows the official Google FunctionGemma fine-tuning notebook approach:
  https://ai.google.dev/gemma/docs/functiongemma/finetuning-with-functiongemma

Uses plain transformers + TRL SFTTrainer (no unsloth) with the tokenizer's
apply_chat_template, which natively handles FunctionGemma's special tokens.

Usage:
    python train.py                          # train from dataset.jsonl
    python train.py --dataset my_data.jsonl  # custom dataset path
    python train.py --epochs 8               # override epochs
"""

import argparse
import json
import os

# Load .env file for API keys and environment variables
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import torch
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from trl import SFTConfig, SFTTrainer


# ── Config ──────────────────────────────────────────────────────────────────

MODEL_NAME = (
    "unsloth/functiongemma-270m-it"  # Mirrors google/functiongemma-270m-it (no gating)
)
MAX_SEQ_LENGTH = 512
OUTPUT_DIR = "./aegis-adapter"

# Hyperparameters from the official Google notebook, adapted for our dataset:
# - 8 epochs (notebook used 8 for 20-sample dataset; fine for 200 too)
# - lr=5e-5 (notebook value, constant scheduler)
# - batch=4, no gradient checkpointing (incompatible with KV-cache)
TRAINING_DEFAULTS = {
    "num_train_epochs": 8,
    "per_device_train_batch_size": 4,
    "gradient_checkpointing": False,  # Incompatible with KV-cache
    "optim": "adamw_torch_fused",  # Fused optimizer for speed on A100
    "logging_steps": 5,
    "eval_strategy": "epoch",
    "learning_rate": 5e-5,
    "lr_scheduler_type": "constant",  # Constant LR as per notebook
    "report_to": "none",  # Disable wandb/tensorboard by default
    "seed": 42,
    "dataloader_num_workers": 0,
}


# ── Load and prepare dataset ─────────────────────────────────────────────────


def load_dataset_from_jsonl(path: str) -> dict:
    """Load dataset.jsonl and return train/test split in the format expected
    by SFTTrainer with apply_chat_template.

    Each example in dataset.jsonl already has:
      - messages: [{role: system, content: ...}, {role: user, content: ...}]
      - tools: [list of tool definitions]
      - expected_tool_call: {name: ..., arguments: {...}}

    We convert to the format used by the Google notebook:
      - messages: [developer turn, user turn, assistant tool_calls turn]
      - tools: [list of tool definitions]
    """
    examples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)

            system_content = raw["messages"][0]["content"]
            user_content = raw["messages"][1]["content"]
            tool_call = raw["expected_tool_call"]
            tools = raw["tools"]

            # Convert to the apply_chat_template format (matching notebook)
            example = {
                "messages": [
                    {"role": "developer", "content": system_content},
                    {"role": "user", "content": user_content},
                    {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "type": "function",
                                "function": {
                                    "name": tool_call["name"],
                                    "arguments": tool_call["arguments"],
                                },
                            }
                        ],
                    },
                ],
                "tools": tools,  # Keep the full {"type":"function","function":{...}} wrapper as the template expects it
            }
            examples.append(example)

    print(f"Loaded {len(examples)} examples from {path}")
    return examples


# ── Main ────────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Fine-tune FunctionGemma for Aegis")
    parser.add_argument(
        "--dataset", default="dataset.jsonl", help="Path to dataset.jsonl"
    )
    parser.add_argument(
        "--epochs", type=int, default=None, help="Override number of epochs"
    )
    parser.add_argument(
        "--batch-size", type=int, default=None, help="Override batch size"
    )
    parser.add_argument("--lr", type=float, default=None, help="Override learning rate")
    parser.add_argument(
        "--output", default=OUTPUT_DIR, help="Output directory for fine-tuned model"
    )
    args = parser.parse_args()

    # Resolve dataset path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = (
        os.path.join(script_dir, args.dataset)
        if not os.path.isabs(args.dataset)
        else args.dataset
    )

    if not os.path.exists(dataset_path):
        print(f"ERROR: Dataset not found at {dataset_path}")
        print("Run generate_dataset.py first to create the dataset.")
        return

    # ── 1. Load model and tokenizer ────────────────────────────────────
    print(f"Loading {MODEL_NAME}...")
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype="auto",  # Auto-selects bf16 on A100
        device_map="auto",  # Single GPU (CUDA_VISIBLE_DEVICES controls which)
        attn_implementation="eager",  # Required for FunctionGemma (no flash attn)
    )
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    print(f"Device: {model.device}")
    print(f"DType: {model.dtype}")
    total_params = sum(p.numel() for p in model.parameters())
    print(f"Total params: {total_params:,}")

    # ── 2. Load and split dataset ───────────────────────────────────────
    all_examples = load_dataset_from_jsonl(dataset_path)

    # Show a sample of the formatted prompt to verify correctness
    sample = all_examples[0]
    sample_text = tokenizer.apply_chat_template(
        sample["messages"],
        tools=sample["tools"],
        add_generation_prompt=False,
        tokenize=False,
    )
    print("\n── Sample formatted prompt ──")
    print(sample_text[:600])
    print("── End sample ──\n")

    # 80/20 train/test split
    split_idx = int(len(all_examples) * 0.8)
    train_examples = all_examples[:split_idx]
    test_examples = all_examples[split_idx:]

    train_dataset = Dataset.from_list(train_examples)
    test_dataset = Dataset.from_list(test_examples)

    print(f"Train: {len(train_dataset)} | Test: {len(test_dataset)}")

    # ── 3. Training config ──────────────────────────────────────────────
    torch_dtype = model.dtype
    training_args = TRAINING_DEFAULTS.copy()

    # Set precision flags based on actual model dtype
    training_args["fp16"] = torch_dtype == torch.float16
    training_args["bf16"] = torch_dtype == torch.bfloat16

    if args.epochs:
        training_args["num_train_epochs"] = args.epochs
    if args.batch_size:
        training_args["per_device_train_batch_size"] = args.batch_size
    if args.lr:
        training_args["learning_rate"] = args.lr

    sft_config = SFTConfig(
        output_dir=args.output,
        max_length=MAX_SEQ_LENGTH,
        packing=False,  # Packing is incompatible with apply_chat_template
        **training_args,
    )

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=train_dataset,
        eval_dataset=test_dataset,
        processing_class=tokenizer,  # Newer TRL API (replaces tokenizer=)
    )

    # ── 4. Train ─────────────────────────────────────────────────────────
    print("\nStarting training...")
    trainer.train()

    # ── 5. Save model ─────────────────────────────────────────────────────
    print(f"\nSaving fine-tuned model to {args.output}...")
    trainer.save_model()
    tokenizer.save_pretrained(args.output)
    print("Done!")

    # ── 6. Quick sanity check ─────────────────────────────────────────────
    print("\n── Sanity check: inference on test prompts ──")
    model.eval()

    test_prompts = [
        {
            "summary": "This is a public README file for an open-source Python library. It describes installation instructions and usage examples. No sensitive information found.",
            "expected": "classify_safe",
        },
        {
            "summary": "CSV export containing 500 customer records with full names, email addresses, phone numbers, and home addresses. Multiple SSN fields detected.",
            "expected": "flag_pii",
        },
        {
            "summary": "Configuration file containing AWS_SECRET_ACCESS_KEY, database connection strings with passwords, and Stripe API keys in plaintext.",
            "expected": "block_transfer",
        },
        {
            "summary": "Document titled 'Project Nexus - Q3 Acquisition Strategy'. Contains board-level discussion of potential M&A targets and confidential valuation estimates.",
            "expected": "request_permission",
        },
    ]

    # Reuse the tools from the dataset
    sample_tools = all_examples[0]["tools"]
    system_msg = all_examples[0]["messages"][0]["content"]

    success = 0
    for item in test_prompts:
        messages = [
            {"role": "developer", "content": system_msg},
            {"role": "user", "content": f"File summary:\n{item['summary']}"},
        ]
        inputs = tokenizer.apply_chat_template(
            messages,
            tools=sample_tools,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        )
        with torch.no_grad():
            out = model.generate(
                **inputs.to(model.device),
                pad_token_id=tokenizer.eos_token_id,
                max_new_tokens=128,
                temperature=0.1,
                do_sample=False,
            )
        response = tokenizer.decode(
            out[0][len(inputs["input_ids"][0]) :],
            skip_special_tokens=False,
        )
        expected = item["expected"]
        ok = expected in response
        status = "OK" if ok else "MISS"
        if ok:
            success += 1
        print(f"  [{status}] Expected: {expected} | Got: {response[:100].strip()}")

    print(f"\nSanity check: {success}/{len(test_prompts)} passed")
    print(f"\nModel saved to: {args.output}/")
    print("Next steps:")
    print("  1. Download the model folder")
    print("  2. On your Mac, run:")
    print(f"     cactus convert {args.output} ./aegis-functiongemma")
    print("  3. Update FUNCTIONGEMMA_PATH in aegis.py")


if __name__ == "__main__":
    main()

