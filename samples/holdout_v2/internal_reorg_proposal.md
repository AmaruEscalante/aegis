# Engineering Reorganization Proposal — H1 2026
## Acme Corporation — Internal Confidential
### Distribution: CEO, CTO, VP Eng, Director of People Ops only

**Author:** Trevor Adisa (CTO)
**Date:** December 3, 2025
**Status:** DRAFT v0.6 — pending CEO approval before broader distribution
**Effective date (proposed):** February 3, 2026

---

This document proposes a reorganization of the Acme engineering org
from the current functional structure to a product-line structure. It
covers the rationale, the proposed structure, headcount implications,
the manager assignments, and the communication plan.

This is a confidential working document. Once approved by the CEO, it
will be communicated to affected managers individually, then to the
full engineering org. Until that communication, please treat this as
strictly need-to-know.

## 1. Why Now

The functional org served us well from 10 → 60 engineers. We are now
at 84 and adding ~25 next year. Specific pain:

- Platform team has become a bottleneck on every product-team change.
- Roadmap planning takes 3+ weeks per quarter because every team
  depends on every other.
- We've lost six product engineers in the last 9 months citing "lack
  of ownership over outcomes."
- The CFO's tooling spend audit found we are paying for shared
  vendors at price points that assume usage by 3 teams; we have 8.

## 2. The Proposed Structure

We move from four functional teams to **five product lines plus one
platform group**:

**Product lines (each led by an Engineering Director reporting to VP Eng):**
- Acme Core (workflow + UI shell)
- Acme Data (warehouse connectors, sync, lineage)
- Acme Insights (analytics, dashboards, exports)
- Acme Agents (the new AI agent surface)
- Acme Marketplace (third-party apps, partner program)

**Platform (reports to CTO directly):**
- Infrastructure, security, data platform, dev productivity

## 3. Headcount Implications

Current engineering: 84
Proposed allocation (post-hires through Feb):

| Group              | Eng | EM | Director |
|--------------------|-----|----|----------|
| Acme Core          | 14  | 2  | 1        |
| Acme Data          | 11  | 2  | 1        |
| Acme Insights      | 9   | 1  | 1        |
| Acme Agents        | 12  | 2  | 1        |
| Acme Marketplace   | 6   | 1  | 0 (TBD)  |
| Platform           | 18  | 3  | 1        |
| Total              | 70  | 11 | 5        |

No layoffs are proposed. Five engineers will move teams; we have
discussed proactively with each.

## 4. Director Assignments

- Acme Core: Reena Belkic (current EM, promotion)
- Acme Data: Joon-ho Park (current EM, promotion)
- Acme Insights: open — recruiting external; offer with Felicia Hong
  pending, target start Feb 15
- Acme Agents: Marek Vasquez (current Principal, lateral)
- Acme Marketplace: TBD (interim: VP Eng directly)
- Platform: Carmen Westbrook (current Director, scope adjusted)

## 5. Risks and Mitigations

- **Risk:** Insights director hire falls through.
  Mitigation: Carmen covers Insights for up to 90 days while we
  recruit. Compensation acknowledged.
- **Risk:** Engineers resist the team moves.
  Mitigation: Each affected engineer has had a 1:1 with their current
  manager AND a coffee with their proposed new manager. Two engineers
  asked to stay; we accommodated one and explained the constraint to
  the other.
- **Risk:** Roadmap continuity during the transition.
  Mitigation: Hard rule — no new initiative starts between Feb 3 and
  Feb 24. Existing work in flight continues.

## 6. Communication Plan

- **Day -3:** Affected managers told individually (T. Adisa)
- **Day -1:** Affected ICs told individually by their new manager
- **Day 0 (Feb 3):** All-hands engineering announcement; new team
  channels open; new on-call rotations active

## 7. Open Questions for CEO

1. Marketplace director — defer or accelerate the search?
2. Do we communicate this to the board before or after the all-hands?
3. People Ops bandwidth — they will be heavily involved; do we need
   to delay any of their other Q1 priorities?

— Trevor
