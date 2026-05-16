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
