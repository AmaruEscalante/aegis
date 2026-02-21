"""
Generate fine-tuning dataset for FunctionGemma privacy classification.
Uses Gemini to generate diverse file summaries for each category.
"""

import json
import os
import time
from google import genai
from tqdm import tqdm

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

CATEGORIES = {
    "classify_safe": {
        "count": 60,
        "prompt": """Generate {count} diverse file summaries that describe SAFE files with NO sensitive data.
These are files that can be freely shared with cloud AI services.

Examples of safe files:
- Public marketing materials, blog posts, press releases
- Open-source code (README, LICENSE, utils, configs with no secrets)
- Academic papers, research notes, tutorials
- Product documentation, user guides, changelogs
- Public financial reports (already published), annual reports
- Meeting notes about public topics, project planning docs
- Design specs for public features, wireframes descriptions
- Test files, mock data clearly labeled as fake, sample configs

Each summary should be 2-4 sentences, written as if a security scanner summarized the file.
End each summary with a note like "No sensitive information found." or "No PII detected."

Return as a JSON array of objects with format:
{{"summary": "...", "reason": "brief reason why safe"}}

Be diverse in file types, industries, writing styles. Some should mention specific (but public) metrics, company names, product names — things that LOOK business-y but are actually public.""",
    },
    "flag_pii": {
        "count": 60,
        "prompt": """Generate {count} diverse file summaries that describe files containing PII (personally identifiable information) that needs REDACTION before sharing.

The summaries should mention specific types of PII found:
- Email addresses (mention actual-looking fake emails)
- Phone numbers
- Social Security Numbers (SSN)
- Physical addresses
- Full names linked to private data
- Date of birth, medical record numbers
- Credit card numbers, bank account numbers
- Employee IDs linked to names

Examples of files with PII:
- Customer databases, user exports, CRM dumps
- HR records, employee directories, payroll files
- Medical/patient records, insurance claims
- Student records, school enrollment data
- Contact lists, mailing lists with personal info
- Support tickets with customer details
- Order histories with shipping addresses
- Survey responses with identifying info

Each summary should be 2-4 sentences, written as if a security scanner found the PII.
Explicitly name the types of PII found.

Return as a JSON array of objects with format:
{{"summary": "...", "types": "comma-separated PII types like: email,ssn,phone,address,name"}}

Be diverse — mix industries (healthcare, finance, retail, education, HR), file formats (JSON, CSV, XML, Excel, PDF), and PII combinations.""",
    },
    "block_transfer": {
        "count": 40,
        "prompt": """Generate {count} diverse file summaries that describe files containing SECRETS that must NEVER be sent to the cloud.

These files contain:
- API keys (Stripe, OpenAI, AWS, GCP, Azure, GitHub tokens)
- Database connection strings with passwords
- .env files with credentials
- Private SSH/PGP/RSA keys
- OAuth client secrets
- JWT signing secrets
- Encryption keys, certificates
- Internal service tokens
- Cloud infrastructure credentials (IAM, service accounts)
- Hardcoded passwords in config files

Each summary should be 2-4 sentences, written as if a security scanner found the secrets.
Mention specific types of secrets found.

Return as a JSON array of objects with format:
{{"summary": "...", "reason": "brief description of what secrets were found"}}

Be diverse — mix formats (.env, .yaml, .json, .ini, .conf, code files), cloud providers, and secret types.""",
    },
    "request_permission": {
        "count": 40,
        "prompt": """Generate {count} diverse file summaries that describe files with AMBIGUOUS or POTENTIALLY CONFIDENTIAL content that requires human review.

These are NOT files with clear PII or secrets. They contain business-sensitive information where it's unclear if sharing is appropriate:

- Partnership agreements, contracts, NDAs
- Internal strategy documents, competitive analysis
- Unreleased product roadmaps, feature specs
- M&A discussions, acquisition targets
- Salary/compensation structures (without individual names)
- Internal pricing models, cost structures
- Legal correspondence, litigation documents
- Board meeting minutes, executive communications
- Proprietary algorithms described in pseudocode
- Trade secrets, manufacturing processes
- Internal project codenames
- Vendor evaluation documents
- Pre-release financial projections
- Internal audit findings

Each summary should be 2-4 sentences, written as if a security scanner flagged the content as potentially confidential.
The key is AMBIGUITY — it's not clearly public, but it's also not clearly secret.

Return as a JSON array of objects with format:
{{"summary": "...", "reason": "what makes this ambiguous or potentially confidential"}}

Be diverse — mix industries, document types, and levels of sensitivity.""",
    },
}


def generate_examples(category, config):
    """Call Gemini to generate examples for one category."""
    prompt = config["prompt"].format(count=config["count"])

    print(f"Generating {config['count']} examples for '{category}'...")

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )

    try:
        examples = json.loads(response.text)
    except json.JSONDecodeError:
        # Try to extract JSON array from response
        text = response.text
        start = text.find("[")
        end = text.rfind("]") + 1
        if start >= 0 and end > start:
            examples = json.loads(text[start:end])
        else:
            print(f"  ERROR: Could not parse response for {category}")
            print(f"  Raw: {text[:200]}")
            return []

    print(f"  Got {len(examples)} examples")
    return examples


def format_training_example(category, example):
    """Format a single example into FunctionGemma's expected training format."""
    summary = example["summary"]

    if category == "classify_safe":
        tool_call = {
            "name": "classify_safe",
            "arguments": {"reason": example.get("reason", "no sensitive data found")},
        }
    elif category == "flag_pii":
        tool_call = {
            "name": "flag_pii",
            "arguments": {"types": example.get("types", "email,phone")},
        }
    elif category == "block_transfer":
        tool_call = {
            "name": "block_transfer",
            "arguments": {"reason": example.get("reason", "contains secrets")},
        }
    elif category == "request_permission":
        tool_call = {
            "name": "request_permission",
            "arguments": {"reason": example.get("reason", "potentially confidential content")},
        }

    return {
        "messages": [
            {
                "role": "system",
                "content": "You are a privacy classifier. Based on the file summary, call the correct tool.",
            },
            {
                "role": "user",
                "content": f"File summary:\n{summary}",
            },
        ],
        "tools": [
            {"type": "function", "function": tool}
            for tool in [
                {
                    "name": "classify_safe",
                    "description": "The file content is safe to share with cloud AI. No sensitive data detected.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string", "description": "Brief reason why the file is safe"}
                        },
                        "required": ["reason"],
                    },
                },
                {
                    "name": "flag_pii",
                    "description": "The file contains personally identifiable information (PII) like emails, phone numbers, social security numbers, or addresses that must be redacted before sharing.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "types": {"type": "string", "description": "Comma-separated list of PII types found: email, ssn, phone, address, name"}
                        },
                        "required": ["types"],
                    },
                },
                {
                    "name": "block_transfer",
                    "description": "The file contains secrets, API keys, passwords, database credentials, or encryption keys. It must NEVER be sent to the cloud.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string", "description": "Why the file must be blocked from transfer"}
                        },
                        "required": ["reason"],
                    },
                },
                {
                    "name": "request_permission",
                    "description": "The file contains ambiguous or potentially confidential content like trade secrets, internal project names, legal terms, or financial details. Need human approval before sharing.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "reason": {"type": "string", "description": "What is ambiguous and why human review is needed"}
                        },
                        "required": ["reason"],
                    },
                },
            ]
        ],
        "expected_tool_call": tool_call,
        "category": category,
    }


def main():
    all_examples = []
    total_expected = sum(c["count"] for c in CATEGORIES.values())

    with tqdm(total=total_expected, desc="Generating dataset", unit="ex") as pbar:
        for category, config in CATEGORIES.items():
            pbar.set_postfix(category=category)
            examples = generate_examples(category, config)
            for ex in examples:
                formatted = format_training_example(category, ex)
                all_examples.append(formatted)
            pbar.update(len(examples))
            # Rate limiting
            time.sleep(2)

    # Shuffle
    import random
    random.shuffle(all_examples)

    # Write JSONL
    output_path = os.path.join(os.path.dirname(__file__), "dataset.jsonl")
    with open(output_path, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\nDataset written to {output_path}")
    print(f"Total examples: {len(all_examples)}")

    # Stats
    from collections import Counter
    cats = Counter(ex["category"] for ex in all_examples)
    for cat, count in sorted(cats.items()):
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
