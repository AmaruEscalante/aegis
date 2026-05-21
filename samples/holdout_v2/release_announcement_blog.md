# Relay 1.4.0 — Cleaner Retries, Faster Cold Start

We are excited to ship **Relay 1.4.0** today. This is a backward-compatible
release. It focuses on retry ergonomics, cold-start performance, and a
handful of operator-friendly improvements that surfaced during the 1.3
series.

## Highlights

- **Per-job retry policies.** You can now attach a `RetryPolicy(...)`
  decorator to any job, with configurable backoff, jitter, and a max
  attempt cap. The old global retry config still works.
- **Worker cold-start reduced ~40%.** We removed an unnecessary table
  scan during the boot-time lease reclamation step. New workers reach
  steady-state in about 180ms on a warm database, down from 300ms.
- **`relay doctor` command.** Runs a battery of checks (db version,
  required extensions, schema drift, suspicious lease backlog) and
  prints actionable advice.
- **Postgres 16 support.** All CI now runs on 14, 15, and 16. We have not
  observed any behavior differences.
- **Structured logs by default.** Logs ship as JSON; set
  `RELAY_LOG_FORMAT=text` to restore the old format.

## Migration Notes

There are no breaking changes. Apply the migration in `db/1.4.0/` after
upgrading the binary; it adds an index used by the new lease reclamation
path. The migration runs in well under a second on tables we have observed
in the wild (up to ~10M rows).

If you used the experimental `relay.retry.exponential()` helper that
shipped behind a feature flag in 1.3.3, it has been promoted to the
public surface as `RetryPolicy.exponential()`. The old import path
continues to work and will be removed in 2.0.

## Deprecations

- `relay.legacy.LegacyEnqueuer` — was already deprecated in 1.3; now
  emits a `DeprecationWarning` on import. Removal target: 2.0.

## Acknowledgements

This release was shaped by feedback from too many community members to
list individually, but a few stand out:

- @kthorn — patient bug report on the cold-start regression that started
  this whole investigation.
- @amal-r and @drebrn — for the retry-policy design discussion in #287.
- @qfeather — for shipping the `relay doctor` prototype that became this
  release's headline feature.

Thanks also to the small army of folks who tested the 1.4 release
candidates against their own workloads. We could not have shipped with
this much confidence without you.

## Getting It

- pip: `pip install -U relay-queue`
- Homebrew: `brew upgrade relay`
- Docker: `docker pull relayproject/relay:1.4.0`

Full release notes and the upgrade checklist are in the repo under
`CHANGELOG.md`. As always, issues and questions are welcome on GitHub.

Happy queueing.
