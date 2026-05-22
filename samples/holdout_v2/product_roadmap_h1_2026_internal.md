# H1 2026 Product Roadmap — Acme Platform
## Internal Working Document — NOT for External Distribution
### Distribution: Product, Eng, Design leadership; CEO/CTO/VPs

**Owner:** Sasha Reinholt (VP Product)
**Date:** December 18, 2025
**Status:** Locked for execution; changes require PM/EM dual sign-off

---

This roadmap covers the six months from January through June 2026.
It reflects the prioritization decisions made in the Q4 planning
cycle following the executive offsite. It is internal: nothing in
this document, including dates, is committed to customers.

## H1 Theme: "Foundations for Acme Agents"

The dominant strategic thread is preparing the platform for the
Acme Agents launch in Q3. Most H1 bets either directly enable the
agent surface or shore up gaps that the agent rollout will exacerbate.

## Workstream 1 — Agent Platform Foundations (Marek)

| Item                                  | Target  | Confidence | Dependency        |
|---------------------------------------|---------|------------|-------------------|
| Tool-calling primitive (v1)           | Feb 14  | High       | none              |
| Permission model unification          | Mar 7   | Medium     | IAM team          |
| Agent state checkpointing             | Apr 4   | Medium     | Data platform     |
| Audit log unification                 | May 16  | High       | Security review   |

**Rationale:** these four are non-negotiable for the Q3 Agents launch.
Slipping any one beyond its target pushes the Q3 launch.

## Workstream 2 — Data Platform Hardening (Joon-ho)

| Item                                  | Target  | Confidence | Dependency        |
|---------------------------------------|---------|------------|-------------------|
| Connector framework v2                | Feb 28  | High       | none              |
| CDC pipeline for top 10 connectors    | Apr 15  | Medium     | Connector v2      |
| Schema evolution support              | May 30  | Low        | CDC pipeline      |
| Backfill orchestration UI             | Jun 27  | Medium     | none              |

**Risks:** Schema evolution is "low confidence" because we have not
yet aligned on the right semantic for handling type narrowing.

## Workstream 3 — Core Product Quality (Reena)

| Item                                  | Target  | Confidence | Dependency        |
|---------------------------------------|---------|------------|-------------------|
| Performance budget enforcement        | Jan 31  | High       | none              |
| Bulk operations (10x volume)          | Mar 21  | High       | none              |
| Mobile-web redesign                   | Apr 30  | Medium     | Design system v3  |
| Settings information architecture     | Jun 13  | Medium     | none              |

## Workstream 4 — Insights & Reporting (Felicia, assuming hire)

If Felicia accepts and starts Feb 15, the Insights team commitments are:

| Item                                  | Target  | Confidence | Dependency        |
|---------------------------------------|---------|------------|-------------------|
| Custom dashboard MVP                  | Apr 15  | Medium     | Connector v2      |
| Scheduled exports v2                  | May 23  | High       | none              |
| Cross-workspace reporting             | Jun 27  | Low        | Permission model  |

If she does not accept, this workstream is paused and reassigned at
the leadership level. (Mitigation: see reorg memo.)

## Workstream 5 — Marketplace (Interim VP Eng)

Marketplace is intentionally slowed in H1. We will ship the partner
portal redesign (target Apr 18) and otherwise hold.

## Cross-Cutting

- **Internationalization:** German and Japanese live by May. French
  by June if Workstream 1 slack permits.
- **Accessibility:** WCAG 2.1 AA full-pass by April 30 is a board-
  facing commitment.

## What We Are NOT Doing in H1

The hardest part of any roadmap is what we cut. These were
specifically debated and deprioritized:

- Acme for Salesforce native integration (deferred to H2)
- Marketplace billing v2 (deferred to H2)
- Enterprise SSO redesign (deferred indefinitely; SCIM in current
  shape is adequate)
- Mobile native apps (deferred; mobile-web redesign covers most cases)

## Process for Changes

Any change to a target date, scope, or confidence rating requires:
- PM and EM dual sign-off, OR
- VP Product approval for cross-workstream impact

All changes logged in the rolling roadmap doc with author and date.

— Sasha
