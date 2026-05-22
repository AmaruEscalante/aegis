# INTERNAL AUDIT REPORT
## Access Control & Privileged User Review
### CONFIDENTIAL — Restricted to Audit Committee, CFO, CISO

Audit ID: IA-2025-Q4-003
Date Issued: December 12, 2025
Lead Auditor: Marcus Webb, Internal Audit
Reviewed by: Elena Vasquez, VP Information Security

---

## Executive Summary

Internal Audit conducted a privileged access review of production systems covering the period August 1 – November 30, 2025. The review identified **3 High** and **5 Medium** findings. Immediate remediation is required for all High findings.

---

## Findings

### FINDING 1 — HIGH: 14 Inactive Admin Accounts with Active Credentials

**System:** AWS Production Environment (account ID: 123456789012)
**Details:** 14 IAM user accounts associated with former employees retained Administrator-level permissions after off-boarding. Of these, 6 still had active access keys. Last usage: account "jsmith-admin" accessed S3 prod-backup bucket on 2025-10-14 — 23 days after separation date.

**Risk:** Unauthorized access to production data; potential data exfiltration vector.

**Required Action:** Disable all 14 accounts immediately; rotate shared secrets used by those accounts; conduct forensic review of jsmith-admin activity (Oct 14 log lines attached as Exhibit A).

**Owner:** CISO Elena Vasquez
**Due Date:** December 19, 2025 (1 week)

---

### FINDING 2 — HIGH: Database Production Credentials Stored in Plaintext in GitHub

**System:** github.com/example-corp/backend-api (private repo)
**Details:** Production PostgreSQL connection string including username/password found in `config/prod.yml` (commit 4a3f9b2, committed by developer account "t.nguyen" on 2025-09-03). File has not been purged from git history.

**Risk:** Any employee with repo access can authenticate directly to the production database, bypassing all access controls.

**Required Action:** Rotate database credentials immediately; purge file from git history using git-filter-repo; implement pre-commit secret scanning hook; mandatory developer training.

**Owner:** VP Engineering
**Due Date:** December 16, 2025 (4 days)

---

### FINDING 3 — HIGH: MFA Not Enforced for 8 Executive Accounts

**System:** Google Workspace, Okta SSO
**Details:** MFA enforcement policy has an exemption list originally created for legacy app compatibility. 8 accounts on the exemption list are executive mailboxes with access to board materials and financial data.

**Required Action:** Remove exemptions; migrate legacy app to SAML/OIDC; enforce MFA universally.
**Owner:** IT Operations
**Due Date:** January 6, 2026

---

## Management Response

VP Engineering: "Finding 2 is confirmed. Credentials rotated Dec 13. History purge in progress. Secret scanning hook will be deployed by Dec 20."

CISO: "Findings 1 and 3 acknowledged. Remediation plans submitted."

---

*Distribution of this report outside the Audit Committee without written CISO approval is prohibited.*
