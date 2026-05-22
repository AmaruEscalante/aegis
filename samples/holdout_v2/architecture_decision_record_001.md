# ADR 001: Use Postgres instead of MySQL

- Status: Accepted
- Date: 2024-08-14
- Deciders: Core Maintainers (@aris, @jpark, @nbenitez)
- Tags: storage, database, infra

## Context

We are bootstrapping the persistence layer for `relay`, an open-source
job queue. We need a single relational store for jobs, schedules, and
worker leases. Two candidates surfaced early:

1. MySQL 8.0 (the default in much of the Rails / PHP ecosystem we came from)
2. Postgres 15+

Our workload is write-heavy in short bursts (job enqueues), with frequent
short-lived transactions and a small number of long-running consumer
loops (`SELECT ... FOR UPDATE SKIP LOCKED`).

We also expect users to embed `relay` inside existing infrastructure, so
the choice should be friendly to the broadest range of hosting providers.

## Decision

We will adopt **Postgres 15+** as the supported store. MySQL support is
explicitly out of scope for the 1.0 line.

## Rationale

- `SKIP LOCKED` semantics in Postgres are mature, well-documented, and
  perform predictably under the kind of contention a job queue produces.
- `LISTEN` / `NOTIFY` gives us a low-latency wake-up path for idle
  consumers without requiring an external broker.
- `JSONB` with GIN indexes covers our job-arguments storage cleanly
  without forcing us to invent a separate schema-on-write layer.
- Logical replication and `pg_dump` are well-understood by ops teams.
- Managed Postgres is available on every major cloud and most PaaS
  offerings (RDS, Cloud SQL, Neon, Supabase, Render, Fly, etc).

## Consequences

- Contributors must run a local Postgres for the test suite. We document
  Docker, Homebrew, and `apt` install paths in `CONTRIBUTING.md`.
- We give up the chance to drop into existing MySQL-only shops without a
  parallel database. We accept this; the alternative was supporting two
  dialects in the queue's locking layer, which we judged a worse trade.
- Future schema migrations will use plain SQL files under `db/migrations`.
  No ORM. Tools: `psql` and `pg_prove` for tests.

## Alternatives considered

- **MySQL 8.0** — `SKIP LOCKED` exists but the lock-manager behavior under
  burst contention was less predictable in our benchmarks, and we lacked
  in-house operational experience.
- **SQLite** — fine for single-process workers, but the multi-consumer
  story is poor and we want a single supported topology.
- **Redis Streams** — beautiful for the hot path, but visibility and
  long-tail retry semantics push complexity into client code.

## Links

- Benchmark notebook: `bench/2024-08-postgres-vs-mysql.ipynb`
- Discussion thread: GitHub issue #142
