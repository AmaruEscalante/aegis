# Changelog

All notable changes to this project are documented here.
This project adheres to [Semantic Versioning](https://semver.org/).

## [2.14.0] — 2026-05-10

### Added
- **Native multi-region replication** for the storage tier. New regions: `eu-west-2`, `ap-southeast-1`. See [docs/replication.md](docs/replication.md) for the consistency model.
- `client.streaming()` API for incremental result streaming. Reduces time-to-first-byte by 40-60% on large queries (#4218).
- Built-in OpenTelemetry exporters for traces and metrics. Configure via `OTEL_EXPORTER_*` env vars (#4254).
- New `--dry-run` flag on all destructive CLI commands.

### Changed
- Default request timeout raised from 30s to 60s. Set `client.timeout` explicitly if you depend on the old value.
- Bumped minimum Node version to 20 LTS. Node 18 is no longer tested.
- Error messages from the SDK now include a stable error code (e.g., `ERR_QUERY_TIMEOUT`) suitable for programmatic handling.

### Fixed
- Race condition in connection pooling that could cause hanging connections under burst load (#4267, #4271, #4283).
- Memory leak in the retry layer when a request was cancelled mid-flight (#4279).
- Incorrect `Content-Type` header on file uploads when the file extension was missing (#4291).

### Deprecated
- The `client.query.legacy()` interface is now deprecated. It will be removed in v3.0.0 (scheduled for Q4 2026). Migrate to `client.query()` per the [migration guide](docs/migration-v3.md).

### Security
- Updated `cross-spawn` transitive dependency to address CVE-2026-04891 (low severity, no exploitable code path in our usage). See [GHSA-4181](https://github.com/advisories/GHSA-4181).

---

## [2.13.2] — 2026-04-22

### Fixed
- Patch release: fix backwards-incompatible behavior change in `client.batch()` introduced in 2.13.0 (#4204). Sorry about that.

[2.14.0]: https://github.com/example/sdk/compare/v2.13.2...v2.14.0
[2.13.2]: https://github.com/example/sdk/compare/v2.13.1...v2.13.2
