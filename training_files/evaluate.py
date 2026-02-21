"""
Evaluate a fine-tuned FunctionGemma model on the held-out test split.
Produces per-class precision, recall, F1, and macro/weighted averages.

Usage:
    python evaluate.py                              # evaluate aegis-adapter on dataset.jsonl
    python evaluate.py --model ./aegis-adapter      # explicit model path
    python evaluate.py --model unsloth/functiongemma-270m-it  # evaluate base (before finetune)
    python evaluate.py --dataset dataset.jsonl --split test   # test split (default)
    python evaluate.py --split all                            # evaluate on all examples
"""

import argparse
import json
import os
import random
from collections import defaultdict

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

LABELS = ["classify_safe", "flag_pii", "block_transfer", "request_permission"]


def load_examples(path: str, split: str, seed: int = 42) -> list:
    """Load and optionally split examples from dataset.jsonl."""
    examples = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            examples.append(raw)

    if split == "all":
        return examples

    # Deterministic 80/20 split (must match train.py)
    random.seed(seed)
    # Don't shuffle here — use index split like train.py does
    split_idx = int(len(examples) * 0.8)
    if split == "train":
        return examples[:split_idx]
    else:  # test
        return examples[split_idx:]


def predict(model, tokenizer, example: dict, tools: list, system_msg: str) -> str:
    """Run inference and return the predicted tool name (or 'invalid')."""
    messages = [
        {"role": "developer", "content": system_msg},
        {"role": "user", "content": example["messages"][1]["content"]},
    ]
    inputs = tokenizer.apply_chat_template(
        messages,
        tools=tools,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors="pt",
    )
    with torch.no_grad():
        out = model.generate(
            **inputs.to(model.device),
            pad_token_id=tokenizer.eos_token_id,
            max_new_tokens=128,
            do_sample=False,
        )
    response = tokenizer.decode(
        out[0][len(inputs["input_ids"][0]) :],
        skip_special_tokens=False,
    )
    # Extract the first tool call name from the response
    for label in LABELS:
        if f"call:{label}" in response:
            return label
    return "invalid"


def compute_metrics(y_true: list, y_pred: list, labels: list) -> dict:
    """Compute per-class and macro/weighted precision, recall, F1."""
    tp = defaultdict(int)
    fp = defaultdict(int)
    fn = defaultdict(int)

    for true, pred in zip(y_true, y_pred):
        if true == pred:
            tp[true] += 1
        else:
            fp[pred] += 1
            fn[true] += 1

    results = {}
    for label in labels:
        p = tp[label] / (tp[label] + fp[label]) if (tp[label] + fp[label]) > 0 else 0.0
        r = tp[label] / (tp[label] + fn[label]) if (tp[label] + fn[label]) > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        support = tp[label] + fn[label]
        results[label] = {"precision": p, "recall": r, "f1": f1, "support": support}

    # Macro average
    macro_p = sum(v["precision"] for v in results.values()) / len(labels)
    macro_r = sum(v["recall"] for v in results.values()) / len(labels)
    macro_f1 = sum(v["f1"] for v in results.values()) / len(labels)

    # Weighted average
    total = sum(v["support"] for v in results.values())
    weighted_p = (
        sum(v["precision"] * v["support"] for v in results.values()) / total
        if total
        else 0
    )
    weighted_r = (
        sum(v["recall"] * v["support"] for v in results.values()) / total
        if total
        else 0
    )
    weighted_f1 = (
        sum(v["f1"] * v["support"] for v in results.values()) / total if total else 0
    )

    # Overall accuracy
    accuracy = sum(tp.values()) / len(y_true) if y_true else 0.0

    results["macro avg"] = {
        "precision": macro_p,
        "recall": macro_r,
        "f1": macro_f1,
        "support": total,
    }
    results["weighted avg"] = {
        "precision": weighted_p,
        "recall": weighted_r,
        "f1": weighted_f1,
        "support": total,
    }
    results["accuracy"] = accuracy

    return results


def print_report(metrics: dict, labels: list):
    """Print a classification report in sklearn style."""
    print(
        f"\n{'':>22}  {'precision':>9}  {'recall':>9}  {'f1-score':>9}  {'support':>7}"
    )
    print()
    for label in labels:
        m = metrics[label]
        print(
            f"  {label:>20}  {m['precision']:>9.4f}  {m['recall']:>9.4f}  {m['f1']:>9.4f}  {m['support']:>7}"
        )
    print()
    for avg in ["macro avg", "weighted avg"]:
        m = metrics[avg]
        print(
            f"  {avg:>20}  {m['precision']:>9.4f}  {m['recall']:>9.4f}  {m['f1']:>9.4f}  {m['support']:>7}"
        )
    print()
    print(
        f"  {'accuracy':>20}  {'':>9}  {'':>9}  {metrics['accuracy']:>9.4f}  {metrics['weighted avg']['support']:>7}"
    )


def main():
    parser = argparse.ArgumentParser(description="Evaluate FunctionGemma for Aegis")
    parser.add_argument(
        "--model", default="./aegis-adapter", help="Model path or HF model ID"
    )
    parser.add_argument(
        "--dataset", default="dataset.jsonl", help="Path to dataset.jsonl"
    )
    parser.add_argument(
        "--split",
        default="test",
        choices=["train", "test", "all"],
        help="Which split to evaluate",
    )
    parser.add_argument("--verbose", action="store_true", help="Print every prediction")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_path = (
        os.path.join(script_dir, args.dataset)
        if not os.path.isabs(args.dataset)
        else args.dataset
    )
    model_path = (
        os.path.join(script_dir, args.model)
        if args.model.startswith("./") and not os.path.isabs(args.model)
        else args.model
    )

    print(f"Model : {model_path}")
    print(f"Data  : {dataset_path} [{args.split}]")

    # Load model
    print("\nLoading model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        dtype="auto",
        device_map="auto",
        attn_implementation="eager",
    )
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model.eval()
    print(f"  Device: {model.device} | DType: {model.dtype}")

    # Load examples
    examples = load_examples(dataset_path, args.split)
    print(f"  Evaluating {len(examples)} examples ({args.split} split)\n")

    # Extract tools and system msg from first example
    tools = examples[0]["tools"]
    system_msg = examples[0]["messages"][0]["content"]

    # Run predictions
    y_true, y_pred = [], []
    errors = []

    for i, ex in enumerate(examples):
        true_label = ex["category"]
        pred_label = predict(model, tokenizer, ex, tools, system_msg)
        y_true.append(true_label)
        y_pred.append(pred_label)

        if args.verbose or pred_label != true_label:
            status = "OK" if pred_label == true_label else "FAIL"
            summary = ex["messages"][1]["content"][:80].replace("\n", " ")
            print(f"  [{status}] {true_label:>20} -> {pred_label:>20}  |  {summary}")
            if pred_label != true_label:
                errors.append((true_label, pred_label, ex["messages"][1]["content"]))

        if (i + 1) % 10 == 0:
            correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
            print(
                f"  Progress: {i + 1}/{len(examples)} | Running accuracy: {correct / (i + 1):.3f}"
            )

    # Compute and print metrics
    metrics = compute_metrics(y_true, y_pred, LABELS)
    print_report(metrics, LABELS)

    # Print confusion matrix
    print("\nConfusion matrix (rows=true, cols=predicted):")
    print(f"  {'':>20}", end="")
    for col in LABELS:
        print(f"  {col[:10]:>10}", end="")
    print()
    for row in LABELS:
        print(f"  {row:>20}", end="")
        for col in LABELS:
            count = sum(1 for t, p in zip(y_true, y_pred) if t == row and p == col)
            print(f"  {count:>10}", end="")
        print()

    # Print errors if any
    invalid = sum(1 for p in y_pred if p == "invalid")
    if invalid:
        print(f"\nInvalid outputs (no tool call detected): {invalid}")

    print(f"\nMacro F1: {metrics['macro avg']['f1']:.4f}")
    print(f"Weighted F1: {metrics['weighted avg']['f1']:.4f}")
    print(f"Accuracy: {metrics['accuracy']:.4f}")


if __name__ == "__main__":
    main()

