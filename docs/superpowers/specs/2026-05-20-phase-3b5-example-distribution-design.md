# Phase 3b.5 — Close the `.example` Distribution Gap (Design Spec)

**Date:** 2026-05-20
**Phase:** 3b.5 (of the [Aegis roadmap](../../roadmap.md))
**Status:** Approved — ready to plan
**Predecessor:** Phase 3b (drop Ollama, 93/98 on the 98-sample held-out, merged in PR #3)
**Successor:** Phase 3c (wire `LocalBackend` into the MCP tool-call path) + Phase 4 (marketplace publish)
**Combines with:** Phase 3b.6 (originally "fresh held-out re-eval" — folded in here so the next accuracy number is publishable)

## Goal

Close the one fail-open misclassification in the current shipped head (`owid_owid-grapher_b8fa04ba.example-full`: `block_transfer` → predicted `classify_safe`) and produce a single-shot publishable accuracy number ready for Phase 4 marketplace publication.

The root cause is a training-distribution gap: only 1 of 200 training rows is `.env`-shaped, but 14 of 98 held-out rows are `.env`/`.example`-shaped (13 labeled `block_transfer`, 1 `flag_pii`). The model has not seen enough of the `.env.example` boundary to distinguish "template with placeholders → classify_safe" from "real-shaped values → block_transfer", especially in the ambiguous middle (empty `KEY=`, dev-style defaults like `db_password=postgres`).

Phase 3b.5 is the last accuracy-and-methodology work before Phase 4. It is not yet that phase.

## Success criteria

The retrained head ships iff **both** clauses hold against the **fresh 100-sample held-out, evaluated exactly once**:

1. **Accuracy > 94.90%** (the current head's number on the 98-sample set) with Wilson 95% CI lower bound ≥ 88.6% (current head's lower bound) — i.e., not just chance-noise improvement.
2. **Zero fail-open errors:** no case where `true ∈ {block_transfer, flag_pii}` is predicted as `classify_safe`.

If the gate fails, roll back to the current `aegis-head/lr.joblib`, document failures in the scorecard with hypothesized fixes, and treat 3b.5 as partial — schedule a 3b.5.1 follow-up. We do not ship a regression.

Secondary (non-gating) success signals:
- Continuity regression: re-score the existing 98-sample set, confirm no class-level recall worse than the current head.
- Ambiguity regression: ≥ 4 of the 5 current failures classified correctly under the new head (specifically: owid is the one we are committed to fixing).

## Decisions locked from brainstorming

| Decision | Choice | Rationale |
|---|---|---|
| Eval methodology | Combine 3b.5 + 3b.6: fresh 100-sample held-out, single-shot publishable | Current 98-sample set was touched twice during Phase 3b (classify_doc + no-prompt rollback); not defensible as a Phase 4 publication number |
| Training-sample source | Channel A (5-7 hand-curated) + Channel C (5-8 mined from public GitHub) | Hand-curate the most pedagogical boundary cases; mine for real-world variance. Combined ~10-15 new training rows |
| Held-out source | 100 samples, Channel C dominant (~80 mined) + ~20 hand-curated fill-ins | Real distribution at scale + controlled coverage on classes Channel C under-represents (NDAs, internal docs) |
| Decision gate | Beat 94.90% on fresh 100 + zero fail-open errors | Two-clause gate; safety story must improve, not just average accuracy |
| Prompt experiment | Re-run, full (prompt × C) CV sweep on the expanded 215-row training set | Phase 3b's prompt experiment failed because training distribution didn't cover `.example`; once that gap closes, CV becomes a more trustworthy selector. Clean methodology: select on CV, report on fresh held-out |
| Ambiguity regression suite | Add: the 5 current failures + ~5 nearby tricky `.example` files | Cheap insurance against regressing on specific known-hard cases; non-headline (informal) |
| `train/train_head.py` shape | Option A — refactor `TASK_PROMPT` to `--prompt`/`--C` CLI args; `prompt_sweep.py` writes winner; `train_head.py` reads it | Clean separation of concerns; sweep is one script, fit is another |

## Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │  TRAINING DATA  (200 → ~215 rows)            │
                    │                                              │
                    │  train/dataset.jsonl                         │
                    │    + 5-7 hand-curated .env.example rows      │
                    │    + 5-8 Channel-C mined .env.example rows   │
                    └─────────────────────┬────────────────────────┘
                                          │
                                          ▼
                ┌──────────────────────────────────────────────────┐
                │  train/prompt_sweep.py                           │
                │    Grid: 4 prompts × 3 C values = 12 cells       │
                │    StratifiedKFold(5), scoring=f1_macro          │
                │    Output: train/sweep_winner.json with          │
                │            {"prompt": str, "C": float, ...}      │
                └─────────────────────┬────────────────────────────┘
                                      │ winner
                                      ▼
                ┌──────────────────────────────────────────────────┐
                │  train/train_head.py --prompt P --C V            │
                │    Fits final LR on all ~215 rows                │
                │    Writes aegis-head/lr.joblib                   │
                └─────────────────────┬────────────────────────────┘
                                      │
                                      ▼
            ┌──────────────────────────────────────────────────────┐
            │  EVAL SURFACES (3, only one gates the ship decision) │
            │                                                      │
            │  [HEADLINE]   eval_head.py --cases-module eval_fresh │
            │                 100 fresh samples, single-shot       │
            │                                                      │
            │  [REGRESSION] eval_head.py --cases-module eval       │
            │                 Existing 98, informal continuity     │
            │                                                      │
            │  [AMBIGUITY]  eval_head.py --cases-module            │
            │                            eval_regression           │
            │                 10 hand-picked, must-not-regress     │
            └──────────────────────────────────────────────────────┘
```

Untouched: `aegis/embedding.py` (prompt machinery already exists), `aegis_bridge.py` (picks up new head automatically at startup), the MCP layer in `middleware/`, the 200 existing training rows.

## Components

### Training-set additions (~215 rows total after additions)

**Source of truth.** `train/dataset.jsonl` is gitignored — it is generated by `train/curated_data.py` (committed). New hand-curated rows are added to the existing per-class lists in `curated_data.py`. New Channel-C mined rows are loaded from their files in `samples/external/training_mined/` via a small new helper (added in plan-time) that appends them to the JSONL output. Either path keeps the training set fully reproducible from committed source.

#### Hand-curated, ~7 rows (Channel A)

Cover the explicit boundary cases the model currently fails on:

- **3 × `classify_safe` templates**: `.env.example` files where every value is an obvious placeholder. One each of these filename shapes:
  - `.env.example` with `your-api-key`, `<your-token>` style values
  - `.env.dist` with explicit `# CHANGEME` annotations
  - `.env.template` with empty values (`KEY=`) and inline comments documenting expected format
- **3 × `block_transfer` real-shaped**: `.env` files with realistically-shaped credential values (random alphanumeric of correct length for AWS access keys, Stripe `sk_live_*`, JWT tokens, GH PATs). Filenames span `.env.local`, `.env.production`, plain `.env`.
- **1 × `block_transfer` "owid-shape" ambiguous**: mixed file with empty placeholders AND dev-style defaults (`db_password=postgres`, `redis_pass=redis`, `OPENAI_API_KEY=`). This teaches the head explicitly that this shape resolves to `block_transfer`.

All hand-curated rows go through `train/generate_dataset.py`'s validators before commit.

#### Channel-C mined, ~5-8 rows

Run `tools/sample_collector.py` against the following query lists, hand-label each result:

- `path:*.env.example` (target: classify_safe candidates with `your-*` / placeholder values)
- `path:*.env.dist` (target: classify_safe with `CHANGEME` / placeholder values)
- `path:*.env.template` (target: classify_safe with empty `KEY=` values)
- `path:*.env STRIPE_SECRET_KEY OR AWS_SECRET_ACCESS_KEY` (target: block_transfer with real-shaped values, even if values are committed-public placeholders — the *shape* is what matters)

Each candidate runs through the existing class-signal regex validators and secret-pattern guards. Anything matching real-secret regex is rejected, not redacted. Borderline judgement calls get hand-resolved by reading the file.

### Fresh held-out (~100 rows, 25 per class)

#### Channel C dominant, ~80 rows

Re-use the per-class query lists from Phase 3a/3b's mining work, but with **strict de-duplication**:
- Reject any file whose SHA-256 matches any file in existing `samples/` or `samples/external/`.
- Reject any file whose `(repo, path, commit_sha)` triple matches existing `.provenance.json` records.

Storage: `samples/external/holdout_v2/{classify_safe,flag_pii,block_transfer,request_permission}/<filename>` with `.provenance.json` siblings. The `holdout_v2/` subtree keeps visual separation from the original 98 set.

#### Channel A fill-ins, ~20 rows (5 per class)

Hand-curate to plug shapes Channel C under-represents:
- `request_permission`: NDAs, M&A term sheets, internal strategic docs (rarely public)
- `block_transfer`: rare credential shapes (Vault tokens, K8s service-account JWTs, GH App private keys)
- `flag_pii`: multi-class-ambiguous edges (HR records that almost look like financial reports)
- `classify_safe`: long-form public docs that are easy to mistake for internal (e.g., open-source ADRs)

Storage: `samples/holdout_v2/`.

### `eval_fresh.py` (NEW)

Structurally identical to `eval.py`: a `CASES: list[tuple[str, str]]` list and a re-exported `LABELS` constant. Cases point at the fresh held-out files (`samples/external/holdout_v2/...` + `samples/holdout_v2/...`).

100 cases total, balanced ~25 per class.

### `eval_regression.py` (NEW)

10 hand-picked cases as a `CASES` list:
- 5 current Phase 3b failures (delphix, AgrawalVi, owid, hr_exit_interview, saas_help_center)
- ~5 nearby tricky `.example` files from the existing 98 that the current head gets right (e.g., tambo-ai, denysdovhan, melkor217) — "must not regress" guards.

### `train/eval_head.py` (refactor)

Add a CLI argument:
```
.venv/bin/python train/eval_head.py [--cases-module {eval,eval_fresh,eval_regression}]
```

Default: `eval` (preserves current behaviour). Imports the chosen module's `CASES` and `LABELS`. Otherwise unchanged.

### `train/train_head.py` (refactor — option A)

Replace the module-level `TASK_PROMPT = "none"` constant with CLI args:
```
.venv/bin/python train/train_head.py --prompt {none,classification,classify_short,classify_doc} --C 1.0
```

If `--prompt`/`--C` are omitted, fall back to reading `train/sweep_winner.json` (written by `prompt_sweep.py`). If neither flags nor file are present, error with a clear message.

Bundle metadata adds:
```python
"training_set_size": 215,
"training_set_phase": "3b.5",
"trained_at": "2026-05-20",
"selection_source": "prompt_sweep.py CV winner",
```

### `train/prompt_sweep.py` (extend)

Already exists from Phase 3b T7d. Modify to:
- Sweep the full (prompt × C) grid: `["none", "classification", "classify_short", "classify_doc"] × [0.1, 1.0, 10.0]` = 12 cells.
- Persist the winning `(prompt, C)` pair to `train/sweep_winner.json` so `train_head.py` consumes it without re-running the sweep.

## Data flow

1. **Curate (parallel):** subagents independently produce the Channel A hand-curated samples (T3), Channel C mined held-out (T2), and Channel C mined training rows (T4). Each subagent commits its own outputs with provenance.
2. **Synthesize:** human merges curated outputs into `train/dataset.jsonl` (training) and `samples/holdout_v2/` + `samples/external/holdout_v2/` (held-out). Write `eval_fresh.py` and `eval_regression.py`.
3. **Sweep:** run `prompt_sweep.py`; it writes `train/sweep_winner.json`.
4. **Train:** run `train_head.py`; it reads the winner JSON, fits final, overwrites `aegis-head/lr.joblib`.
5. **Eval (single-shot headline + two informal):** run `eval_head.py --cases-module eval_fresh` once. Then run `--cases-module eval` and `--cases-module eval_regression` for context.
6. **Decide:** apply the two-clause gate against the headline numbers only.
7. **Document:** if pass, update scorecard with the new Phase 3b.5 row + outcome; mark roadmap done. If fail, document failures and schedule 3b.5.1.

## Error handling

- **Sample collector fails to find enough files in a class:** allowed to short-fall by ≤ 2 per class. If short by more, broaden the query list or supplement with Channel A. Do not pad with synthetic duplicates.
- **Validator rejects too many candidates:** flag in the scorecard write-up — may indicate the queries are mining secret-leaked repos at higher rates than Phase 3b. No automatic redaction; reject-only.
- **Sweep selects a prompt that performs worse on held-out than no-prompt CV alternative:** this is a known failure mode from Phase 3b. The fresh held-out is single-shot, so we eat the result either way. The decision gate covers this.
- **Decision gate fails:** restore `aegis-head/lr.joblib` to the Phase 3b head (`git checkout main -- aegis-head/lr.joblib` if you haven't committed the new head, or revert the commit if you have). Re-run `eval_fresh.py` against the rolled-back head to confirm baseline holds. File 3b.5.1 with the specific failure pattern (which clause of the gate failed, which files).

## Testing

- `tests/test_eval_fresh.py` — sanity-check that `eval_fresh.CASES` is well-formed (no missing files, no label typos, balanced per-class within ±2).
- `tests/test_eval_regression.py` — same shape, plus an assertion that the 5 named Phase 3b failures are all present.
- `tests/test_train_head_cli.py` — unit-test the new CLI arg handling for `train_head.py` (e.g., missing both flags and JSON errors with a helpful message).
- All Phase 3b tests continue to pass (no regression in the test suite).

Slow tests (`@pytest.mark.slow`) NOT required for Phase 3b.5 — the existing slow tests cover the in-process pipeline and don't need retest.

## Out of scope

Explicitly NOT included in Phase 3b.5:

- PDF / DOCX support in `aegis_read` — that's Phase 3d.
- MCP layer routing changes — that's Phase 3c.
- Fine-tuning the EmbeddingGemma encoder itself — Phase X rescue path only.
- Multi-language `.env` content — current dataset is English-only and that's fine.
- Other distribution gaps beyond `.example` — only surface those if the fresh held-out reveals them; otherwise schedule for a future 3b.5.1.
- Phase 4 packaging / marketplace listing — separate phase, blocked on this one passing the gate.
- Statistical comparison to `gemma4:31b` on the fresh set — already eliminated on architecture grounds in Phase 3a; not worth ~50 min of bridge eval per run.

## Reviewable artifacts on completion

When 3b.5 lands, the following are part of the deliverable:

1. `train/curated_data.py` — extended with the new hand-curated rows. `train/dataset.jsonl` (gitignored) regenerates from it at ~215 rows; counts and per-class distribution documented in the scorecard. If a separate mined-rows helper is introduced at plan time, it's a committed file too.
2. `samples/external/holdout_v2/` and `samples/holdout_v2/` — fresh held-out files with provenance.
3. `eval_fresh.py`, `eval_regression.py` — new eval modules.
4. `train/train_head.py`, `train/prompt_sweep.py` — refactored.
5. `aegis-head/lr.joblib` — retrained head with new metadata fields.
6. `docs/eval-results/2026-05-20-phase-3b5-fresh-holdout.txt` — captured headline eval output.
7. `docs/eval-results/scorecard.md` — new Phase 3b.5 row + outcome write-up.
8. `docs/roadmap.md` — Phase 3b.5 marked done.

Open re-decisions deferred to plan time:
- Exact GitHub query lists for `sample_collector.py` (start from Phase 3b's queries, tune to avoid already-mined repos).
- The Wilson-CI overlap clause in the gate — depending on the fresh held-out's actual variance, we may revise the phrasing. Worth a fresh look when we have the numbers.
