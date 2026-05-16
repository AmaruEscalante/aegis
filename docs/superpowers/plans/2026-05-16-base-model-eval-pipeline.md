# Base Model Eval Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the synthetic data pipeline (`train/`) and generalized eval framework (`eval.py`) that runs all 3 base models against the 12 hand-curated real samples, producing a scorecard that drives the Phase 2 training decision.

**Architecture:** Two independent components on the same branch. `train/generate_dataset.py` calls Gemini per scenario to build a 200-example synthetic dataset (used as Phase 2 training fuel, NOT for eval). `eval.py` is a generic runner that evaluates any Ollama-served model against the 12 real samples, splitting cold-start from warm-call latency.

**Tech Stack:** Python 3.12 stdlib (`urllib.request`, `json`, `argparse`, `time`, `statistics`), `google-genai` (already in `pyproject.toml`), `numpy` (transitively available via `torch`), Ollama 0.5+, Gemini 2.5 Flash for synthetic generation.

**Spec:** `docs/superpowers/specs/2026-05-16-base-model-eval-pipeline-design.md`

**Branch:** `ollama-migration` (do not push without teammate sign-off — same as the migration work).

---

## File map

| File | Purpose | Created in task |
|---|---|---|
| `train/prompts.py` | 200 pre-defined scenarios + Gemini system prompt | Task 1 |
| `train/generate_dataset.py` | Gemini-driven synthetic content generator | Task 2 |
| `train/README.md` | How to regenerate / extend the dataset | Task 2 |
| `train/dataset.jsonl` | Generated artifact, **gitignored** | Tasks 3-5 |
| `eval.py` | Generalized eval runner, repo root | Task 6 |
| `docs/eval-results/2026-05-16-gemma4-e2b-base.txt` | Eval log for gemma4:e2b | Task 8 |
| `docs/eval-results/2026-05-16-functiongemma-base.txt` | Eval log for functiongemma | Task 8 |
| `docs/eval-results/2026-05-16-embeddinggemma-base.txt` | Eval log for embeddinggemma | Task 8 |
| `docs/eval-results/scorecard.md` | Aggregated comparison | Task 9 |
| `.gitignore` | Append `train/dataset.jsonl` line | Task 2 |

---

## Task 1: Scenario definitions in `train/prompts.py`

**Files:**
- Create: `train/prompts.py`

- [ ] **Step 1: Create the train/ directory and prompts.py with the system prompt + 4 scenario lists**

Create `train/prompts.py` with this exact content:

```python
"""
Synthetic dataset scenarios for the Aegis privacy classifier.

Each scenario is a short directive that Gemini expands into realistic
file content. The scenarios are pre-defined (50 per class × 4 classes
= 200 total) to enforce deterministic coverage of common privacy-
classification cases.

Used by train/generate_dataset.py. Reused by Phase 2 training (when
that spec lands).
"""

# Gemini sees this on every generation call.
SYSTEM_PROMPT = """You are generating REALISTIC file content for a privacy classifier training dataset.

Given a brief scenario, produce the full text content of a plausible file matching that scenario. Output ONLY the file content — no preamble, no commentary, no markdown fencing.

Guidelines:
- Length: 500-3000 characters of realistic content.
- Format: match the implied file type (CSV header + rows, JSON object, YAML, .env style key=value lines, plain prose, code with comments, etc.).
- Realism: use plausible-looking names, addresses, IDs, dates. They will be FAKE (this is a training dataset) but should look real enough to pass eyeball inspection.
- For files that should contain secrets/PII: ACTUALLY include them in plausible formats (e.g., AWS_SECRET_ACCESS_KEY=AKIA... with a realistic-looking key value).
- For SAFE files: do NOT slip in PII, emails, secrets, or "confidential" markers.
- For AMBIGUOUS files: use language that hints at confidentiality without naming explicit secrets (NDA language, "internal use only", "Q3 projections", etc.).

Output the file content directly, starting with the first character of the file."""


# 50 scenarios per class. Each is a short directive (~10-25 words).

CLASSIFY_SAFE = [
    "README.md for an open-source Python utility library (string manipulation helpers)",
    "README.md for an open-source JavaScript date-formatting library",
    "MIT LICENSE file for an open-source project",
    "CONTRIBUTING.md for an open-source library — code style, PR process, testing",
    "CHANGELOG.md fragment listing version 2.4.0 bug fixes and features for a CLI tool",
    "B2B SaaS marketing one-pager describing analytics platform features (no customer names)",
    "Consumer app marketing copy for a meditation app — features, pricing tiers, public testimonials",
    "Press release announcing a new product launch with public stats (units sold, market reach)",
    "Public case study describing aggregate ROI from a B2B customer (anonymized, percentages only)",
    "Public API reference page for a payments SDK — endpoints, params, example requests/responses",
    "Step-by-step tutorial: how to deploy a Next.js app to Vercel (public docs)",
    "FAQ page for a developer tool — common questions about installation, support tiers",
    "Public product spec for an open-source database extension (postgres pg_search)",
    "Excerpt from a published annual report — aggregate revenue, headcount, no individual data",
    "Excerpt from a public market research report on global EV adoption",
    "tsconfig.json for a TypeScript project — strict mode, paths, no secrets",
    ".eslintrc.json with rules, parser config, no secrets",
    "package.json without secrets — dependencies, scripts, repository field",
    "Public CSV sample: weather station readings — date, temp, humidity (no PII)",
    "Public CSV sample: city population statistics by year (no PII)",
    "Recipe blog post — ingredients, instructions, no personal info",
    "Travel blog post about a public destination (Tokyo) — no personal contact info",
    "Tech blog post: explaining how a database B-tree works (educational)",
    "Tech blog post: comparing two JavaScript frameworks at the API level (no customer data)",
    "Tutorial: setting up Docker for local development (no secrets in the examples)",
    "Open-source code: a utility module of pure functions for array manipulation",
    "Open-source code: a Python class implementing a sorted set, with docstrings and tests",
    "Open-source code: a small React component (Button) with TypeScript props",
    "Code-of-conduct document for an open-source community",
    "Public roadmap document for an open-source project (issues to tackle next quarter)",
    "Stack Overflow answer explaining a CSS grid layout problem",
    "GitHub issue description: 'Feature request: add dark mode toggle to settings page'",
    "Public meetup announcement: 'Python user group, next Tuesday, RSVP free'",
    "Public job description for a backend engineer role (responsibilities, qualifications, no internal salary)",
    "Public docs: command reference for a CLI tool (subcommands, flags, examples)",
    "Public docs: error code reference for a public API (error codes, descriptions)",
    "Public benchmark report: comparing 3 open-source HTTP libraries (latency, throughput)",
    "Public design system documentation: color tokens, spacing scale, typography",
    "Public conference abstract: a talk about distributed systems patterns",
    "Public newsletter issue: 5 links and short commentary on recent tech news",
    "Public glossary of terms in machine learning (definitions, no proprietary data)",
    "Public whitepaper excerpt about consensus algorithms in distributed databases",
    "Public coding-bootcamp curriculum outline: week-by-week topics, no student data",
    "Public sample test suite for a string parser — fixtures and assertions",
    "Public hackathon submission README — what was built, team members' GitHub handles only",
    "Public RFC discussing a proposed feature addition to an open-source standard library",
    "Public release notes for a Linux distribution — kernel version, package updates",
    "Public infrastructure-as-code module example (Terraform) using only public AMI IDs",
    "Public Postman collection example: how to call a weather API (no API key set)",
    "Public ETL pipeline tutorial: how to load CSV into BigQuery using public datasets",
]


FLAG_PII = [
    "customers.csv with 10 rows: full_name, email, phone, address fields populated with realistic fake values",
    "patient_records.csv with 8 rows including date_of_birth, ssn, medical_record_number, diagnosis",
    "employees.json — array of 12 employees with name, email, phone, home_address, employee_id, salary_band",
    "hr_payroll.csv — name, ssn, address, gross_pay, net_pay, bank_account_last4 for 6 employees",
    "mailing_list.csv with name, email, signup_date columns and 20 rows of realistic-looking contacts",
    "support_tickets.json — array of 5 tickets each with customer_name, customer_email, account_number, address",
    "survey_responses.csv with respondent_name, age, email, zip_code, free_text_feedback (20 rows)",
    "order_history.json — 6 orders with customer_name, shipping_address, phone, items_purchased, total_paid",
    "school_enrollment.csv — student_name, dob, parent_name, parent_phone, parent_email, address (10 rows)",
    "insurance_claims.json — 4 claims with claimant_name, policy_number, dob, diagnosis_code, claim_amount",
    "donor_list.csv — donor_name, email, phone, donation_amount, donation_date (15 rows)",
    "volunteer_signups.json — name, email, phone, t_shirt_size, emergency_contact_name, emergency_contact_phone",
    "membership_directory.csv — member_name, member_id, email, phone, home_address, join_date",
    "customer_feedback.json — 5 entries with customer_name, email, account_id, rating, free_text_comments",
    "lead_capture.csv — name, work_email, company, phone, job_title (12 rows)",
    "client_contact_sheet.csv — client_name, primary_contact_name, contact_email, contact_phone, address",
    "guest_list.json — 8 guests with full_name, email, plus_one_name, dietary_restrictions",
    "appointment_book.csv — patient_name, dob, phone, appointment_date, appointment_type (15 rows)",
    "lab_results.json — 3 patients each with name, dob, mrn, test_type, result_value, doctor_name",
    "prescription_log.csv — patient_name, dob, drug_name, dose, prescribed_by, pharmacy (10 rows)",
    "rental_applications.csv — applicant_name, ssn_last4, current_address, monthly_income, employer (6 rows)",
    "loan_applications.json — 4 applicants with full_name, ssn, dob, employer, annual_income, address",
    "vehicle_registrations.csv — owner_name, owner_address, vin, license_plate, make, model (8 rows)",
    "background_check_results.json — 3 candidates with name, dob, ssn_last4, employment_history",
    "police_report_excerpt.txt — incident description naming victim, witnesses, addresses (anonymized to look real)",
    "real_estate_listing_contacts.csv — seller_name, seller_phone, seller_email, property_address, asking_price",
    "tax_return_summary.json — taxpayer_name, ssn, dependents (with names and dobs), agi, refund_amount",
    "bank_statement_excerpt.csv — account_holder_name, account_number_last4, date, transaction, balance (12 rows)",
    "credit_card_statement_lines.csv — cardholder_name, card_last4, transaction_date, merchant, amount (15 rows)",
    "veterinary_records.json — pet_owner_name, owner_phone, pet_name, vaccinations, microchip_id (5 entries)",
    "fitness_class_signup.csv — participant_name, dob, phone, emergency_contact, medical_notes (12 rows)",
    "dating_app_export.json — 4 user profiles with name, age, dob, photo_url, bio, last_known_location",
    "matchmaker_intake_form.csv — client_name, dob, contact_phone, preferences, dealbreakers (8 rows)",
    "therapy_intake_notes.txt — patient name, dob, contact info, presenting issue, family history (prose)",
    "dental_records.csv — patient_name, dob, insurance_id, last_visit, procedures_done (10 rows)",
    "pediatric_records.json — 3 children with name, dob, parent_name, parent_phone, allergies, vaccinations",
    "student_grades.csv — student_id, student_name, parent_email, course, grade, term (15 rows)",
    "alumni_directory.csv — name, graduation_year, current_employer, work_email, home_email, phone (10 rows)",
    "neighborhood_watch_roster.csv — resident_name, address, phone, email, vehicle_info (8 rows)",
    "club_membership.json — 6 members with name, address, phone, email, membership_tier, payment_method_last4",
    "shipping_manifest.csv — recipient_name, recipient_address, recipient_phone, tracking_number (12 rows)",
    "gym_signup_sheet.csv — name, dob, phone, emergency_contact_name, emergency_contact_phone (10 rows)",
    "summer_camp_registration.json — 4 kids with name, dob, parent_name, parent_email, medical_conditions",
    "babysitter_contact_list.csv — sitter_name, phone, hourly_rate, certifications, references (6 rows)",
    "pet_adoption_records.json — 3 adopters with adopter_name, address, phone, email, pet_id, adoption_date",
    "marathon_registration.csv — runner_name, age, sex, address, phone, t_shirt_size, emergency_contact (12 rows)",
    "voter_outreach_list.csv — voter_name, address, phone, party_affiliation_guess, last_voted (15 rows)",
    "petition_signatures.json — 10 signatories with name, address, email, date_signed",
    "private_tutor_intake.csv — student_name, parent_name, parent_phone, parent_email, subjects, schedule (8 rows)",
    "wedding_guest_responses.json — 12 guests with name, plus_one_name, dietary_needs, address (for invitations)",
]


BLOCK_TRANSFER = [
    ".env file with AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION (realistic-looking IAM creds)",
    ".env file with DATABASE_URL containing password, REDIS_URL with auth, JWT_SECRET, SESSION_SECRET",
    ".env file with STRIPE_SECRET_KEY (sk_live_...), STRIPE_WEBHOOK_SECRET, STRIPE_PUBLISHABLE_KEY",
    ".env file with OPENAI_API_KEY (sk-...), ANTHROPIC_API_KEY, COHERE_API_KEY",
    ".env file with GITHUB_TOKEN (ghp_...), GITHUB_WEBHOOK_SECRET, GITHUB_APP_PRIVATE_KEY (base64)",
    ".env file with TWILIO_AUTH_TOKEN, TWILIO_ACCOUNT_SID, TWILIO_API_SECRET",
    "kubernetes_secrets.yaml with base64-encoded production database password, JWT secret, S3 keys",
    "kubernetes secret manifest with TLS cert + private key (PEM, base64-encoded), namespace: prod",
    "kubernetes secret YAML containing OAuth provider client_id + client_secret base64-encoded",
    "docker-compose.yml with hard-coded POSTGRES_PASSWORD, REDIS_PASSWORD in environment blocks",
    "docker-compose.yml exposing GRAFANA_ADMIN_PASSWORD, MINIO_ROOT_PASSWORD in env section",
    "OAuth client_secret.json (Google OAuth 2.0 — client_id, client_secret, redirect_uris)",
    "Google Cloud service-account key JSON (private_key field with full PEM block)",
    "Firebase service-account credentials JSON with private_key_id, private_key, client_email",
    "AWS credentials file (~/.aws/credentials format) with [default] and [production] profiles",
    "Stripe API key file (literally the key on one line — sk_live_51A...)",
    "OpenSSH private key file (-----BEGIN OPENSSH PRIVATE KEY----- through END)",
    "RSA private key (-----BEGIN RSA PRIVATE KEY----- through END) for SSL termination",
    "PGP private key block — armored PEM",
    "GnuPG keyring excerpt — secret subkey with passphrase note",
    "Vault sealed-key shamir share (looks like base64 with a prefix)",
    "HashiCorp Vault token file: s.RandomBase64TokenHere with role_id and secret_id",
    ".npmrc with //registry.npmjs.org/:_authToken=npm_...",
    ".pypirc with [pypi] username + password for uploading packages",
    "Docker config.json with auths block containing base64 encoded registry credentials",
    "Pulumi config file with encrypted secret strings (pulumi-secret: ...) and the encryption key",
    "1Password emergency kit text export with master password and secret key",
    "Bitwarden vault export JSON with login entries (name, username, password, totp_secret)",
    "LastPass CSV export — url, username, password, totp for many entries",
    "Database connection string file: postgresql://admin:HARDCODED_PASSWORD@prod-db.example.com/maindb",
    "MongoDB connection URI in plain text: mongodb+srv://user:SECRETPASS@cluster.example.mongodb.net/",
    "Redis URL with auth: redis://default:LONGRANDOMSECRET@redis.example.com:6380/0",
    "JWT signing key text file (HS256 secret) — single long random string",
    "Symmetric encryption key text file — AES-256 key in hex",
    "Slack bot token file: xoxb-... and signing_secret",
    "Discord bot token text file: MTAxxxxx.YYYY.ZZZZ",
    "Telegram bot token: 1234567890:AAH... (single line)",
    "Twilio API key file: AC... (account sid) and corresponding auth token below",
    "SendGrid API key text file: SG.RandomBase64String",
    "Mailgun API key text file: key-RandomHexString and domain",
    "Cloudflare API token file: full token string for DNS edit permissions",
    "Heroku auth token file (~/.netrc snippet for heroku.com)",
    "GitLab personal access token file: glpat-... (full token)",
    "DigitalOcean spaces credentials: SPACES_KEY, SPACES_SECRET (.env style)",
    "Backblaze B2 application key file: keyID + applicationKey",
    "Wasabi S3 credentials .env: WASABI_ACCESS_KEY_ID, WASABI_SECRET_ACCESS_KEY",
    "MinIO credentials: MINIO_ROOT_USER, MINIO_ROOT_PASSWORD in plain-text config",
    "RDS master password export: 'rds-master-password=' single line file",
    "SMTP credentials file: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS",
    "GCP service account key in Terraform variable file (sensitive=true but value present)",
]


REQUEST_PERMISSION = [
    "Non-Disclosure Agreement template — parties, term, confidential information definition, jurisdiction",
    "Mutual NDA between Acme Inc and a vendor — full body with effective date and signature blocks",
    "Master Services Agreement excerpt: scope, payment terms, IP assignment, confidentiality, term",
    "Partnership Agreement memo — partners, capital contributions, profit split, dissolution clause",
    "Letter of Intent for M&A — non-binding LOI describing proposed acquisition price range and timeline",
    "Term sheet for a Series B financing round — valuation, board composition, liquidation preference",
    "Board meeting minutes Q3 — financial highlights (internal numbers), strategic decisions discussed",
    "Board resolution authorizing a $5M credit facility — text with internal financials referenced",
    "'Confidential — Competitive Strategy' memo describing how to respond to a competitor's launch",
    "Internal Q4 financial forecast — revenue projections, operating margin, headcount plan (pre-publication)",
    "Salary band internal doc — IC1 through IC6 salary ranges, equity bands, comp philosophy",
    "Layoff plan (RIF) — list of impacted roles, severance terms, communications timeline (no individual names)",
    "Trade-secret recipe / formula — proprietary process for manufacturing a coating",
    "Internal SWOT analysis — strengths, weaknesses, market threats, opportunities (with strategic implications)",
    "Vendor evaluation matrix — internal scoring of 3 vendors on price, capability, risk (decision-supporting)",
    "Confidential customer churn analysis — internal narrative about which segment is leaving and why",
    "Pre-IPO S-1 draft excerpt — risk factors section with confidential business risks listed",
    "Acquisition target due-diligence memo — internal assessment of a target's revenue and risks",
    "Internal red-team report — security findings prior to remediation (CVEs identified but not yet fixed)",
    "Compliance audit report — internal findings with control gaps and remediation plan",
    "GDPR data-processing impact assessment — internal analysis of risks for a new product feature",
    "Litigation hold notice — internal memo instructing employees to preserve documents for pending suit",
    "Settlement agreement draft — text discussing dispute terms (Confidential settlement)",
    "Employment contract draft — base salary, bonus structure, restrictive covenants (specific to a hire)",
    "Severance agreement template with negotiated terms — release of claims, NDA, non-compete",
    "Internal market expansion plan — countries to enter Q1-Q4, capital needed, GTM strategy",
    "Pricing strategy memo — proposed pricing changes, competitor analysis, projected revenue impact",
    "Internal roadmap doc — feature releases planned for next 4 quarters with confidential rationale",
    "Patent application draft — claims and detailed description prior to filing",
    "Patent license negotiation memo — internal walk-through of terms being considered",
    "Internal investor update memo — quarterly metrics, runway, fundraising status (confidential to LPs)",
    "Cap table snapshot — shareholder names, share counts, percentage ownership (sensitive but not PII per se)",
    "409A valuation report excerpt — internal valuation drivers and resulting strike price",
    "Compensation committee meeting notes — discussion of executive comp recommendations",
    "Litigation strategy memo from counsel — privileged + internal-strategy",
    "Confidential customer reference list with internal notes on each customer's status / health",
    "Internal pricing exception log — list of deals where standard pricing was waived and why",
    "Sales pipeline snapshot — internal deal stages, ARR, probability for top accounts (no PII)",
    "Channel partner agreement draft — economics, exclusivity, termination terms",
    "Internal data-sharing agreement draft — what data leaves the company under what controls",
    "Board observer rights agreement — terms describing observer access to board materials",
    "Confidential post-mortem of a security incident — internal timeline, root cause, lessons learned",
    "Internal communication policy — what employees should/shouldn't say on social media about the company",
    "Crisis communication plan — internal playbook for PR responses to specific bad scenarios",
    "Confidential talent succession plan — internal map of who could backfill which leadership role",
    "Internal customer-segmentation strategy — proprietary segmentation criteria and rationale",
    "Buy-vs-build analysis for a new technology — internal financial and strategic comparison",
    "Internal investor pitch deck (pre-roadshow) — financial projections, market sizing, ask amount",
    "Confidential M&A target list — short list of companies being considered for acquisition",
    "Internal merger integration plan — Day-1, Day-30, Day-90 actions with internal-only details",
]


# Public mapping for the generator. Order matters: this is the order classes
# are iterated when --limit is applied.
SCENARIOS = {
    "classify_safe": CLASSIFY_SAFE,
    "flag_pii": FLAG_PII,
    "block_transfer": BLOCK_TRANSFER,
    "request_permission": REQUEST_PERMISSION,
}


def assert_scenario_counts():
    """Run-time sanity check: every class has exactly 50 scenarios."""
    for label, scenarios in SCENARIOS.items():
        assert len(scenarios) == 50, f"{label} has {len(scenarios)} scenarios, expected 50"
```

- [ ] **Step 2: Verify scenario counts (sanity check)**

Run:
```bash
python3 -c "from train.prompts import assert_scenario_counts; assert_scenario_counts(); print('OK: 50 scenarios per class')"
```

Expected: `OK: 50 scenarios per class`. Any AssertionError means a scenario list is off by one or more.

- [ ] **Step 3: Commit**

```bash
git add train/prompts.py
git commit -m "$(cat <<'EOF'
Add scenario lists for synthetic dataset generation

50 scenarios per verdict class (200 total). Pre-defined for
deterministic coverage of the kinds of files Aegis should
classify. Used by train/generate_dataset.py and reusable for
Phase 2 training.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Implement `train/generate_dataset.py`

**Files:**
- Create: `train/generate_dataset.py`
- Create: `train/README.md`
- Modify: `.gitignore` (append two lines)

- [ ] **Step 1: Update .gitignore**

Append these lines to `.gitignore`:

```
# Phase 1 synthetic dataset
train/dataset.jsonl
```

(Don't replace the file — append. Use `echo` or open in an editor and add at the end.)

- [ ] **Step 2: Create `train/generate_dataset.py`**

Create `train/generate_dataset.py` with this exact content:

```python
"""
Synthetic dataset generator for Aegis privacy classification.

Reads scenarios from train/prompts.py, calls Gemini per scenario,
validates the output, and appends to train/dataset.jsonl.

Each line of dataset.jsonl is a JSON object:
    {"scenario_id": "<class>:<n>", "label": "<class>", "text": "<file content>"}

Resumes from existing dataset.jsonl on rerun — skips scenarios whose
scenario_id is already present.

Usage:
    GEMINI_API_KEY=... python train/generate_dataset.py            # 50/class = 200 total
    GEMINI_API_KEY=... python train/generate_dataset.py --limit 2  # 2/class = 8 (smoke)
    GEMINI_API_KEY=... python train/generate_dataset.py --limit 4  # 4/class = 16 (validate)

Phased rollout (matches the spec):
    Stage 1 (smoke):    --limit 2  -> ~8 examples,  ~$0.01
    Stage 2 (validate): --limit 4  -> ~16 examples, ~$0.03
    Stage 3 (full):     (no limit) -> 200 examples, ~$0.20
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

from google import genai

# train/ is a sibling of the repo root scripts; import the local prompts module.
# When run as `python train/generate_dataset.py` from the repo root, sys.path
# includes the script's directory (train/) so the local import works.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompts import SYSTEM_PROMPT, SCENARIOS  # noqa: E402


DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "dataset.jsonl"

MIN_OUTPUT_CHARS = 300
MAX_RETRIES = 2
RETRY_TEMPERATURES = [0.4, 0.7, 0.9]  # used by retry attempts in order

# Regex patterns that flag_pii outputs MUST contain at least one of, to be
# considered a valid PII-bearing file. Loose intentionally — Gemini sometimes
# produces dates as YYYY-MM-DD, sometimes MM/DD/YYYY, etc.
PII_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}"),  # email
    re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),                            # SSN
    re.compile(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),           # phone
    re.compile(r"\b\d{1,5}\s+\w+\s+(?:Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Lane|Ln|Court|Ct)\b", re.IGNORECASE),  # address
]

# Regex patterns that block_transfer outputs SHOULD contain at least one of.
# Same intent as PII_PATTERNS — looseness is intentional.
SECRET_HINT_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9]+"),                              # Stripe live key prefix
    re.compile(r"sk-[A-Za-z0-9]{20,}"),                               # OpenAI-ish key prefix
    re.compile(r"AKIA[0-9A-Z]{16}"),                                  # AWS access key id
    re.compile(r"AIza[A-Za-z0-9_-]{20,}"),                            # GCP API key prefix
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),                              # GitHub PAT
    re.compile(r"BEGIN\s+(RSA|OPENSSH|EC|PGP)\s+PRIVATE KEY"),        # PEM private key marker
    re.compile(r"(?i)password\s*[:=]\s*\S{6,}"),                      # password=...
    re.compile(r"(?i)secret(_key|_token)?\s*[:=]\s*\S{10,}"),         # secret=, secret_key=
    re.compile(r"(?i)api[_-]?key\s*[:=]\s*\S{10,}"),                  # api_key=, apiKey=
    re.compile(r"xox[bpoa]-[A-Za-z0-9-]{10,}"),                       # Slack token
]


def load_done_ids(path: Path) -> set:
    """Return the set of scenario_ids already present in dataset.jsonl."""
    if not path.exists():
        return set()
    done = set()
    with path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                if "scenario_id" in row:
                    done.add(row["scenario_id"])
            except json.JSONDecodeError:
                continue
    return done


def validate(label: str, text: str, scenario: str) -> tuple[bool, str]:
    """
    Return (ok, reason). reason is empty if ok=True, else explains why not.
    """
    if len(text) < MIN_OUTPUT_CHARS:
        return False, f"too short ({len(text)} < {MIN_OUTPUT_CHARS})"

    # Reject obvious instruction echo
    if scenario.lower()[:60] in text.lower():
        return False, "echoes scenario instruction"

    # Class-specific structural checks
    if label == "flag_pii":
        if not any(p.search(text) for p in PII_PATTERNS):
            return False, "flag_pii output contains no detectable PII pattern"
    elif label == "block_transfer":
        if not any(p.search(text) for p in SECRET_HINT_PATTERNS):
            return False, "block_transfer output contains no detectable secret pattern"

    return True, ""


def generate_one(client, model: str, scenario: str, temperature: float) -> str:
    """One Gemini call. Returns the raw text content."""
    full_prompt = f"{SYSTEM_PROMPT}\n\nScenario: {scenario}\n\nFile content:"
    response = client.models.generate_content(
        model=model,
        contents=full_prompt,
        config={"temperature": temperature},
    )
    return (response.text or "").strip()


def generate_with_retries(client, model: str, label: str, scenario: str) -> tuple[str, str]:
    """
    Try to generate a valid example for `scenario`. Returns (text, status).
    status is "ok" on success or the validation failure reason on giving up.
    """
    last_reason = "no attempt"
    for attempt, temp in enumerate(RETRY_TEMPERATURES[: MAX_RETRIES + 1]):
        try:
            text = generate_one(client, model, scenario, temp)
        except Exception as exc:
            last_reason = f"api error: {exc}"
            time.sleep(1.0)
            continue
        ok, reason = validate(label, text, scenario)
        if ok:
            return text, "ok"
        last_reason = reason
    return "", last_reason


def main():
    parser = argparse.ArgumentParser(description="Synthetic Aegis dataset generator")
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max scenarios per class (default 50 = full 200-example set)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output JSONL path",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Gemini model (default {DEFAULT_MODEL})",
    )
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    client = genai.Client(api_key=api_key)

    done = load_done_ids(args.output)
    if done:
        print(f"[generate] Resuming. {len(done)} scenarios already in {args.output}.")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    total_planned = 0
    generated = 0
    skipped = 0
    failed: list[tuple[str, str]] = []

    with args.output.open("a") as out:
        for label, scenarios in SCENARIOS.items():
            for n, scenario in enumerate(scenarios[: args.limit]):
                scenario_id = f"{label}:{n}"
                total_planned += 1

                if scenario_id in done:
                    skipped += 1
                    continue

                print(f"[{generated + skipped + len(failed) + 1:3d}/{total_planned:3d}] {scenario_id:30s} {scenario[:50]:50s} ", end="", flush=True)
                text, status = generate_with_retries(client, args.model, label, scenario)
                if status != "ok":
                    failed.append((scenario_id, status))
                    print(f"FAIL ({status})")
                    continue

                row = {"scenario_id": scenario_id, "label": label, "text": text}
                out.write(json.dumps(row) + "\n")
                out.flush()
                generated += 1
                print(f"OK ({len(text)} chars)")

    print()
    print(f"Generated: {generated}")
    print(f"Skipped (already in file): {skipped}")
    print(f"Failed: {len(failed)}")
    if failed:
        print("Failures:")
        for sid, reason in failed:
            print(f"  {sid}: {reason}")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create `train/README.md`**

Create `train/README.md` with this exact content:

````markdown
# Synthetic Dataset Generator

Builds `dataset.jsonl` — labeled file content for Phase 2 training of the Aegis privacy classifier. **Not used at eval time** (eval runs on `samples/`).

## Quick start

```bash
# Phased rollout — run each stage, eyeball quality between them.
GEMINI_API_KEY=<your_key> python train/generate_dataset.py --limit 2   # stage 1: 8 examples
GEMINI_API_KEY=<your_key> python train/generate_dataset.py --limit 4   # stage 2: 16 examples
GEMINI_API_KEY=<your_key> python train/generate_dataset.py             # stage 3: 200 examples
```

Subsequent runs **append** to the file. If you want to start over, `rm train/dataset.jsonl` first.

## What's generated

- Each row of `dataset.jsonl`:
  ```json
  {"scenario_id": "block_transfer:7", "label": "block_transfer", "text": "<file content>"}
  ```
- 4 verdict classes × up to 50 scenarios = up to 200 examples.
- Scenario list lives in `train/prompts.py` — edit there to extend or change coverage.

## Validation

Each generated example is checked against class-specific rules:
- All: length ≥ 300 characters, doesn't echo the scenario instruction.
- `flag_pii`: must contain at least one regex-detectable PII pattern (email, SSN, phone, US address).
- `block_transfer`: must contain at least one secret-hint pattern (AWS/Stripe/OpenAI/GitHub/PEM/`password=`/etc.).

Validation failures retry with a different temperature up to 2 times before giving up on that scenario. Failed scenarios are listed at the end of the run and the script exits 1.

## Cost (approx, Gemini 2.5 Flash)

| Stage | Examples | Cost | Time |
|---|---|---|---|
| Stage 1 (--limit 2) | 8 | <$0.01 | ~1 min |
| Stage 2 (--limit 4) | 16 | ~$0.03 | ~3 min |
| Stage 3 (full) | 200 | ~$0.20 | ~15 min |
````

- [ ] **Step 4: Syntax-check the generator**

Run:
```bash
python3 -c "import ast; ast.parse(open('train/generate_dataset.py').read()); print('OK')"
```

Expected: `OK`.

- [ ] **Step 5: Help text smoke (no API call)**

Run:
```bash
python3 train/generate_dataset.py --help
```

Expected: argparse help text printed, exits 0. Mentions `--limit`, `--output`, `--model`.

- [ ] **Step 6: Commit**

```bash
git add train/generate_dataset.py train/README.md .gitignore
git commit -m "$(cat <<'EOF'
Add Gemini-driven synthetic dataset generator

Resumes from existing dataset.jsonl on rerun via scenario_id lookup.
Validates each output: length, no instruction echo, class-specific
regex hints for flag_pii (PII patterns) and block_transfer (secrets).
Retries on validation failure with rising temperature, gives up
after MAX_RETRIES.

--limit per class controls phased rollout: --limit 2 = 8 examples
(smoke), --limit 4 = 16 (validate), default = 200 (full).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Stage 1 — smoke generation

**Files:** none modified; `train/dataset.jsonl` populated.

- [ ] **Step 1: Run stage 1 smoke generation**

Make sure `GEMINI_API_KEY` is set in your shell. Then run:

```bash
python3 train/generate_dataset.py --limit 2
```

Expected stdout:
- Lines like `[  1/  8] classify_safe:0   README.md for an open-source ...       OK (1234 chars)` for each of the 8 attempts.
- Final summary: `Generated: 8`, `Skipped: 0`, `Failed: 0`.
- Exit code 0.

If any scenario fails: stop, read the failure reason, and decide whether it's a prompt issue (fix in `train/prompts.py` or refine `SYSTEM_PROMPT`) or a transient Gemini issue (rerun — resume logic skips already-generated rows).

- [ ] **Step 2: Eyeball-check the generated content**

```bash
python3 -c "
import json
with open('train/dataset.jsonl') as f:
    for line in f:
        row = json.loads(line)
        print('---', row['scenario_id'], '(', row['label'], ')---')
        print(row['text'][:500])
        print()
"
```

Manually check the 8 examples:
- Does each look like the kind of file the scenario described?
- Are the `block_transfer` examples actually full of credentials, not just talking about them?
- Are the `flag_pii` examples carrying real-looking PII (not redacted with `[REDACTED]`)?
- Are the `classify_safe` examples actually safe (no slipped-in emails or "confidential" markers)?
- Are the `request_permission` examples appropriately ambiguous (NDA-ish language without explicit secrets)?

If any class is consistently bad, **stop, fix the scenarios in `train/prompts.py` or `SYSTEM_PROMPT`, then `rm train/dataset.jsonl` and rerun stage 1.**

- [ ] **Step 3: Commit a marker noting stage 1 passed**

The dataset itself is gitignored. Commit only a tiny note in the generator's README so the gate is recorded in git history:

```bash
git commit --allow-empty -m "$(cat <<'EOF'
Phase 1 stage 1 (smoke generation) passed

Generated 8 examples, eyeballed quality across all 4 classes,
proceeding to stage 2.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Stage 2 — validate generation

**Files:** `train/dataset.jsonl` extended.

- [ ] **Step 1: Run stage 2**

```bash
python3 train/generate_dataset.py --limit 4
```

Expected:
- ~8 lines saying `OK` for the 8 already-done scenarios... actually no, the script reports `[N/total]` but skips already-done rows silently in the count. Re-read the output: the printed counter starts after skips. You should see only the **new** scenarios being generated (8 new ones — scenarios 2 and 3 for each class).
- Final summary: `Generated: 8`, `Skipped: 8`, `Failed: 0`.
- `train/dataset.jsonl` now has 16 lines total.

Verify line count:
```bash
wc -l train/dataset.jsonl
```
Expected: `16 train/dataset.jsonl`.

- [ ] **Step 2: Random-sample inspection (5 per class)**

```bash
python3 -c "
import json, random
random.seed(0)
by_label = {}
for line in open('train/dataset.jsonl'):
    row = json.loads(line)
    by_label.setdefault(row['label'], []).append(row)
for label, rows in by_label.items():
    print('===', label, '===')
    for row in random.sample(rows, min(len(rows), 5)):
        print('--- scenario_id:', row['scenario_id'])
        print(row['text'][:400])
        print()
"
```

Check:
- Are stage 2 examples adding scenario variety beyond stage 1?
- Is any class consistently weak (e.g., all `classify_safe` examples are README files — too narrow)?
- Did any example get through validation despite being borderline (e.g., a `flag_pii` row with a regex-detectable phone number but otherwise no real PII content)?

If quality is acceptable, proceed. If not, **stop, fix prompts/scenarios, `rm train/dataset.jsonl`, rerun stage 1 + 2.**

- [ ] **Step 3: Commit marker**

```bash
git commit --allow-empty -m "$(cat <<'EOF'
Phase 1 stage 2 (validate generation) passed

16 examples total. Sampled 5/class; quality is acceptable for
proceeding to the full 200-example run.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Stage 3 — full generation

**Files:** `train/dataset.jsonl` completed.

- [ ] **Step 1: Run the full generation**

```bash
python3 train/generate_dataset.py
```

This generates the remaining 184 scenarios (50/class × 4 = 200 total minus the 16 already done). Expect ~12-15 minutes of wall time and ~$0.15-0.20 of Gemini API cost.

Expected final summary:
```
Generated: 184
Skipped (already in file): 16
Failed: 0
```

- [ ] **Step 2: Verify counts**

```bash
wc -l train/dataset.jsonl
```
Expected: `200 train/dataset.jsonl`.

```bash
python3 -c "
import json
counts = {}
for line in open('train/dataset.jsonl'):
    row = json.loads(line)
    counts[row['label']] = counts.get(row['label'], 0) + 1
for label, n in sorted(counts.items()):
    print(f'{label}: {n}')
"
```
Expected:
```
block_transfer: 50
classify_safe: 50
flag_pii: 50
request_permission: 50
```

If any class is short, rerun the generator (it'll fill in the missing ones via resume logic). If a class is over 50, something's wrong with the deduplication — investigate.

- [ ] **Step 3: Commit marker**

```bash
git commit --allow-empty -m "$(cat <<'EOF'
Phase 1 stage 3 (full generation) complete

200 examples in train/dataset.jsonl, 50 per class. Dataset is
ready for Phase 2 training (when that spec lands).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Implement `eval.py`

**Files:**
- Create: `eval.py` (repo root)

- [ ] **Step 1: Create eval.py**

Create `/Users/excallibur/dev/aegis/eval.py` with this exact content:

```python
"""
Generalized eval runner for Aegis base models.

Runs one model through the eval set (12 hand-curated real samples in samples/),
reports per-class P/R/F1, accuracy, macro F1, confusion matrix, and warm-call
latency p50/p95/p99 (cold-start reported separately).

Supports two protocols:
  - bridge: POST to a running aegis_bridge.py /classify (generative models)
  - knn:    POST to Ollama /api/embed directly, k-NN against labeled set (embeddings)

Usage:
    # Generative model via bridge (bridge must already be running with --model <tag>)
    python eval.py --model gemma4:31b --protocol bridge

    # Embedding model directly (no bridge needed)
    python eval.py --model embeddinggemma --protocol knn

    # Auto-detect: if model name contains "embed", use knn; else bridge.
    python eval.py --model embeddinggemma   # -> knn
    python eval.py --model gemma4:e2b        # -> bridge

Output:
    docs/eval-results/<YYYY-MM-DD>-<model-tag>-base.txt
"""

import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

# Optional numpy — only needed for the knn protocol. Import lazily.
def _import_numpy():
    try:
        import numpy as np
        return np
    except ImportError:
        print("ERROR: numpy is required for --protocol knn. Run via `uv run python eval.py ...`.", file=sys.stderr)
        sys.exit(1)


# Hand-curated samples — must match what existed for Phase 0.
CASES = [
    ("samples/open_source_readme.md",      "classify_safe"),
    ("samples/marketing_copy.txt",         "classify_safe"),
    ("samples/blog_post_draft.txt",        "classify_safe"),
    ("samples/patient_records.csv",        "flag_pii"),
    ("samples/employee_directory.json",    "flag_pii"),
    ("samples/user_database.json",         "flag_pii"),
    ("samples/api_config.env",             "block_transfer"),
    ("samples/kubernetes_secrets.yaml",    "block_transfer"),
    ("samples/docker_compose_prod.yml",    "block_transfer"),
    ("samples/vendor_evaluation.txt",      "request_permission"),
    ("samples/partnership_agreement.txt",  "request_permission"),
    ("samples/board_meeting_minutes.txt",  "request_permission"),
]

LABELS = ["classify_safe", "flag_pii", "block_transfer", "request_permission"]

DEFAULT_BRIDGE_URL = "http://127.0.0.1:7523"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
MAX_INPUT_CHARS = 8000


# ── Per-protocol classifiers ─────────────────────────────────────────────────

def classify_via_bridge(bridge_url: str, text: str) -> tuple[str, float, float]:
    """Return (predicted_tool, confidence, wall_ms)."""
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(
        f"{bridge_url}/classify",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    start = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    wall_ms = (time.time() - start) * 1000
    tool = data.get("tool", "request_permission")
    confidence = float(data.get("confidence", 0.0))
    return tool, confidence, wall_ms


def embed_text(ollama_url: str, model: str, text: str):
    """Call Ollama /api/embed and return (embedding_vector, wall_ms)."""
    payload = json.dumps({"model": model, "input": text[:MAX_INPUT_CHARS]}).encode("utf-8")
    req = urllib.request.Request(
        f"{ollama_url}/api/embed",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    start = time.time()
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read())
    wall_ms = (time.time() - start) * 1000
    np = _import_numpy()
    return np.array(data["embeddings"][0], dtype=np.float32), wall_ms


# ── Metrics ──────────────────────────────────────────────────────────────────

def f1_for_class(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return precision, recall, f1


def percentile(values: list[float], p: float) -> float:
    """p in [0, 100]. Returns NaN-like value (0.0) if values is empty."""
    if not values:
        return 0.0
    sorted_vals = sorted(values)
    k = (len(sorted_vals) - 1) * p / 100.0
    f = int(k)
    c = min(f + 1, len(sorted_vals) - 1)
    if f == c:
        return sorted_vals[f]
    return sorted_vals[f] + (sorted_vals[c] - sorted_vals[f]) * (k - f)


# ── Main ─────────────────────────────────────────────────────────────────────

def auto_protocol(model: str) -> str:
    """Heuristic: model names containing 'embed' use knn, otherwise bridge."""
    return "knn" if "embed" in model.lower() else "bridge"


def load_eval_texts() -> list[tuple[str, str, str]]:
    """Return [(path, label, text)] for every CASE. Skip missing files with a warning."""
    out = []
    for path, label in CASES:
        try:
            with open(path, "r", errors="replace") as f:
                text = f.read()
            out.append((path, label, text))
        except OSError as e:
            print(f"WARNING: skipping {path}: {e}", file=sys.stderr)
    return out


def main():
    parser = argparse.ArgumentParser(description="Aegis eval runner")
    parser.add_argument("--model", required=True, help="Ollama model tag (e.g., gemma4:e2b, embeddinggemma)")
    parser.add_argument(
        "--protocol",
        choices=["bridge", "knn", "auto"],
        default="auto",
        help="bridge = POST to running aegis_bridge.py /classify; knn = direct Ollama /api/embed + k-NN LOO-CV",
    )
    parser.add_argument("--bridge-url", default=DEFAULT_BRIDGE_URL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument(
        "--warmup-calls",
        type=int,
        default=1,
        help="Throwaway calls before timing (default 1)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("docs/eval-results"),
        help="Where to write the per-model log",
    )
    args = parser.parse_args()

    protocol = auto_protocol(args.model) if args.protocol == "auto" else args.protocol
    print(f"[eval] model={args.model} protocol={protocol}")

    cases = load_eval_texts()
    if len(cases) < 4:
        print(f"ERROR: only {len(cases)} eval cases loaded; need at least 4 (one per class).", file=sys.stderr)
        sys.exit(1)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    out_path = args.output_dir / f"{date.today().isoformat()}-{args.model.replace(':', '-').replace('/', '-')}-base.txt"

    # ── Warm-up ──
    cold_start_ms = 0.0
    if args.warmup_calls > 0:
        warmup_text = cases[0][2]
        if protocol == "bridge":
            t0 = time.time()
            try:
                classify_via_bridge(args.bridge_url, warmup_text)
            except Exception as e:
                print(f"ERROR: bridge unreachable for warmup: {e}", file=sys.stderr)
                sys.exit(1)
            cold_start_ms = (time.time() - t0) * 1000
        else:
            t0 = time.time()
            try:
                embed_text(args.ollama_url, args.model, warmup_text)
            except Exception as e:
                print(f"ERROR: Ollama embed failed during warmup: {e}", file=sys.stderr)
                sys.exit(1)
            cold_start_ms = (time.time() - t0) * 1000
        for _ in range(args.warmup_calls - 1):
            if protocol == "bridge":
                classify_via_bridge(args.bridge_url, warmup_text)
            else:
                embed_text(args.ollama_url, args.model, warmup_text)
        print(f"[eval] warm-up done ({args.warmup_calls} call(s)), cold_start_ms={cold_start_ms:.0f}")

    # ── Eval loop ──
    rows = []  # (path, expected, predicted, confidence, latency_ms)
    warm_latencies = []

    if protocol == "bridge":
        for path, expected, text in cases:
            tool, confidence, wall_ms = classify_via_bridge(args.bridge_url, text)
            rows.append((path, expected, tool, confidence, wall_ms))
            warm_latencies.append(wall_ms)
            mark = "OK" if tool == expected else "XX"
            print(f"  {mark} {path:42s} expected={expected:22s} got={tool:22s} ({wall_ms:.0f}ms)")
    else:  # knn
        np = _import_numpy()
        # Embed every case + measure latency for each
        embeddings = []
        for path, expected, text in cases:
            vec, wall_ms = embed_text(args.ollama_url, args.model, text)
            embeddings.append(vec)
            warm_latencies.append(wall_ms)
        X = np.stack(embeddings)
        norms = np.linalg.norm(X, axis=1, keepdims=True)
        Xn = X / np.clip(norms, 1e-12, None)
        sim = Xn @ Xn.T
        np.fill_diagonal(sim, -np.inf)
        for i, (path, expected, _text) in enumerate(cases):
            nbr = int(np.argmax(sim[i]))
            predicted = cases[nbr][1]
            confidence = float(sim[i, nbr])
            rows.append((path, expected, predicted, confidence, warm_latencies[i]))
            mark = "OK" if predicted == expected else "XX"
            print(f"  {mark} {path:42s} expected={expected:22s} got={predicted:22s} sim={confidence:.2f} ({warm_latencies[i]:.0f}ms)")

    # ── Aggregate ──
    tp = {k: 0 for k in LABELS}
    fp = {k: 0 for k in LABELS}
    fn = {k: 0 for k in LABELS}
    correct = 0
    confusion = {k: {kk: 0 for kk in LABELS} for k in LABELS}
    for _path, expected, predicted, _conf, _ms in rows:
        if predicted in LABELS:
            confusion[expected][predicted] += 1
        if predicted == expected:
            correct += 1
            tp[expected] += 1
        else:
            fp[predicted] = fp.get(predicted, 0) + 1
            fn[expected] = fn.get(expected, 0) + 1
    accuracy = correct / len(rows) if rows else 0.0
    macro_f1 = 0.0
    per_class = []
    for k in LABELS:
        p, r, f1 = f1_for_class(tp[k], fp[k], fn[k])
        per_class.append((k, p, r, f1))
        macro_f1 += f1
    macro_f1 /= len(LABELS)

    p50 = percentile(warm_latencies, 50)
    p95 = percentile(warm_latencies, 95)
    p99 = percentile(warm_latencies, 99)

    # ── Format the log file ──
    lines = []
    lines.append(f"Aegis base-model eval")
    lines.append(f"Date:     {date.today().isoformat()}")
    lines.append(f"Model:    {args.model}")
    lines.append(f"Protocol: {protocol}")
    lines.append(f"Cases:    {len(rows)}")
    lines.append(f"Warmup:   {args.warmup_calls} call(s); cold_start_ms={cold_start_ms:.0f}")
    lines.append("")
    lines.append(f"{'file':42s} {'expected':22s} {'predicted':22s} {'conf':>5s} {'ms':>7s}")
    lines.append("-" * 105)
    for path, expected, predicted, conf, ms in rows:
        mark = "OK" if predicted == expected else "XX"
        lines.append(f"{mark} {path:39s} {expected:22s} {predicted:22s} {conf:5.2f} {ms:7.0f}")
    lines.append("")
    lines.append(f"{'class':24s} {'P':>6s} {'R':>6s} {'F1':>6s}")
    lines.append("-" * 50)
    for k, p, r, f1 in per_class:
        lines.append(f"{k:24s} {p:6.2f} {r:6.2f} {f1:6.2f}")
    lines.append("")
    lines.append("Confusion matrix (rows=expected, cols=predicted):")
    header = "             " + " ".join(f"{k[:10]:>10s}" for k in LABELS)
    lines.append(header)
    for row_label in LABELS:
        cells = " ".join(f"{confusion[row_label][col]:10d}" for col in LABELS)
        lines.append(f"{row_label:12s} {cells}")
    lines.append("")
    lines.append(f"Accuracy:                {accuracy:.2%} ({correct}/{len(rows)})")
    lines.append(f"Macro F1:                {macro_f1:.3f}")
    lines.append(f"Warm latency p50:        {p50:.0f} ms")
    lines.append(f"Warm latency p95:        {p95:.0f} ms")
    lines.append(f"Warm latency p99:        {p99:.0f} ms")
    lines.append(f"Cold start (1 throwaway): {cold_start_ms:.0f} ms")
    text = "\n".join(lines) + "\n"

    with out_path.open("w") as f:
        f.write(text)
    print()
    print(text)
    print(f"[eval] wrote {out_path}")
    sys.exit(0 if accuracy > 0.0 else 1)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Syntax check**

```bash
python3 -c "import ast; ast.parse(open('eval.py').read()); print('OK')"
```

Expected: `OK`.

- [ ] **Step 3: Help text smoke**

```bash
python3 eval.py --help
```

Expected: argparse help, mentions `--model`, `--protocol`, `--bridge-url`, `--ollama-url`, `--warmup-calls`.

- [ ] **Step 4: Commit**

```bash
git add eval.py
git commit -m "$(cat <<'EOF'
Add generalized eval runner

Single script for evaluating any base model against the 12 hand-
curated samples. Two protocols: 'bridge' POSTs to aegis_bridge.py
/classify (generative models), 'knn' calls Ollama /api/embed
directly and runs k-NN LOO-CV (embedding models). Auto-selects
based on model name (contains 'embed' -> knn).

Outputs per-case rows, per-class P/R/F1, confusion matrix, and
warm-only latency p50/p95/p99 with cold-start reported separately.
Per-model log written to docs/eval-results/.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Smoke test `eval.py` against `gemma4:31b`

**Files:** `docs/eval-results/<date>-gemma4-31b-base.txt` written (committable).

- [ ] **Step 1: Make sure Ollama is running and `gemma4:31b` is pulled**

```bash
curl -sf http://127.0.0.1:11434/api/tags | python3 -c "import sys, json; d=json.load(sys.stdin); print([m['name'] for m in d.get('models', [])])"
```

Expected: list includes `gemma4:31b` (already pulled in the migration work).

- [ ] **Step 2: Start the bridge with gemma4:31b**

In a separate terminal (or as a background job):

```bash
pkill -f aegis_bridge.py 2>/dev/null; sleep 1
python3 aegis_bridge.py --model gemma4:31b > /tmp/bridge_31b.log 2>&1 &
sleep 4
curl -s http://127.0.0.1:7523/health
```

Expected: JSON with `"status": "ok"`, `"backend": "ollama"`, `"model": "gemma4:31b"`.

- [ ] **Step 3: Run eval.py against gemma4:31b**

```bash
python3 eval.py --model gemma4:31b --protocol bridge
```

Expected (over ~5 min wall time):
- 12 per-case rows printed.
- Per-class P/R/F1, confusion matrix, accuracy, macro F1, latency percentiles.
- A log file written to `docs/eval-results/<date>-gemma4-31b-base.txt`.
- Accuracy should be roughly in line with Phase 0 (we saw 7/8 on the smoke test = 87.5%; 12 cases may show similar).

- [ ] **Step 4: Stop the bridge**

```bash
pkill -f aegis_bridge.py
sleep 1
pgrep -f aegis_bridge.py || echo "bridge stopped"
```

Expected: `bridge stopped`.

- [ ] **Step 5: Commit the log**

```bash
git add docs/eval-results/*-gemma4-31b-base.txt
git commit -m "$(cat <<'EOF'
Add gemma4:31b base eval log (Phase 1 smoke)

Smoke-tested the eval.py runner end-to-end against gemma4:31b on
the 12 hand-curated samples. Confirms the bridge protocol path,
warm-up + warm-only latency reporting, and scorecard log format.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 8: Run base evals for the 3 candidate models

**Files:** 3 new logs in `docs/eval-results/`.

- [ ] **Step 1: Run eval for gemma4:e2b**

```bash
pkill -f aegis_bridge.py 2>/dev/null; sleep 1
python3 aegis_bridge.py --model gemma4:e2b > /tmp/bridge_e2b.log 2>&1 &
sleep 4
curl -s http://127.0.0.1:7523/health
python3 eval.py --model gemma4:e2b --protocol bridge
pkill -f aegis_bridge.py
```

Expected: log file `docs/eval-results/<date>-gemma4-e2b-base.txt` with accuracy roughly matching Phase 0 (58%, macro F1 0.51).

- [ ] **Step 2: Run eval for functiongemma**

```bash
pkill -f aegis_bridge.py 2>/dev/null; sleep 1
python3 aegis_bridge.py --model functiongemma > /tmp/bridge_fg.log 2>&1 &
sleep 4
curl -s http://127.0.0.1:7523/health
python3 eval.py --model functiongemma --protocol bridge
pkill -f aegis_bridge.py
```

Expected: log file `docs/eval-results/<date>-functiongemma-base.txt`. Phase 0 saw 25%, expect similar.

- [ ] **Step 3: Run eval for embeddinggemma (no bridge needed for this protocol)**

```bash
python3 eval.py --model embeddinggemma --protocol knn
```

Note: `--protocol knn` is auto-selected because the model name contains "embed", but pass explicitly for clarity. The bridge does NOT need to be running for this protocol.

Expected: log file `docs/eval-results/<date>-embeddinggemma-base.txt`. Phase 0 saw 75%, expect similar.

- [ ] **Step 4: Verify all 3 logs exist**

```bash
ls -la docs/eval-results/$(date +%Y-%m-%d)-*-base.txt
```

Expected: 4 files (the gemma4-31b smoke from Task 7 plus the 3 new ones from this task).

- [ ] **Step 5: Commit the 3 base-model logs**

```bash
git add docs/eval-results/*-gemma4-e2b-base.txt \
        docs/eval-results/*-functiongemma-base.txt \
        docs/eval-results/*-embeddinggemma-base.txt
git commit -m "$(cat <<'EOF'
Add Phase 1 base-model eval logs

Three base models evaluated against the 12 hand-curated samples
using the unified eval.py runner. Logs include per-case rows,
per-class P/R/F1, confusion matrix, and warm-only latency
percentiles with cold-start reported separately.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 9: Write `docs/eval-results/scorecard.md`

**Files:** Create: `docs/eval-results/scorecard.md`.

- [ ] **Step 1: Extract the numbers from each per-model log**

Run:

```bash
python3 -c "
import re, sys
from pathlib import Path
logs = sorted(Path('docs/eval-results').glob('*-base.txt'))
for log in logs:
    text = log.read_text()
    name = log.stem.replace('-base', '')
    acc = re.search(r'Accuracy:\s*([\d.]+)%', text)
    f1 = re.search(r'Macro F1:\s*([\d.]+)', text)
    p50 = re.search(r'p50:\s*(\d+)', text)
    p95 = re.search(r'p95:\s*(\d+)', text)
    p99 = re.search(r'p99:\s*(\d+)', text)
    cold = re.search(r'Cold start[^:]*:\s*(\d+)', text)
    print(f'{name:50s} acc={acc.group(1) if acc else \"?\"}% f1={f1.group(1) if f1 else \"?\"} p50={p50.group(1) if p50 else \"?\"}ms p95={p95.group(1) if p95 else \"?\"}ms p99={p99.group(1) if p99 else \"?\"}ms cold={cold.group(1) if cold else \"?\"}ms')
"
```

Use the output of that command to fill in the scorecard in Step 2.

- [ ] **Step 2: Create `docs/eval-results/scorecard.md`**

Substitute the actual numbers from Step 1 for the `<...>` placeholders below.

```markdown
# Aegis Base-Model Scorecard

**Phase:** Phase 1 (base-model eval, no training)
**Eval set:** 12 hand-curated real samples in `samples/` (3 per verdict class)
**Date:** <YYYY-MM-DD>
**Hardware:** local M-class Mac
**Spec:** [`docs/superpowers/specs/2026-05-16-base-model-eval-pipeline-design.md`](../superpowers/specs/2026-05-16-base-model-eval-pipeline-design.md)

## Results

| Model | Protocol | Accuracy | Macro F1 | Cold start | Warm p50 | Warm p95 | Warm p99 | Notes |
|---|---|---|---|---|---|---|---|---|
| `gemma4:31b` (current prod) | bridge | <X>% | <X.XX> | <X>ms | <X>ms | <X>ms | <X>ms | Strongest accuracy; slowest |
| `gemma4:e2b` (untuned) | bridge | <X>% | <X.XX> | <X>ms | <X>ms | <X>ms | <X>ms | Confidently-wrong false negatives |
| `functiongemma` (untuned) | bridge | <X>% | <X.XX> | <X>ms | <X>ms | <X>ms | <X>ms | Collapses to one class (untuned LM behavior) |
| `embeddinggemma` (k=1 NN LOO-CV) | knn | <X>% | <X.XX> | <X>ms | <X>ms | <X>ms | <X>ms | Strong on flag_pii/block_transfer/request_permission; heterogeneous safe corpus is the failure mode |

## Reading the scorecard

- **Accuracy** is on 12 samples — small N, wide confidence intervals. Treat differences ≤8pp (one case flip) as noise.
- **Cold start** = first call after model load. Operational concern (keep models warm) but not a model-capability number.
- **Warm latency** = subsequent calls, after one throwaway warm-up.
- **The 200-sample synthetic dataset** in `train/dataset.jsonl` is reserved for Phase 2 training and is **not** in the eval set.

## Phase 2 decision criteria (from spec)

- If `embeddinggemma` ≥ 85% accuracy and p95 < 500ms → Phase 2 = train an LR/MLP head on `train/dataset.jsonl`, ship as production classifier.
- If `embeddinggemma` < 85% but failure concentrated in one class → augment scenarios for that class, regenerate, re-eval.
- If all 3 base models broadly underperform → Phase 2 = FunctionGemma LoRA fine-tune.
- If any base model already hits ≥ 92% at p95 < 500ms → ship as-is, skip training.

## Recommendation

<Fill in based on the scorecard numbers. Pick the Phase 2 direction
indicated by the criteria above. If multiple paths apply or none cleanly do,
note that and recommend a next step (more eval data, prompt adjustment, etc.).>
```

- [ ] **Step 3: Commit**

```bash
git add docs/eval-results/scorecard.md
git commit -m "$(cat <<'EOF'
Add Phase 1 scorecard with base-model comparison

Side-by-side: gemma4:31b, gemma4:e2b, functiongemma, embeddinggemma
on the 12 hand-curated samples. Includes accuracy, macro F1,
cold-start latency, and warm p50/p95/p99. Decision criteria for
Phase 2 included; the recommendation row is the Phase 1 deliverable.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Done criteria

After all 9 tasks complete:

- `train/prompts.py` exists with 50 scenarios per class (verified by `assert_scenario_counts()`).
- `train/generate_dataset.py` exists and supports `--limit`.
- `train/dataset.jsonl` exists with 200 rows, 50 per class (verified by line count + per-class counts).
- `eval.py` exists at repo root and runs against any of the 3 candidate base models.
- 4 logs in `docs/eval-results/` (one per model run, including the gemma4:31b smoke).
- `docs/eval-results/scorecard.md` exists with real numbers and a recommended Phase 2 direction.
- All 9 task commit messages exist in `git log`.
- `main` branch is untouched (verify with `git log main..ollama-migration`).
- Phase 2 spec can be written based on the scorecard data.

---

## Self-review notes (not part of plan execution)

- Spec coverage: every spec section maps to at least one task. Scenario lists (spec § Components / prompts.py) → Task 1. Generator (spec § generate_dataset.py + Phased rollout) → Tasks 2-5. Eval framework (spec § eval.py + Metrics + Output formats) → Task 6. Per-model runs (spec § Per-model paths) → Tasks 7-8. Scorecard (spec § Aggregate output) → Task 9.
- No "TODO" / "TBD" / "implement later" patterns.
- Type/name consistency: `scenario_id` field is used identically in Task 2 (writes) and Task 5 (reads). `--limit` flag is consistent across Tasks 2-5. `--protocol` values (bridge/knn/auto) are consistent across Task 6 (impl) and Tasks 7-8 (usage).
