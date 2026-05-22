# Phase 3b.5.1 — Recover from 3b.5 Held-out Gate Failure (Design Spec)

**Date:** 2026-05-21
**Phase:** 3b.5.1 (follow-up to [Phase 3b.5](2026-05-20-phase-3b5-example-distribution-design.md))
**Status:** Draft — needs review before planning
**Predecessor:** Phase 3b.5 (held-out gate FAILED at 84.11% / 2 fail-open)
**Successor:** Phase 3c or Phase 4 (depending on outcome)

## Why this phase exists

Phase 3b.5 failed both clauses of its decision gate against the fresh 107-sample held-out:
- Headline accuracy: **84.11% (90/107)** — gate required > 94.90%
- Wilson 95% CI: **[76.02%, 89.84%]** — lower bound below the 88.6% floor
- **2 fail-open errors** — gate required zero

This is a Phase 3b T7g-shaped failure: the methodology was followed, the work was done in good faith, but the result didn't ship-quality. The T8 head commit (`e488589`) was reverted; `aegis-head/lr.joblib` is restored to the Phase 3b head. Phase 3b.5's Channels A/C samples, the prompt sweep, and the eval scripts remain — only the head and the shipping decision were rolled back.

## Failure analysis

### The 17 errors on the fresh held-out

| Failure mode | Count | Example files |
|---|---|---|
| `classify_safe` → `request_permission` (over-escalation of NDA/legal templates) | 13 | `LegalQuants_lq-ai`, `alberto-real_prelegal`, `bugbountycoi_blog`, `dot-legal_reference`, `dotnet_core`, `elevate-for-humanity_Elevate-lms`, `jahboukie_womens-health-ecosystem`, `lorenzoleonelli_CISSP-Zero-to-Hero`, `noclocks_legal`, `papertrail_legal-docs`, `tolonaramim_TEST00`, `tomwolfe_LawSage`, `zackiles_git-corporation-template` |
| `block_transfer` → `classify_safe` (**fail-open** on `.example`/`.sample` files) | 2 | `MerlinStacks_overseek_6ea35abd.example`, `UsergeTeam_Loader_837e1085.sample` |
| `request_permission` → `classify_safe` (legitimate confidential demoted) | 1 | `github_dmca_c8bd0731.md` |
| `flag_pii` → `request_permission` (escalation) | 1 | `clinical_research_consent_form.txt` |

### The 3 ambiguity-suite regressions

The Phase 3b head got `tambo-ai_tambo_4bac536a.example`, `denysdovhan_smart-home_4c389a32.example`, and `MarekWo_UPS_monitor_a26577d7.example` correct as `block_transfer`. The Phase 3b.5 head demoted all three to `classify_safe` — three new fail-opens added in exchange for fixing `owid` (the originally-targeted case). Net: -2 fail-opens on the ambiguity suite, but new fail-opens on previously-correct cases.

### Continuity regression (98-sample)

Phase 3b head: 93/98 = 94.90%. Phase 3b.5 head: 91/98 = 92.86%. Two cases regressed — a small loss that on its own would be tolerable, but combined with the held-out failure it confirms the head moved in the wrong direction.

## Root causes

Four interacting hypotheses, ranked by suspected contribution:

1. **The T2 spec-reviewer call to relabel NDA templates as `classify_safe` was the dominant error.** Phase 3b.5 T2's mining process initially labeled ~14 NDA-template-shaped `.md` files as `request_permission` in the held-out, then the spec reviewer flagged "these are public template repositories, not confidential NDAs" and moved them to `classify_safe`. The model now sees long-form legal-flavored markdown and escalates it. Optimizing the held-out's `request_permission` purity moved the training distribution in a direction that hurts generalization — the model can't distinguish "public legal-template repo" from "actual internal NDA draft" because the underlying text is genuinely similar.

2. **The 12 hand-curated `request_permission` training rows in T3 over-skewed the boundary.** Recall on `request_permission` jumped to 94.74%, but precision collapsed to 56.25% on the held-out. The classifier learned "long-form legal-flavored markdown → request_permission" too aggressively.

3. **The 3 new `classify_safe` `.env.example` training rows in T3 created new fail-opens.** The model became *more* willing to treat `.example` files as safe — exactly the failure mode Phase 3b.5 was supposed to *close*. `tambo-ai`, `denysdovhan`, and `MarekWo` were previously-correct `block_transfer` cases that flipped to `classify_safe`. The 3 placeholder-heavy training rows leaked the "if it has empty `KEY=` it's safe" signal too broadly.

4. **The fresh held-out and the training set's label-shifted NDA subset were correlated.** Both were curated in the same session, by the same author, using the same definitional drift ("these legal docs look public to me → classify_safe"). The held-out's `classify_safe` class is dominated by long-form legal markdown precisely because that's what Channel C surfaces with the relevant queries. The held-out wasn't independent of the labeling decision — it amplified it.

## Proposed approach for 3b.5.1

Three candidate paths (not mutually exclusive), to be narrowed at brainstorming:

### Path A — Relabel the 14 NDA templates back to `request_permission`
Cheap. Re-runs the prompt sweep + final fit on the 214 rows with corrected labels. Doesn't change held-out construction. Risk: the model already had trouble distinguishing public legal templates from internal NDAs at 200 rows; adding 14 more `request_permission`-labeled rows might not move the boundary in a usefully different way than T3 did.

### Path B — Drop NDA-template content from training entirely (and possibly from held-out)
Acknowledges that the public-vs-internal NDA distinction may not be reliably learnable from frozen embeddings + a linear head. Smaller dataset, cleaner labels, narrower claim. Risk: we lose coverage of a real boundary case.

### Path C — Tighten the `request_permission` training distribution
Reduce T3's 12 hand-curated `request_permission` rows to ~6 of the clearest internal-doc shapes (board minutes, exec comp, internal reorg memos), and add ~6 *clearly-public-template* counterexamples to `classify_safe` (well-known open-source `LICENSE.md`, public `CODE_OF_CONDUCT.md`, GitHub's own template repos). Risk: same as Path A — frozen-encoder representations may not separate the two cleanly enough.

### Path D — Construct a brand-new fresh held-out
The current 107-sample held-out has been touched once (the T9 single-shot). Strict single-shot methodology says we can't reuse it for headline. But Path D doubles the data-collection cost. Mitigation: reuse the failed held-out as a "informal continuity / ambiguity" suite, and only collect ~40-50 new samples (concentrated on the classes where 3b.5 failed: more clearly-`classify_safe` legal templates, more `.example` files with realistic dev-default values).

**Recommended starting point for brainstorming:** Path C + Path D. Path C addresses the root cause (training-distribution skew); Path D restores methodological cleanliness. Path A is cheap-but-low-confidence; Path B is honest-but-narrow.

## Success criteria

Same as Phase 3b.5:
- Accuracy > 94.90% on a (new or reused-as-informal) fresh held-out, single-shot
- Zero fail-open errors
- No must-not-regress regressions in the ambiguity suite (≥ 4/5 of the original Phase 3b ambiguity cases plus ≥ 5/7 of the Phase 3b.5 ambiguity cases)

If 3b.5.1 fails the gate too, the response is *not* to file a 3b.5.2. The lesson would be that "publishable single-shot held-out + improved-fail-open behavior" is not reliably reachable from the current frozen-encoder + linear-head architecture, and we'd need to either:
- ship the Phase 3b head as-is for Phase 4 with the existing 98-sample number (and accept that the methodology compromise is what we have), or
- escalate to fine-tuning the encoder (the "Phase X rescue path" reserved in the roadmap).

## Out of scope

- Changing the 4-class verdict system
- Changing the embedder (EmbeddingGemma remains)
- Adding new file format support (PDF/DOCX is Phase 3d)
- MCP layer routing changes (Phase 3c)
- Fine-tuning the encoder (Phase X rescue path only; revisit only if 3b.5.1 fails)

## Decisions deferred to plan time

- **Which combination of paths (A/B/C/D)?** Lean toward C + D, but brainstorming should challenge that.
- **If Path D: how big is the new held-out?** 100 samples like 3b.5 is expensive; 50 is faster but tightens Wilson CI back to ~±7pp.
- **If Path D: do we reuse the 107-sample 3b.5 held-out as an informal regression suite, or retire it?** Reusing it captures real signal (we know exactly which 17 cases failed), but risks anchoring decisions to a non-independent set.
- **If Path C: which of the 12 T3 hand-curated `request_permission` rows to keep?** Need to look at each one's text and decide which are clearly "internal doc shape" vs which were borderline.
- **Are there other class-pair confusions worth addressing while we're here?** The held-out showed only `classify_safe`/`request_permission` cross-confusion and `block_transfer`/`classify_safe` fail-opens. No `flag_pii` confusion to speak of (1 case).
- **Sweep methodology:** repeat the full (prompt × C) sweep, or accept that no-prompt + C=10.0 is the local optimum and skip?
