"""Dump the exact prompt that transformers generates so we can replicate it in Cactus."""
import sys
sys.path.insert(0, "cactus/python/src")

from transformers import AutoTokenizer

ADAPTER_PATH = "aegis-adapter"

TOOLS = [
    {"type": "function", "function": {
        "name": "classify_safe",
        "description": "The file content is safe to share with cloud AI. No sensitive data detected.",
        "parameters": {"type": "object", "properties": {"reason": {"type": "string", "description": "Brief reason why the file is safe"}}, "required": ["reason"]},
    }},
    {"type": "function", "function": {
        "name": "flag_pii",
        "description": "The file contains personally identifiable information (PII) like emails, phone numbers, social security numbers, or addresses that must be redacted before sharing.",
        "parameters": {"type": "object", "properties": {"types": {"type": "string", "description": "Comma-separated list of PII types found"}}, "required": ["types"]},
    }},
    {"type": "function", "function": {
        "name": "block_transfer",
        "description": "The file contains secrets, API keys, passwords, database credentials, or encryption keys. It must NEVER be sent to the cloud.",
        "parameters": {"type": "object", "properties": {"reason": {"type": "string", "description": "Why the file must be blocked from transfer"}}, "required": ["reason"]},
    }},
    {"type": "function", "function": {
        "name": "request_permission",
        "description": "The file contains ambiguous or potentially confidential content like trade secrets, internal project names, legal terms, or financial details. Need human approval before sharing.",
        "parameters": {"type": "object", "properties": {"reason": {"type": "string", "description": "What is ambiguous and why human review is needed"}}, "required": ["reason"]},
    }},
]

tokenizer = AutoTokenizer.from_pretrained(ADAPTER_PATH)

messages = [
    {"role": "developer", "content": "You are a privacy classifier. Based on the file summary, call the correct tool."},
    {"role": "user", "content": "File summary:\nThis is a public README file for an open-source Python library. No sensitive information found."},
]

prompt = tokenizer.apply_chat_template(
    messages, tools=TOOLS, add_generation_prompt=True, tokenize=False,
)

print("=" * 80)
print("EXACT PROMPT (what the model was trained to see):")
print("=" * 80)
print(prompt)
print("=" * 80)
print(f"\nLength: {len(prompt)} chars")
