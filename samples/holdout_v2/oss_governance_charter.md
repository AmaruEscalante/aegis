# Relay Project Governance Charter

This document describes how the Relay open-source project is governed.
It is a living document; amendments follow the process in section 6.

## 1. Mission

Relay provides a small, embeddable, Postgres-backed job queue under a
permissive license. The project values:

- A stable public API across minor versions.
- A small, readable codebase that newcomers can understand in an afternoon.
- Honest documentation, including known limitations.
- A welcoming, low-drama contributor culture.

## 2. Roles

The project recognizes four roles:

### 2.1 Users

Anyone who runs Relay. Users have no governance power but are the audience
for every decision the project makes.

### 2.2 Contributors

Anyone who has had a pull request merged. Contributors may open issues,
submit pull requests, and participate in design discussions. They are
listed in `CONTRIBUTORS.md`.

### 2.3 Maintainers

Trusted contributors who have been granted commit access. Responsibilities:

- Triage incoming issues within seven days.
- Review pull requests they are tagged on.
- Uphold the code of conduct.

Maintainers are nominated by another maintainer and confirmed by simple
majority of the current maintainer set. They may step down at any time.

### 2.4 Steering Committee

A subset of maintainers (currently three) responsible for:

- Tie-breaking technical disputes.
- Approving releases.
- Managing project infrastructure (GitHub org, domain, accounts).
- Selecting new maintainers.

The Steering Committee rotates annually. Members are elected from the
maintainer pool by approval voting.

## 3. Decision-Making

We use a lazy-consensus model:

- Routine changes (bug fixes, docs, internal refactors) merge on a single
  maintainer approval.
- Public-API changes require two maintainer approvals and a 72-hour
  comment window.
- Charter changes, license changes, and breaking 1.x changes require a
  Steering Committee majority and a one-week comment window.

Vetos may be issued by any maintainer but must include a written rationale
referencing project values or technical risk. A veto can be overridden by
unanimous Steering Committee vote.

## 4. Contribution Paths

- **Documentation** — typo fixes, clearer examples, new how-tos. Reviewed
  by any maintainer.
- **Bug fixes** — issue first, PR second; tests required.
- **Features** — discussion issue first to confirm fit; design sketch
  encouraged; PR last.
- **Discussions** — open-ended brainstorming in GitHub Discussions; no
  decisions taken there.

## 5. Code of Conduct

We follow the Contributor Covenant 2.1. Reports go to
conduct@relay-project.example. Reports are confidential and handled by
two Steering Committee members not involved in the report.

## 6. Amending This Charter

Charter amendments follow the same process as 1.x-breaking changes:
Steering Committee majority + one-week comment window. Discussion in
public on the project repo.
