# Post-Incident Review: INC-2024-08-22

**Severity:** SEV-1
**Customer impact:** Full API unavailability, 84 minutes
**Region:** us-east-1 (primary), partial degradation in us-west-2
**Date:** August 22, 2024
**Author:** Trevor Adisa (CTO), with Reliability team
**Status:** FINAL — INTERNAL ONLY

---

## TL;DR

A schema migration on the `customer_quota` table acquired an
`ACCESS EXCLUSIVE` lock that backed up the API connection pool. The
deploy step that should have run the migration off-hours instead ran at
peak traffic due to a misconfigured cron entry. We failed to fail-fast
into a degraded mode; instead, the entire API tier went down.

## Timeline (all times PT)

- **09:48** — `quota-migration-022` deploy triggered via scheduled CI job.
- **09:51** — First customer reports in #status-internal.
- **09:53** — PagerDuty fires; primary on-call (Jamie) ack'd in 1m.
- **10:02** — Secondary on-call (Renata) paged; war room created.
- **10:11** — Hypothesis: bad release. Rolled back app deploy. No effect.
- **10:22** — Database team identifies long-running migration; running
  query: `ALTER TABLE customer_quota ADD COLUMN ...`. Acquired lock at
  09:48:32, still held.
- **10:31** — Decision to kill the migration. `pg_cancel_backend` issued.
  Lock released at 10:31:47.
- **10:34** — API response times return to baseline. Error rate at 0.4%.
- **11:12** — Customer-facing status page marked resolved.
- **12:00** — Internal escalation closed.

## Impact

- 84 minutes of full API unavailability
- 412 enterprise customer accounts impacted
- 7 customers issued SLA credit per contract
- Estimated revenue impact (excluding credits): negligible (subscription)
- Reputational impact: significant in the SRE community on Twitter

## Root Cause

The migration was scheduled to run at 02:48 UTC (off-peak). A change to
the deployment scheduler in July introduced a timezone bug: cron entries
authored with PT intent were being interpreted as UTC after the change.
This had been masked by other off-hours migrations that happened to be
safe at both UTC and PT times.

The migration itself was not designed for the new table size. The
`customer_quota` table grew 11x in the last six months. The migration's
naive `ALTER TABLE` approach was acceptable at the original size and
became unsafe.

## Contributing Factors

1. **No CI gate on migration runtime estimate.** We have lint rules
   that flag locking operations, but no gate that combines table size
   with operation type.
2. **No connection pool circuit breaker on lock waits.** The pool
   filled with waiters; no fast-fail to a degraded "503 with retry-after"
   response.
3. **Runbook gap.** The on-call runbook for SEV-1 did not include
   "check for long-running database lock holders" until step 4.

## Action Items

- **AI-1 (owner: M. Lin):** Fix scheduler timezone bug. Done Aug 23.
- **AI-2 (owner: J. Patel):** Add CI lint rule that blocks lockful
  migrations on tables > 10M rows without `CONCURRENTLY` keyword.
  Due Sep 5.
- **AI-3 (owner: R. Vance):** Add lock-wait timeout to the API pool
  config; return 503 with retry-after when exceeded. Due Sep 12.
- **AI-4 (owner: Reliability):** Update SEV-1 runbook to put database
  lock check at step 1. Due Aug 30.
- **AI-5 (owner: Data Platform):** Migration framework redesign with
  pt-online-schema-change-style cutover. Due Q4.

## What Went Well

- Communication in #status-internal was excellent. Decisions were made
  in the open and audit trail is clean.
- Customer Success communicated proactively; no customer required a
  follow-up call beyond the standard SLA-credit conversation.
- Roll-forward fix was clean once root cause was identified.

## What Didn't

- Detection lagged customer reports by three minutes. Our synthetic
  monitors did not catch the early lock wait.
- We attempted a full rollback before diagnosing root cause. That cost
  us 9 minutes.
- Internal escalation tree had two stale phone numbers.

— Reviewed and approved by Trevor Adisa, CTO, August 29, 2024.
