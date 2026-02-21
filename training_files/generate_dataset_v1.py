"""
Generate fine-tuning dataset for FunctionGemma privacy classification.

Improvements over v1:
  - 600 total examples (150 per class) for better generalisation
  - Balanced classes: exactly 150 each (was 60/60/40/40)
  - Hard negatives: examples that contain surface-level cues of another class
    but the correct answer is different (e.g., public docs that mention PII
    types but describe them abstractly — still classify_safe)
  - Deceptive patterns: internal docs without actual secrets → request_permission
    not block_transfer; redacted PII docs → classify_safe not flag_pii
  - Richer variety: more file types, industries, writing styles, file names
  - Each batch is generated separately to maximise diversity across calls
"""

import json
import os
import random
import time
from collections import Counter

from dotenv import load_dotenv
from google import genai
from tqdm import tqdm

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

# ── Tool definitions (shared across all examples) ────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "classify_safe",
            "description": "The file content is safe to share with cloud AI. No sensitive data detected.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Brief reason why the file is safe",
                    }
                },
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "flag_pii",
            "description": "The file contains personally identifiable information (PII) like emails, phone numbers, social security numbers, or addresses that must be redacted before sharing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "types": {
                        "type": "string",
                        "description": "Comma-separated list of PII types found: email, ssn, phone, address, name, dob, bank_account, credit_card, medical_record",
                    }
                },
                "required": ["types"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "block_transfer",
            "description": "The file contains secrets, API keys, passwords, database credentials, or encryption keys. It must NEVER be sent to the cloud.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "Why the file must be blocked from transfer",
                    }
                },
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_permission",
            "description": "The file contains ambiguous or potentially confidential content like trade secrets, internal project names, legal terms, or financial details. Need human approval before sharing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {
                        "type": "string",
                        "description": "What is ambiguous and why human review is needed",
                    }
                },
                "required": ["reason"],
            },
        },
    },
]

SYSTEM_MSG = (
    "You are a privacy classifier. Based on the file summary, call the correct tool."
)

# ── Per-category generation configs ─────────────────────────────────────────

CATEGORIES = {
    "classify_safe": {
        "total": 150,
        "batches": [
            # Batch 1: Standard public content
            {
                "count": 40,
                "prompt": """Generate {count} diverse file summaries describing SAFE files with NO sensitive data — freely shareable with cloud AI.

STANDARD SAFE FILES (no tricks):
- Public marketing materials, press releases, blog posts, newsletters
- Open-source README, LICENSE, CHANGELOG, docs, code with no secrets
- Academic papers, research notes, conference slides, tutorials
- Public financial reports (annual reports already published), investor presentations
- Product documentation, user manuals, FAQs, help articles
- Public meeting agendas (for open events), project overview docs
- Design specs for public features, wireframe descriptions with no IP
- Test files, mock data clearly labeled fake, sample data with no real people

Each summary: 2-4 sentences as if a security scanner summarized it.
End each with "No sensitive information found." or "No PII detected." or similar.

Return JSON array: [{{"summary": "...", "reason": "why safe"}}]

Be diverse in industries (tech, healthcare marketing, retail, education, finance PR), file formats, and writing styles.""",
            },
            # Batch 2: Hard negatives — look dangerous but are safe
            {
                "count": 40,
                "prompt": """Generate {count} file summaries of SAFE files that CONTAIN MISLEADING SURFACE PATTERNS — files that LOOK sensitive but are actually safe. These are the hardest cases.

HARD NEGATIVE SAFE FILES (look risky but aren't):
- Documents that DISCUSS privacy/PII/GDPR in the abstract but contain no actual PII
  e.g. "Privacy policy explaining how we handle user data" (no actual user data present)
  e.g. "GDPR compliance checklist with no personal records attached"
- Tutorials or docs that USE EXAMPLE/FAKE VALUES like api_key="your_api_key_here"
  e.g. "Developer quickstart guide showing how to authenticate with fake placeholder API keys"
- Internal policy documents that MENTION secrets handling but contain no actual secrets
  e.g. "Secrets management guide recommending storing keys in Vault — no actual keys listed"
- Reports that FOUND and FIXED PII (redacted version)
  e.g. "Post-remediation audit confirming all SSNs were removed from the database export"
- Documents describing OTHER documents that contain PII, but this doc itself has none
  e.g. "Index of HR files listing which spreadsheets contain employee records (index only, no data)"
- Public case studies that mention types of data companies handle but use no real records
  e.g. "Healthcare IT case study about de-identifying patient records — uses fictional examples only"
- Training materials about security threats that use fictional examples
  e.g. "Phishing awareness training with sample fake emails — all senders are fictional@example.com"

Each summary: 2-4 sentences. Be EXPLICIT that the file is safe despite surface-level patterns.
End with a clarifying phrase like "No actual credentials present" or "All values are placeholder/fictional" or "Contains no real personal data."

Return JSON array: [{{"summary": "...", "reason": "why safe despite appearance"}}]""",
            },
            # Batch 3: Edge cases and variety
            {
                "count": 35,
                "prompt": """Generate {count} diverse file summaries of SAFE files. Focus on UNUSUAL or NICHE file types that are public.

UNUSUAL SAFE FILE TYPES:
- Open-source configuration file templates with placeholder values (e.g., config.example.yml)
- Public dataset documentation (explaining columns in a public Kaggle dataset)
- Company career page / job descriptions
- Event schedules, conference programs, speaker bios
- Public GitHub issues, feature request documents
- Public API changelogs and deprecation notices
- Open-source license texts and contribution guidelines
- Public terms of service, cookie policies, accessibility statements
- Internal documents about publicly announced features or public roadmap items
- Sample/template contracts with clearly generic/placeholder parties
- Public compliance certificates (ISO 27001 cert document, SOC2 summary report for customers)
- Sports team rosters (public info), event programs with public names
- Open government data documentation

Each summary: 2-4 sentences. Clearly indicate no sensitive data.

Return JSON array: [{{"summary": "...", "reason": "why safe"}}]

Be diverse — vary industries, countries, file formats (.yaml, .md, .docx, .pdf, .json, .txt, .csv)""",
            },
            # Batch 4: More variety
            {
                "count": 35,
                "prompt": """Generate {count} MORE diverse file summaries of SAFE files, different from typical corporate documents.

Focus on:
- Creative industry files: scripts, game design docs (public), music metadata files (public)
- Scientific data: published dataset descriptions, experiment protocols (published), lab notebooks (public)
- Education sector: public curriculum docs, published textbooks TOC, public syllabi
- Government / public sector: published legislation summaries, public tender documents, FOIA-released docs
- NGO / non-profit: public impact reports, published grant results, public fundraising materials
- Real estate: public property listings descriptions, zoning regulation summaries
- Retail: public product catalog excerpts, public pricing sheets, published promotional rules

Each: 2-4 sentences. Clearly safe.

Return JSON array: [{{"summary": "...", "reason": "why safe"}}]""",
            },
        ],
    },
    "flag_pii": {
        "total": 150,
        "batches": [
            # Batch 1: Standard PII — obvious
            {
                "count": 40,
                "prompt": """Generate {count} file summaries describing files containing REAL PII that needs REDACTION before cloud sharing.

STANDARD PII FILES:
- Customer databases, user exports, CRM dumps with names/emails/phones/addresses
- HR records: employee directories, payroll exports, benefits enrollment forms
- Medical/patient records, insurance claims, pharmacy records
- Student records: enrollment data, transcripts, financial aid applications
- Support tickets or CRM notes with customer details and contact info
- Order histories with shipping addresses and payment info
- Survey responses or forms with identifying info
- Voter registration data, government benefit recipient files

Name SPECIFIC PII types found. Use realistic-sounding filenames.
Each: 2-4 sentences.

Return JSON array: [{{"summary": "...", "types": "comma-separated: email,ssn,phone,address,name,dob,bank_account,credit_card,medical_record"}}]

Vary: industries, file formats (CSV, JSON, XML, Excel, PDF), PII combinations.""",
            },
            # Batch 2: Subtle PII — not obviously flagged
            {
                "count": 40,
                "prompt": """Generate {count} file summaries of files containing SUBTLE or INDIRECT PII — cases where PII is present but not in a typical "user database" format.

SUBTLE PII FILES:
- Log files that inadvertently captured IP addresses, user IDs, or email addresses in URLs
- Configuration files referencing real employee emails as admin contacts
- Code files with hardcoded test data using real-looking (but needs masking) names and emails
- Analytics exports where user IDs can be re-identified via join keys
- Meeting transcripts or notes that mention specific individuals with contact info
- Backup files that include personal info as part of system state
- Debug dumps containing session data with user details
- Exported reports where column headers suggest PII (e.g., "client_email", "patient_dob")
- Customer chat transcripts containing names, addresses mentioned in conversation
- Photos/images metadata files (EXIF) with GPS coordinates and device owner name
- Git commit history files showing author names and emails

Return JSON array: [{{"summary": "...", "types": "pii types found"}}]

Be diverse — make the PII presence clear but not in an obvious "user_records.csv" format.""",
            },
            # Batch 3: Healthcare and financial PII
            {
                "count": 35,
                "prompt": """Generate {count} file summaries from HEALTHCARE and FINANCIAL sectors containing PII.

HEALTHCARE PII:
- Patient intake forms, medical history questionnaires
- Lab result files with patient names and test values
- Insurance pre-authorization requests with member IDs and diagnoses
- Clinical trial participant enrollment files
- Prescription records, pharmacy dispensing logs
- Telehealth session notes with patient details
- Mental health assessment forms

FINANCIAL PII:
- Mortgage applications with full personal and financial history
- Credit card dispute records with cardholder details
- Investment account statements with account holder info
- Tax preparation files with SSNs and financial data
- Payroll direct deposit setup forms
- Bank account opening applications
- Loan origination files

Be specific about PII types. Use realistic healthcare/finance filenames.

Return JSON array: [{{"summary": "...", "types": "specific pii types"}}]""",
            },
            # Batch 4: Hard negatives for PII — not actually PII
            {
                "count": 35,
                "prompt": """Generate {count} file summaries where files APPEAR to contain PII but are actually SAFE (classify_safe).

IMPORTANT: These should be labeled classify_safe, NOT flag_pii. Generate them as tricky "safe" examples to help the model learn boundaries.

Files that LOOK like PII but aren't:
- Fully anonymized/aggregated datasets with no individual-level data
- Files with PII field names in schema/column headers but no actual PII values filled in (template)
- Published datasets with only fake/synthetic records labeled as such
- Statistical reports showing aggregate counts (e.g., "12,000 users in 18-24 age group") with no individuals
- Data dictionaries explaining what a PII-containing database looks like (the dict itself has no records)
- Pseudonymized data where real identifiers are fully replaced with random IDs and no re-identification is possible
- Test fixtures using clearly fictional names (John Doe, Jane Smith, ACME Corp) in a dev environment

Each must CLEARLY explain why it's safe despite looking like it might have PII.
End with "No actual personal data present" or "All records are synthetic/anonymized."

Return JSON array: [{{"summary": "...", "reason": "why safe despite PII-like appearance"}}]

NOTE: These will be added to the classify_safe category in the final dataset.""",
            },
        ],
    },
    "block_transfer": {
        "total": 150,
        "batches": [
            # Batch 1: Obvious secrets
            {
                "count": 45,
                "prompt": """Generate {count} file summaries describing files containing SECRETS that must NEVER be sent to cloud AI.

CLEAR SECRET FILES:
- .env files with API keys, database passwords, service credentials
- Private SSH keys (id_rsa, id_ed25519), PGP private keys
- TLS/SSL private key files (.pem, .key)
- Service account JSON files (GCP, AWS IAM credentials)
- OAuth client_secret.json files
- JWT signing secret config files
- Config files with hardcoded passwords (database.yml, settings.py with SECRET_KEY)
- Vault unseal keys or root tokens
- Cloud provider credential files (~/.aws/credentials, ~/.gcloud/credentials)
- Kubernetes secret manifests (k8s/secrets.yaml)
- Docker registry auth configs with credentials
- CI/CD pipeline secrets files (.github/workflows with leaked secrets)
- Terraform state files (.tfstate) with sensitive outputs

Mention SPECIFIC secret types. Use realistic filenames.
Each: 2-4 sentences.

Return JSON array: [{{"summary": "...", "reason": "what secrets were found"}}]

Vary: cloud providers (AWS/GCP/Azure/HCloud), secret types, file formats, severity.""",
            },
            # Batch 2: Embedded secrets in code and config
            {
                "count": 40,
                "prompt": """Generate {count} file summaries of SOURCE CODE or CONFIG files where secrets are EMBEDDED — not dedicated secrets files, but credentials hardcoded into normal-looking files.

SECRETS EMBEDDED IN CODE/CONFIG:
- Python/JS/Go/Ruby files where someone hardcoded an API key variable
- Database connection strings hardcoded into application code
- SMTP credentials embedded in email-sending utility scripts
- Webhook URLs with auth tokens in them embedded in code
- S3 bucket names + access keys in infrastructure scripts
- Third-party service credentials (Stripe, Twilio, SendGrid, Slack) in source files
- Admin panel URLs with username/password in comments or hardcoded
- Mobile app config files (google-services.json, Info.plist) with API keys
- Webpack/build configs with API keys for analytics or error tracking
- Backup scripts with FTP/SFTP credentials
- Monitoring configs with auth tokens
- Browser automation scripts with login credentials

Each: 2-4 sentences. Be specific about WHERE the secret is and WHAT type.

Return JSON array: [{{"summary": "...", "reason": "specific secrets embedded and where"}}]""",
            },
            # Batch 3: Hard edge cases for secrets
            {
                "count": 35,
                "prompt": """Generate {count} file summaries of AMBIGUOUS-LOOKING files where secrets are DEFINITELY present (still block_transfer).

These are subtle cases — the file doesn't scream "secrets" but contains them:
- A README.md that was accidentally committed with real API keys in the code examples
- A test file that uses production credentials instead of mocks
- A backup of a config file that was supposed to be gitignored
- An exported Postman collection with real auth headers/tokens saved in it
- A developer notebook (.ipynb) with API calls that still have real keys in cells
- A shell history file (.bash_history) with `export AWS_ACCESS_KEY_ID=AKIA...` commands
- A log file that captured a request body containing an Authorization Bearer token
- A package.json or similar with a hardcoded npm token in the scripts section
- A Docker Compose file with environment variables set to real credentials
- An Ansible playbook with vault-encrypted content but also some hardcoded passwords

Each: 2-4 sentences. Make clear why it must be blocked.

Return JSON array: [{{"summary": "...", "reason": "why it must be blocked"}}]""",
            },
            # Batch 4: Hard negatives — looks like secrets but isn't
            {
                "count": 30,
                "prompt": """Generate {count} file summaries where files APPEAR to contain secrets but DON'T — these are SAFE files (classify_safe).

IMPORTANT: These are classify_safe, not block_transfer. The model must learn the difference.

Files that LOOK like they have secrets but don't:
- .env.example or config.example files with PLACEHOLDER values (YOUR_API_KEY_HERE, <your-token>)
- Documentation explaining HOW to configure API keys without containing real ones
- Public blog posts or tutorials showing how to use an API with fake key examples
- Code that uses environment variables (os.getenv("API_KEY")) but doesn't contain the actual value
- Redacted configuration files where real values were replaced with [REDACTED] or ***
- Security audit reports describing what secrets were FOUND and ROTATED (keys are now invalid)
- Architecture diagrams or README files showing where secrets should be placed (not the actual secrets)
- Unit tests that mock API calls with fake credential strings clearly marked "FAKE" or "TEST"

Each must CLEARLY explain that no actual usable secrets are present.

Return JSON array: [{{"summary": "...", "reason": "why safe despite secrets-like appearance"}}]

NOTE: These will be added to the classify_safe category.""",
            },
        ],
    },
    "request_permission": {
        "total": 150,
        "batches": [
            # Batch 1: Standard confidential business docs
            {
                "count": 45,
                "prompt": """Generate {count} file summaries of AMBIGUOUS or POTENTIALLY CONFIDENTIAL business documents needing human review before cloud sharing.

STANDARD CONFIDENTIAL DOCUMENTS:
- NDAs, confidentiality agreements, non-solicitation agreements
- Internal strategy documents, competitive analysis reports
- Unreleased product roadmaps, feature specs, pre-announcement docs
- M&A discussions, term sheets, acquisition target research
- Salary bands and compensation structures (aggregate, no individual names)
- Internal pricing models, cost structures, margin analysis
- Legal correspondence, cease-and-desist drafts, litigation prep
- Board meeting minutes, executive strategy memos
- Proprietary algorithms described at high level in pseudocode
- Trade secrets: manufacturing formulas, recipe variants, process innovations
- Internal project codenames and feature codenames
- Vendor evaluation scorecards comparing suppliers
- Pre-release financial projections, budget forecasts

Each: 2-4 sentences. The KEY is AMBIGUITY — not clearly public, not clearly secret.
Explain what makes it confidential/sensitive without being an obvious secret.

Return JSON array: [{{"summary": "...", "reason": "what makes this ambiguous or potentially confidential"}}]""",
            },
            # Batch 2: Internal but not secret
            {
                "count": 40,
                "prompt": """Generate {count} file summaries of INTERNAL documents that are SENSITIVE but don't contain PII or hard secrets — they require human judgment to decide if sharing is appropriate.

INTERNAL-BUT-AMBIGUOUS DOCUMENTS:
- Internal audit findings and compliance gap assessments
- Customer churn analysis with company names (not individual PII)
- Partner or reseller performance reviews
- Engineering architecture decision records (ADRs) for unreleased systems
- Internal pricing exception approvals or customer discounting history
- Draft press releases and announcements not yet approved
- Incident post-mortems referencing internal system names and vulnerabilities
- Internal employee handbook sections covering sensitive HR policies
- Performance review processes and calibration guidelines (no individual reviews)
- Internal tool evaluations comparing vendors by name with opinions
- Security assessment reports identifying internal vulnerabilities (no credentials)
- Org chart changes / reorg planning docs
- Internal brand guidelines or unreleased brand refresh materials
- Content moderation policy documents

Return JSON array: [{{"summary": "...", "reason": "why ambiguous / needs human decision"}}]""",
            },
            # Batch 3: Legal, financial, and IP sensitive
            {
                "count": 35,
                "prompt": """Generate {count} file summaries from LEGAL, FINANCIAL, and IP domains that require permission escalation.

LEGAL SENSITIVE:
- Patent application drafts (before filing)
- Trademark research and watch notices
- Litigation strategy memos, deposition preparation notes
- Regulatory submission drafts (pre-filing)
- Internal compliance risk assessments
- Settlement negotiation correspondence

FINANCIAL SENSITIVE:
- Pre-earnings financial model forecasts
- Investment thesis documents for unreleased positions
- Internal cost-benefit analyses for strategic initiatives
- Revenue attribution and margin reports by business line
- Budget variance analysis with internal cost centers

IP SENSITIVE:
- Trade secret documentation for manufacturing processes
- Research breakthroughs in draft form (before publication)
- Software architecture docs for proprietary unreleased systems
- Customer-specific customization specifications

Return JSON array: [{{"summary": "...", "reason": "why escalation needed"}}]""",
            },
            # Batch 4: Hard negatives — looks like request_permission but is safe
            {
                "count": 30,
                "prompt": """Generate {count} file summaries of documents that LOOK internal/confidential but are actually SAFE to share (classify_safe).

IMPORTANT: These are classify_safe. The model must learn these subtle distinctions.

Files that LOOK internal/sensitive but are safe:
- Internal documents about PUBLICLY ANNOUNCED products/features (the content is already public)
- Meeting notes from a public town hall or all-hands covering already-announced info
- Internal tracking of public bug reports or public GitHub issues
- Internal copies of published blog posts or public press releases
- Internal distribution of a published academic paper or patent (already public)
- Strategy documents that only discuss publicly known company direction
- Documents marked "internal" but containing only information already in public SEC filings
- Internal checklists for implementing publicly documented compliance frameworks

Each must CLEARLY note why the content is actually public/safe despite internal labels.
End with something like "Content reflects publicly announced strategy" or "Information already in public filings."

Return JSON array: [{{"summary": "...", "reason": "why safe despite internal-looking format"}}]

NOTE: These will be added to the classify_safe category.""",
            },
        ],
    },
}


def call_gemini(prompt: str, retries: int = 3) -> list:
    """Call Gemini and parse the JSON array response."""
    for attempt in range(retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            try:
                examples = json.loads(response.text)
                if isinstance(examples, list):
                    return examples
            except json.JSONDecodeError:
                text = response.text
                start = text.find("[")
                end = text.rfind("]") + 1
                if start >= 0 and end > start:
                    return json.loads(text[start:end])
            print(f"  WARN: parse failed on attempt {attempt + 1}, retrying...")
        except Exception as e:
            print(f"  ERROR on attempt {attempt + 1}: {e}")
            if attempt < retries - 1:
                time.sleep(5 * (attempt + 1))
    return []


def format_example(category: str, example: dict) -> dict:
    """Format a raw Gemini example into the training JSONL schema."""
    summary = example.get("summary", "")

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
            "arguments": {
                "reason": example.get("reason", "potentially confidential content")
            },
        }
    else:
        raise ValueError(f"Unknown category: {category}")

    return {
        "messages": [
            {"role": "system", "content": SYSTEM_MSG},
            {"role": "user", "content": f"File summary:\n{summary}"},
        ],
        "tools": TOOLS,
        "expected_tool_call": tool_call,
        "category": category,
    }


def main():
    all_examples = []

    # Hard-negative batches are collected into classify_safe
    # We track which category each batch's output belongs to
    batch_specs = []
    for category, config in CATEGORIES.items():
        for i, batch in enumerate(config["batches"]):
            # The last batch in flag_pii, block_transfer, and request_permission
            # generates classify_safe hard-negatives
            is_hard_negative_for_safe = (
                "reason" in batch["prompt"]
                and "classify_safe" in batch["prompt"]
                and "NOTE: These will be added to the classify_safe category"
                in batch["prompt"]
            )
            output_category = "classify_safe" if is_hard_negative_for_safe else category
            batch_specs.append((category, i, batch, output_category))

    total_expected = sum(b["count"] for _, _, b, _ in batch_specs)
    print(f"Generating ~{total_expected} examples across {len(batch_specs)} batches...")

    with tqdm(total=total_expected, desc="Generating dataset", unit="ex") as pbar:
        for src_category, batch_idx, batch, output_category in batch_specs:
            label = f"{src_category}[{batch_idx}]→{output_category}"
            pbar.set_postfix(batch=label)

            prompt = batch["prompt"].format(count=batch["count"])
            examples = call_gemini(prompt)

            if not examples:
                print(f"\n  SKIP: no examples from batch {label}")
                pbar.update(batch["count"])
                continue

            count_added = 0
            for ex in examples:
                if not isinstance(ex, dict) or "summary" not in ex:
                    continue
                formatted = format_example(output_category, ex)
                all_examples.append(formatted)
                count_added += 1

            pbar.update(count_added)
            print(f"\n  Batch {label}: got {count_added}/{batch['count']}")
            time.sleep(2)  # rate limiting

    # Shuffle
    random.shuffle(all_examples)

    # Write JSONL
    output_path = os.path.join(os.path.dirname(__file__), "dataset.jsonl")
    with open(output_path, "w") as f:
        for ex in all_examples:
            f.write(json.dumps(ex) + "\n")

    print(f"\nDataset written to {output_path}")
    print(f"Total examples: {len(all_examples)}")

    cats = Counter(ex["category"] for ex in all_examples)
    for cat in ["classify_safe", "flag_pii", "block_transfer", "request_permission"]:
        print(f"  {cat}: {cats.get(cat, 0)}")


if __name__ == "__main__":
    main()

