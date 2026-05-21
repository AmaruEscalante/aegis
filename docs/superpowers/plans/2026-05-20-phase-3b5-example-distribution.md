# Phase 3b.5 — Close the `.example` Distribution Gap (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the one fail-open misclassification in the current shipped head (`owid_owid-grapher_b8fa04ba.example-full` → `classify_safe`) by expanding the `.env`/`.example` training distribution from 1 of 200 rows to ~12 of ~215 rows, retrain via a (prompt × C) CV sweep, and produce a publishable single-shot accuracy number against a fresh 100-sample held-out set.

**Architecture:** No new code paths. Refactor `train/train_head.py` to take `--prompt`/`--C` CLI args (consuming a sweep winner JSON). Extend `train/prompt_sweep.py` to cover the full (4 prompts × 3 C values) grid and persist the winner. Curate ~12-15 new training rows and 100 fresh held-out samples. Run a single CV sweep, fit the final head, evaluate ONCE against the fresh held-out, apply a two-clause decision gate (accuracy > 94.90% AND zero fail-open errors).

**Tech Stack:** Python 3.12, sentence-transformers, sklearn `LogisticRegression`, `tools/sample_collector.py` (existing Channel-C mining tool), pytest.

**Workflow shape:** T2, T3, T4 (curation) run in parallel as independent subagents. T1, T5, T6 (code refactors) run serially. T7-T11 (training + eval + decision + docs) are tightly serial.

**Spec:** [`docs/superpowers/specs/2026-05-20-phase-3b5-example-distribution-design.md`](../specs/2026-05-20-phase-3b5-example-distribution-design.md)

**Rules carried over from prior phases:**
- Commits are local-only. The user is the sole gatekeeper for what reaches the remote — never `git push`, never `gh pr create`. Plan commits, not pushes.
- `.codex/` is gitignored and out of scope. Do not read, edit, or commit anything under `.codex/`.

---

## File Structure (locked at plan time)

**NEW files:**

| Path | Purpose |
|---|---|
| `eval_fresh.py` | Holds `CASES` for the fresh 100-sample held-out; same shape as `eval.py` |
| `eval_regression.py` | Holds `CASES` for the 10-row ambiguity regression suite |
| `tests/test_eval_fresh.py` | Validates `eval_fresh.CASES` structure (file existence, label balance) |
| `tests/test_eval_regression.py` | Validates `eval_regression.CASES` structure + presence of 5 Phase 3b failures |
| `tests/test_train_head_cli.py` | Unit tests for new `train_head.py` CLI arg handling + sweep-winner JSON fallback |
| `train/sweep_winner.json` | Persisted output of `prompt_sweep.py`; consumed by `train_head.py` if `--prompt`/`--C` omitted |
| `samples/external/holdout_v2/{classify_safe,flag_pii,block_transfer,request_permission}/<file>` | Channel-C mined fresh held-out files + `.provenance.json` siblings |
| `samples/holdout_v2/<file>` | Channel-A hand-curated fresh held-out files (~20) |
| `samples/external/training_mined/<file>` | Channel-C mined training rows + `.provenance.json` siblings |
| `docs/eval-results/2026-05-20-phase-3b5-fresh-holdout.txt` | Captured headline eval output |

**MODIFIED files:**

| Path | What changes |
|---|---|
| `train/train_head.py` | CLI args `--prompt`/`--C`; fallback to `train/sweep_winner.json`; new bundle metadata fields |
| `train/prompt_sweep.py` | Sweep the full (prompt × C) grid; write `train/sweep_winner.json` |
| `train/curated_data.py` | Add ~7 new hand-curated `.env.example`-style training rows |
| `train/eval_head.py` | New `--cases-module` CLI arg to switch between `eval`, `eval_fresh`, `eval_regression` |
| `aegis-head/lr.joblib` | Overwritten by the final fit (committed only if the gate passes) |
| `docs/eval-results/scorecard.md` | New Phase 3b.5 row + outcome write-up |
| `docs/roadmap.md` | Phase 3b.5 marked done (combined with 3b.6) |

---

## Task 1: Refactor `train/train_head.py` to take CLI args

**Files:**
- Modify: `train/train_head.py:34-56` (TASK_PROMPT constant + embed setup)
- Create: `tests/test_train_head_cli.py`

This is a pure refactor — no new behaviour, just turns the hard-coded `TASK_PROMPT = "none"` and `C_GRID = [0.1, 1.0, 10.0]` into things controllable from the command line, with a JSON-file fallback so a sweep winner can be piped in. Do this FIRST so the rest of the pipeline can rely on it.

- [ ] **Step 1.1: Write the failing tests**

Create `tests/test_train_head_cli.py`:

```python
"""Unit tests for train/train_head.py CLI argument handling."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
TRAIN_SCRIPT = REPO_ROOT / "train" / "train_head.py"
PY = REPO_ROOT / ".venv" / "bin" / "python"


def test_help_lists_new_args():
    """--help mentions both --prompt and --C."""
    result = subprocess.run(
        [str(PY), str(TRAIN_SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "--prompt" in result.stdout
    assert "--C" in result.stdout


def test_missing_both_args_and_winner_file_errors_clearly(tmp_path, monkeypatch):
    """If no --prompt/--C AND no sweep_winner.json, exit nonzero with helpful message."""
    # Run from a fresh cwd so train/sweep_winner.json isn't found
    result = subprocess.run(
        [str(PY), str(TRAIN_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode != 0
    err = (result.stderr + result.stdout).lower()
    assert "prompt" in err and "sweep_winner.json" in err


def test_winner_file_consumed_when_flags_absent(tmp_path):
    """If train/sweep_winner.json exists and flags are absent, it's read."""
    # Build a minimal sweep_winner.json in tmp_path/train/
    train_dir = tmp_path / "train"
    train_dir.mkdir()
    winner = {"prompt": "none", "C": 1.0}
    (train_dir / "sweep_winner.json").write_text(json.dumps(winner))

    # We can't actually run the full training pipeline here (needs HF model).
    # Instead, invoke train_head.py in a --dry-run mode that prints the resolved
    # (prompt, C) without doing any model work. (Implementation note: add a
    # --dry-run flag in Step 1.3 if it doesn't already exist.)
    result = subprocess.run(
        [str(PY), str(TRAIN_SCRIPT), "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    assert '"prompt": "none"' in result.stdout or "prompt=none" in result.stdout
    assert '"C": 1.0' in result.stdout or "C=1.0" in result.stdout


def test_explicit_flags_override_winner_file(tmp_path):
    """If both --prompt and the winner file exist, --prompt wins."""
    train_dir = tmp_path / "train"
    train_dir.mkdir()
    (train_dir / "sweep_winner.json").write_text(json.dumps({"prompt": "classify_doc", "C": 10.0}))

    result = subprocess.run(
        [str(PY), str(TRAIN_SCRIPT), "--prompt", "none", "--C", "1.0", "--dry-run"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert '"prompt": "none"' in out or "prompt=none" in out
    assert '"C": 1.0' in out or "C=1.0" in out
```

- [ ] **Step 1.2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_train_head_cli.py -v`
Expected: 4 failures — the script has no `--prompt`, `--C`, or `--dry-run` args yet.

- [ ] **Step 1.3: Implement the CLI args in `train/train_head.py`**

Replace lines 34-56 of `train/train_head.py` (the `# ── Config ──` block + `TASK_PROMPT` + `_get_embedder` setup) with:

```python
# ── Config ──────────────────────────────────────────────────────────
DATASET_PATH = pathlib.Path("train/dataset.jsonl")
HEAD_PATH = pathlib.Path("aegis-head/lr.joblib")
WINNER_PATH = pathlib.Path("train/sweep_winner.json")
EMBED_DIM = 768
RANDOM_SEED = 42
DEFAULT_C_GRID = [0.1, 1.0, 10.0]
VALID_PROMPTS = ("none", "classification", "classify_short", "classify_doc")


def _parse_args() -> tuple[str, float, bool]:
    """Resolve (prompt, C, dry_run) from CLI flags or sweep_winner.json.

    Resolution order:
      1. Explicit --prompt / --C flags
      2. train/sweep_winner.json (if present)
      3. Error
    """
    import argparse
    parser = argparse.ArgumentParser(description="Train the Aegis LR head.")
    parser.add_argument("--prompt", choices=VALID_PROMPTS, default=None,
                        help="Task-prompt variant (overrides sweep_winner.json).")
    parser.add_argument("--C", type=float, default=None,
                        help="Regularization strength (overrides sweep_winner.json).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print resolved (prompt, C) and exit without training.")
    args = parser.parse_args()

    prompt: str | None = args.prompt
    C: float | None = args.C

    if prompt is None or C is None:
        if WINNER_PATH.exists():
            try:
                winner = json.loads(WINNER_PATH.read_text())
            except (json.JSONDecodeError, OSError) as e:
                print(f"ERROR: failed to read {WINNER_PATH}: {e}", file=sys.stderr)
                sys.exit(2)
            if prompt is None:
                prompt = winner.get("prompt")
            if C is None:
                C = winner.get("C")

    if prompt is None or C is None:
        print(
            "ERROR: must supply --prompt and --C, or run train/prompt_sweep.py first to\n"
            f"produce {WINNER_PATH} (consumed automatically when flags are omitted).",
            file=sys.stderr,
        )
        sys.exit(2)

    if prompt not in VALID_PROMPTS:
        print(f"ERROR: invalid prompt {prompt!r}; valid: {VALID_PROMPTS}", file=sys.stderr)
        sys.exit(2)

    return prompt, float(C), args.dry_run


# Resolved at module load via _parse_args() in __main__
TASK_PROMPT: str = "none"  # placeholder; real value set at runtime
SELECTED_C: float = 1.0     # placeholder; real value set at runtime

_EMBEDDER: Embedder | None = None


def _get_embedder() -> Embedder:
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = Embedder(default_task=TASK_PROMPT)
    return _EMBEDDER


def embed_text(text: str) -> np.ndarray:
    """Embed via the shared in-process Embedder. Returns (768,) float32."""
    return _get_embedder().encode(text, task=TASK_PROMPT)
```

Then update the `if __name__ == "__main__":` block (currently around line 152) to wire in the CLI args:

```python
if __name__ == "__main__":
    TASK_PROMPT, SELECTED_C, DRY_RUN = _parse_args()

    if DRY_RUN:
        # Print resolved config and exit — used by tests + sanity checks.
        print(json.dumps({"prompt": TASK_PROMPT, "C": SELECTED_C}, indent=2))
        sys.exit(0)

    if not DATASET_PATH.exists():
        print(f"ERROR: {DATASET_PATH} not found. Run `python3 train/curated_data.py` first.", file=sys.stderr)
        sys.exit(1)

    # --- Embed
    X, y, ids = embed_dataset(DATASET_PATH)

    # Sanity prints
    print(f"\nX shape: {X.shape}    dtype: {X.dtype}")
    print(f"y shape: {y.shape}    classes: {sorted(set(y))}")
    print(f"per-class count: {dict((c, int((y == c).sum())) for c in sorted(set(y)))}")
    norms = np.linalg.norm(X, axis=1)
    print(f"L2 norms: min={norms.min():.4f}  mean={norms.mean():.4f}  max={norms.max():.4f}")

    # --- Skip the CV sweep — the prompt_sweep step already selected (prompt*, C*).
    print(f"\n=== Fitting head at prompt={TASK_PROMPT!r}, C={SELECTED_C} (chosen upstream) ===")
    model = fit_final(X, y, SELECTED_C)

    # --- Save
    bundle = {
        "model": model,
        "embed_model": Embedder.DEFAULT_MODEL_ID,
        "embed_task_prompt": TASK_PROMPT,
        "C": SELECTED_C,
        "training_set_phase": "3b.5",
        "training_set_size": int(X.shape[0]),
        "trained_at": time.strftime("%Y-%m-%d"),
        "selection_source": "prompt_sweep.py CV winner" if WINNER_PATH.exists() else "manual flags",
    }
    HEAD_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, HEAD_PATH)
    print(f"\nSaved trained head to {HEAD_PATH}  ({HEAD_PATH.stat().st_size/1024:.1f} KB)")
    for k in ("embed_model", "embed_task_prompt", "C", "training_set_phase", "training_set_size", "trained_at"):
        print(f"  {k}: {bundle[k]}")
```

The `sweep_C_with_cv` function (currently at line 97) is no longer called from `__main__` — leave it in place for now (other callers may use it; we'll clean up in Task 6 if it's truly orphaned).

At the top of the file, ensure `import json` is present (it's already imported per line 19; verify).

- [ ] **Step 1.4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_train_head_cli.py -v`
Expected: 4 passes.

- [ ] **Step 1.5: Commit**

```bash
git add train/train_head.py tests/test_train_head_cli.py
git commit -m "Phase 3b.5 T1 — train_head.py: CLI args --prompt/--C + sweep_winner.json fallback"
```

---

## Task 2: Channel C — mine 100 fresh held-out samples [parallelizable subagent]

**Files:**
- Create: `samples/external/holdout_v2/{classify_safe,flag_pii,block_transfer,request_permission}/<filename>` (~80 mined files)
- Create: matching `.provenance.json` siblings for each mined file
- Modify: `tools/sample_collector.py` — only if a config tweak is needed for `holdout_v2/` output path (see Step 2.2)

The goal is ~20 newly-mined files per class (80 total). They must NOT overlap with the existing 98-sample set by SHA-256 or by `(repo, path, commit_sha)` provenance triple. Hand-judgment is required for label assignment on borderline files.

**Dispatch note:** this task is independent of T3 and T4 — run them in parallel as separate subagents.

- [ ] **Step 2.1: Inspect existing `tools/sample_collector.py` to confirm output-path is configurable**

Run: `grep -nE 'samples/external|OUTPUT' tools/sample_collector.py | head -10`
If the output path is parameterized via CLI arg, proceed to Step 2.2 unchanged. If hard-coded to `samples/external/{class}/`, add an `--output-prefix` arg in Step 2.2 before running.

- [ ] **Step 2.2: Run the collector against per-class query lists into `holdout_v2/`**

Use the existing Phase 3a/3b queries, but write into `samples/external/holdout_v2/` and tag provenance to record this as a `holdout_v2/` batch.

```bash
.venv/bin/python tools/sample_collector.py \
    --target-class classify_safe \
    --target-count 20 \
    --output-prefix samples/external/holdout_v2 \
    --queries 'path:README.md stars:>100' \
              'path:docs.md stars:>50'

.venv/bin/python tools/sample_collector.py \
    --target-class flag_pii \
    --target-count 20 \
    --output-prefix samples/external/holdout_v2 \
    --queries 'path:patients.csv' \
              'path:users.csv "email"'

.venv/bin/python tools/sample_collector.py \
    --target-class block_transfer \
    --target-count 20 \
    --output-prefix samples/external/holdout_v2 \
    --queries 'path:*.env STRIPE_SECRET_KEY OR AWS_SECRET_ACCESS_KEY' \
              'path:*.env.production' \
              'path:credentials.ini'

.venv/bin/python tools/sample_collector.py \
    --target-class request_permission \
    --target-count 20 \
    --output-prefix samples/external/holdout_v2 \
    --queries 'path:nda.md OR path:non-disclosure.md' \
              'path:term-sheet.md'
```

If a class falls short by ≤2 files, allow it; Channel A fill-ins in T3 will compensate. If short by more, broaden the queries (e.g., add `OR path:non_disclosure.md`) rather than padding with duplicates.

- [ ] **Step 2.3: De-duplicate against existing 98-sample set**

Write a one-off check script (do not commit it) or run inline:

```bash
.venv/bin/python -c "
import hashlib, pathlib, json, sys

existing = set()
for p in pathlib.Path('samples/external').rglob('*'):
    if p.is_file() and not p.name.endswith('.provenance.json') and 'holdout_v2' not in str(p):
        existing.add(hashlib.sha256(p.read_bytes()).hexdigest())
for p in pathlib.Path('samples').glob('*'):
    if p.is_file():
        existing.add(hashlib.sha256(p.read_bytes()).hexdigest())

dupes = []
for p in pathlib.Path('samples/external/holdout_v2').rglob('*'):
    if p.is_file() and not p.name.endswith('.provenance.json'):
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        if h in existing:
            dupes.append(str(p))

if dupes:
    print('FAIL: SHA-256 duplicates found:')
    for d in dupes:
        print(f'  {d}')
    sys.exit(1)
print(f'OK: 0 duplicates across {len(list(pathlib.Path(\"samples/external/holdout_v2\").rglob(\"*\")))} new files')
"
```

Expected: `OK: 0 duplicates ...`. If dupes are found, delete them and re-mine that class until clean.

- [ ] **Step 2.4: Spot-check label assignments**

For each class, open 3 random samples and confirm the label assignment is correct. Mining is regex-driven and noisy — every batch has 1-2 mislabels. Re-label or delete as needed. This is human-judgment work, not automated.

- [ ] **Step 2.5: Commit**

```bash
git add samples/external/holdout_v2/
git commit -m "Phase 3b.5 T2 — mine ~80 fresh held-out samples (Channel C) into holdout_v2/"
```

---

## Task 3: Channel A — hand-curate held-out + training samples [parallelizable subagent]

**Files:**
- Create: `samples/holdout_v2/<filename>` (~20 hand-curated held-out files, 5 per class)
- Modify: `train/curated_data.py` — append ~7 new rows to the per-class lists

**Dispatch note:** runs in parallel with T2 and T4. T3 produces BOTH new training rows (in `curated_data.py`) AND new held-out files (in `samples/holdout_v2/`).

- [ ] **Step 3.1: Add new training rows to `train/curated_data.py`**

Open `train/curated_data.py`. Locate the `CLASSIFY_SAFE` and `BLOCK_TRANSFER` lists. Append the following 7 new entries with comments matching the existing pattern (look at the existing `# 0. README.md for ...` style comments).

Add to `CLASSIFY_SAFE` (3 new rows):

```python
    # 50. .env.example with "your-*" placeholder values throughout
    """# Example environment configuration
# Copy to .env and replace placeholders with real values.

DATABASE_URL=postgresql://your-db-user:your-db-password@your-db-host:5432/your-db-name
REDIS_URL=redis://your-redis-host:6379/0
SECRET_KEY=your-secret-key-min-32-characters
JWT_SECRET=your-jwt-secret-min-32-characters

# Third-party API keys (sign up at the provider to obtain these)
STRIPE_SECRET_KEY=sk_test_your-stripe-test-key-here
SENDGRID_API_KEY=your-sendgrid-api-key
OPENAI_API_KEY=your-openai-api-key

# Feature flags (true/false)
ENABLE_BETA_FEATURES=false
""",
    # 51. .env.dist with explicit CHANGEME markers
    """# .env.dist — checked-in template. Copy to .env before running.

# Database
PG_HOST=localhost
PG_USER=app
PG_PASSWORD=CHANGEME
PG_DB=app_dev

# Auth
SESSION_SECRET=CHANGEME-AT-LEAST-32-CHARS
ADMIN_BOOTSTRAP_TOKEN=CHANGEME

# External services
SMTP_HOST=smtp.example.com
SMTP_USER=CHANGEME
SMTP_PASS=CHANGEME
""",
    # 52. .env.template with empty KEY= placeholders and inline documentation
    """# Production environment template
# Populate every key below before deploying.
# DO NOT commit a filled-in copy.

# Required: Postgres connection
DATABASE_HOST=
DATABASE_PORT=5432
DATABASE_USER=
DATABASE_PASSWORD=
DATABASE_NAME=

# Required: Redis (for sessions + job queue)
REDIS_HOST=
REDIS_PORT=6379

# Required: AWS S3 (for asset uploads)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_S3_BUCKET=

# Optional: Sentry error tracking
SENTRY_DSN=
""",
```

Add to `BLOCK_TRANSFER` (4 new rows — 3 real-shaped + 1 owid-style ambiguous):

```python
    # 50. .env.local with real-shaped credential values across multiple providers
    """# .env.local — generated 2025-12-03, DO NOT COMMIT
DATABASE_URL=postgresql://app_prod:9f4d8e7c2b1a0e6f3d8c5b9a4e7d2c1b@db-primary.internal.acme.io:5432/app_prod
REDIS_URL=rediss://default:R3d1s_Pr0d_T0k3n_8K2nM4pL9vQ@redis-cluster-0.internal.acme.io:6380/0
SECRET_KEY=zX9mP3kQ7nL2vR8tY5jH1fG4dB6cA0eW
JWT_SIGNING_KEY=eyJzdWIiOiJzZWNyZXQiLCJpYXQiOjE3MzM0MjA4MDB9.RealLookingJwtSignatureValueGoesHere
STRIPE_SECRET_KEY=sk_live_FAKE_TRAINING_KEY_DO_NOT_USE
SENDGRID_API_KEY=SG.7nQ3pM4kR2vL9wY8jH5fG1dB0cA6eX.tK8mN5pQ3rS7vL2wY9jH4fG6dB1cA0e
""",
    # 51. .env.production with realistic AWS / GitHub / Twilio values
    """# .env.production — DO NOT COMMIT — DO NOT SHARE
AWS_ACCESS_KEY_ID=AKIAQ7XK4PL5N8M2RJ9V
AWS_SECRET_ACCESS_KEY=hT3kP9mN8qL2rS5vW7jY4fG6dB1cA0eX9zM4pK2nL5wQ
AWS_DEFAULT_REGION=us-west-2
S3_BUCKET=acme-prod-assets

GH_PAT=ghp_K8mN5pQ3rS7vL2wY9jH4fG6dB1cA0eX9zM4pK
GH_ORG=acme-corp

TWILIO_ACCOUNT_SID=AC8a9b7c6d5e4f3g2h1i0j9k8l7m6n5o4p3
TWILIO_AUTH_TOKEN=z9y8x7w6v5u4t3s2r1q0p9o8n7m6l5k4
TWILIO_FROM_NUMBER=+14155551234
""",
    # 52. plain .env shipped with real-shaped Postgres/Redis/JWT secrets
    """DATABASE_URL=postgresql://acme_app:P0stgr3sPr0dP@ssw0rd2024@db-cluster-east-1.internal:5432/acme_app_prod
REDIS_URL=redis://:R3d1sCach3T0k3n_2024_n0tT0Sh@r3@redis-cache.internal:6379
SESSION_SECRET=h7K9mN3pQ5rS8vL2wY6jH4fG1dB0cA9eX5zM7pK4nL8wQ
INTERNAL_API_TOKEN=int_t0k3n_p9o8n7m6l5k4j3h2g1f0e9d8c7b6a5z4y3x2
ENCRYPTION_KEY=aGVsbG93b3JsZGZyb21wcm9kZW5jcnlwdGlvbjEyMzQ1Ng==
WEBHOOK_SIGNING_SECRET=whsec_K8mN5pQ3rS7vL2wY9jH4fG6dB1cA0eX
""",
    # 53. owid-shape ambiguous: empty placeholders mixed with dev-style defaults
    """TZ=utc
ENV=development

GRAPHER_DB_NAME=grapher
GRAPHER_DB_USER=grapher
GRAPHER_DB_PASS=grapher
GRAPHER_DB_HOST=127.0.0.1
GRAPHER_DB_PORT=3307

GRAPHER_TEST_DB_PASS=graphertest
GRAPHER_TEST_DB_HOST=127.0.0.1

GDOCS_PRIVATE_KEY=
GDOCS_CLIENT_EMAIL=
GDOCS_CLIENT_ID=

OPENAI_API_KEY=
FIGMA_API_KEY=

R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=

# This shape is ambiguous: dev defaults look like real values, but most external
# keys are empty. Treat as block_transfer because the dev DB credentials (postgres/postgres,
# grapher/grapher) ARE real local credentials, not template placeholders.
""",
```

After editing, **regenerate `train/dataset.jsonl`**:

```bash
.venv/bin/python train/curated_data.py
```

Verify the new row count:

```bash
wc -l train/dataset.jsonl
```

Expected: 207 lines (was 200 + 7 new = 207).

Verify per-class balance:

```bash
.venv/bin/python -c "
import json, collections
c = collections.Counter()
for line in open('train/dataset.jsonl'):
    if line.strip():
        c[json.loads(line)['label']] += 1
for k, v in sorted(c.items()):
    print(f'  {k}: {v}')
"
```

Expected: `classify_safe: 53`, `block_transfer: 54`, `flag_pii: 50`, `request_permission: 50`.

- [ ] **Step 3.2: Hand-curate ~20 held-out files into `samples/holdout_v2/`**

Create 5 files per class. Use diverse shapes to plug gaps that Channel C tends to under-represent.

`classify_safe` (5 files): long-form public docs that could superficially look internal. Examples:
- `samples/holdout_v2/architecture_decision_record_001.md` — public ADR style
- `samples/holdout_v2/oss_governance_charter.md` — open-source project governance
- `samples/holdout_v2/conference_workshop_handout.md` — public-talk material
- `samples/holdout_v2/release_announcement_blog.md` — open-source release notes
- `samples/holdout_v2/community_code_of_conduct.txt` — CoC standard text

`flag_pii` (5 files): multi-class-ambiguous PII edges. Examples:
- `samples/holdout_v2/clinical_research_consent_form.txt` — medical PII + signatures
- `samples/holdout_v2/loan_underwriting_summary.csv` — PII + financial data
- `samples/holdout_v2/k12_grade_report.csv` — student records with parent contact
- `samples/holdout_v2/jury_summons_database.csv` — personal address + jurisdiction
- `samples/holdout_v2/health_screening_intake.txt` — name + DOB + medical history

`block_transfer` (5 files): rare credential shapes. Examples:
- `samples/holdout_v2/vault_root_token.txt` — HashiCorp Vault token
- `samples/holdout_v2/k8s_service_account.yaml` — K8s SA with embedded JWT
- `samples/holdout_v2/gh_app_private_key.pem` — GitHub App private key shape
- `samples/holdout_v2/google_service_account.json` — GCP service-account JSON
- `samples/holdout_v2/datadog_api_keys.env` — Datadog `api_key` + `app_key`

`request_permission` (5 files): internal docs Channel C rarely surfaces. Examples:
- `samples/holdout_v2/board_meeting_minutes_q3.md`
- `samples/holdout_v2/acquisition_term_sheet_draft.md`
- `samples/holdout_v2/employee_handbook_compensation_section.md`
- `samples/holdout_v2/post_incident_review_outage_2024.md`
- `samples/holdout_v2/customer_churn_analysis_q4.md`

Each file should be 30-100 lines of plausible-looking content. Use placeholder names (Acme, Initech) and dates. **Do NOT embed real PII or real credentials** — these are committed to git. For `block_transfer`, use realistically-shaped FAKE values (e.g., random alphanumeric of correct length).

Run `train/generate_dataset.py`'s validators against each file:

```bash
.venv/bin/python -c "
import pathlib
import sys
sys.path.insert(0, '.')
from train.generate_dataset import validate_content  # or whatever the validator entry point is
for p in pathlib.Path('samples/holdout_v2').glob('*'):
    if p.is_file():
        result = validate_content(p.read_text(), expected_class=...)  # see validator API
        print(f'{p.name}: {result}')
"
```

If `train/generate_dataset.py` does not expose a `validate_content` function, skip this step — visual review is the fallback. **Reject any file matching real-secret regex; do not redact.**

- [ ] **Step 3.3: Commit**

```bash
git add samples/holdout_v2/ train/curated_data.py
git commit -m "Phase 3b.5 T3 — hand-curate +7 training rows (curated_data.py) + 20 held-out files (holdout_v2/)"
```

---

## Task 4: Channel C — mine 5-8 training samples [parallelizable subagent]

**Files:**
- Create: `samples/external/training_mined/<filename>` (5-8 mined `.env.example`-style files + `.provenance.json` siblings)
- Modify: `train/curated_data.py` — append a new section that loads from `samples/external/training_mined/` and emits training rows (OR alternative inlining; see Step 4.3)

**Dispatch note:** runs in parallel with T2 and T3.

- [ ] **Step 4.1: Run the collector with `.env.example`-focused queries**

```bash
.venv/bin/python tools/sample_collector.py \
    --target-count 8 \
    --output-prefix samples/external/training_mined \
    --queries 'path:.env.example' \
              'path:.env.dist' \
              'path:.env.template' \
              'path:.env STRIPE_SECRET_KEY OR AWS_SECRET_ACCESS_KEY'
```

The collector will write files to `samples/external/training_mined/` with `.provenance.json` siblings.

- [ ] **Step 4.2: Hand-assign labels**

The collector by default tags files with a regex-guessed class. For training rows, hand-correct each one based on what's actually in the file:

- All placeholder values (`your-X`, empty `=`, `CHANGEME`) → `classify_safe`
- Realistic-shaped values → `block_transfer`
- Mixed (owid-style) → `block_transfer` (the safer call)

Edit each `.provenance.json` to set `"hand_assigned_label": "<label>"`.

- [ ] **Step 4.3: Wire mined training rows into the dataset pipeline**

Two acceptable approaches — pick one based on the size of the mined files:

**Approach A (recommended if mined files are small, < 5KB each):** inline them into `train/curated_data.py` lists as additional entries (copying the same pattern as Step 3.1). Re-run `train/curated_data.py` to regenerate `dataset.jsonl`.

**Approach B (recommended if mined files are large or numerous):** add a new function in `train/curated_data.py`:

```python
def load_mined_training_rows() -> list[dict]:
    """Load Channel-C mined training rows from samples/external/training_mined/."""
    import json, pathlib
    rows = []
    base = pathlib.Path("samples/external/training_mined")
    for f in sorted(base.glob("*")):
        if f.suffix == ".json":
            continue
        prov_path = f.with_suffix(f.suffix + ".provenance.json")
        if not prov_path.exists():
            continue
        prov = json.loads(prov_path.read_text())
        label = prov.get("hand_assigned_label") or prov.get("inferred_class")
        if not label:
            continue
        rows.append({
            "scenario_id": f"mined:{f.stem}",
            "label": label,
            "text": f.read_text(),
        })
    return rows
```

Then in the `__main__` block of `train/curated_data.py`, append `load_mined_training_rows()` results to the rows list before writing JSONL.

Either way, after the change, run:

```bash
.venv/bin/python train/curated_data.py
wc -l train/dataset.jsonl
```

Expected: ~212-215 lines (200 base + 7 from T3 + 5-8 from T4).

- [ ] **Step 4.4: Sanity-check per-class balance**

Run the same per-class count snippet from Step 3.1. Expected per-class counts after T3 + T4: roughly `classify_safe: 55-58`, `block_transfer: 57-60`, `flag_pii: 50`, `request_permission: 50`. Mild imbalance — LR handles it; no `class_weight='balanced'` needed.

- [ ] **Step 4.5: Commit**

```bash
git add samples/external/training_mined/ train/curated_data.py
git commit -m "Phase 3b.5 T4 — mine 5-8 .env.example training rows (Channel C) into training_mined/"
```

---

## Task 5: Build `eval_fresh.py` + `eval_regression.py`

**Files:**
- Create: `eval_fresh.py`
- Create: `eval_regression.py`
- Create: `tests/test_eval_fresh.py`
- Create: `tests/test_eval_regression.py`
- Modify: `train/eval_head.py` — add `--cases-module` arg

**Dispatch note:** runs after T2 + T3 (held-out files must exist before the CASES lists can point at them). Independent of T4.

- [ ] **Step 5.1: Write the failing tests**

Create `tests/test_eval_fresh.py`:

```python
"""Validate eval_fresh.CASES structure + file existence + class balance."""
from __future__ import annotations

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import eval_fresh

VALID_LABELS = {"classify_safe", "flag_pii", "block_transfer", "request_permission"}


def test_cases_is_nonempty_list_of_tuples():
    assert isinstance(eval_fresh.CASES, list)
    assert len(eval_fresh.CASES) >= 90
    for entry in eval_fresh.CASES:
        assert isinstance(entry, tuple) and len(entry) == 2


def test_every_case_file_exists():
    for path_str, _ in eval_fresh.CASES:
        p = REPO_ROOT / path_str
        assert p.exists(), f"missing: {path_str}"


def test_every_label_is_valid():
    for _, label in eval_fresh.CASES:
        assert label in VALID_LABELS


def test_class_balance_within_5():
    from collections import Counter
    c = Counter(label for _, label in eval_fresh.CASES)
    assert set(c.keys()) == VALID_LABELS, f"missing class(es): {VALID_LABELS - set(c)}"
    min_count, max_count = min(c.values()), max(c.values())
    assert max_count - min_count <= 5, f"class imbalance > 5: {dict(c)}"


def test_no_overlap_with_existing_98_set():
    import eval as eval_original
    fresh_paths = {p for p, _ in eval_fresh.CASES}
    original_paths = {p for p, _ in eval_original.CASES}
    overlap = fresh_paths & original_paths
    assert not overlap, f"fresh held-out overlaps with original 98: {overlap}"
```

Create `tests/test_eval_regression.py`:

```python
"""Validate eval_regression.CASES + presence of the 5 Phase 3b failures."""
from __future__ import annotations

import pathlib
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import eval_regression

VALID_LABELS = {"classify_safe", "flag_pii", "block_transfer", "request_permission"}

PHASE_3B_FAILURES = {
    "samples/external/flag_pii/delphix_dxtoolkit_f6fdab90.example",
    "samples/external/flag_pii/AgrawalVi_ponovo_83908028.csv",
    "samples/external/block_transfer/owid_owid-grapher_b8fa04ba.example-full",
    "samples/hr_exit_interview_records.txt",
    "samples/saas_help_center_article.md",
}


def test_cases_is_list_of_tuples():
    assert isinstance(eval_regression.CASES, list)
    for entry in eval_regression.CASES:
        assert isinstance(entry, tuple) and len(entry) == 2


def test_all_five_phase_3b_failures_present():
    paths = {p for p, _ in eval_regression.CASES}
    missing = PHASE_3B_FAILURES - paths
    assert not missing, f"missing Phase 3b failures: {missing}"


def test_every_case_file_exists():
    for path_str, _ in eval_regression.CASES:
        p = REPO_ROOT / path_str
        assert p.exists(), f"missing: {path_str}"


def test_every_label_is_valid():
    for _, label in eval_regression.CASES:
        assert label in VALID_LABELS
```

- [ ] **Step 5.2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_eval_fresh.py tests/test_eval_regression.py -v`
Expected: ImportError on `eval_fresh` and `eval_regression` (the modules don't exist yet).

- [ ] **Step 5.3: Create `eval_fresh.py`**

Same structure as `eval.py`. Build the CASES list by walking the `samples/external/holdout_v2/` and `samples/holdout_v2/` directories:

```python
"""Phase 3b.5 — fresh held-out eval set (100 samples).

This module is touched EXACTLY ONCE for the headline Phase 3b.5 accuracy
number. Re-running it after gate decision reuses the held-out and invalidates
the single-shot guarantee. If you find yourself wanting to re-run, stop and
add the failing case to eval_regression.py instead.

Generated 2026-05-20 from:
  - ~80 Channel C mined files in samples/external/holdout_v2/
  - ~20 Channel A hand-curated files in samples/holdout_v2/

Provenance for each Channel-C file lives in its sibling .provenance.json.
"""
from __future__ import annotations

import pathlib

LABELS = ("classify_safe", "flag_pii", "block_transfer", "request_permission")


def _discover_cases() -> list[tuple[str, str]]:
    """Walk holdout_v2/ subtrees and emit (relative_path, label) tuples."""
    cases: list[tuple[str, str]] = []
    repo_root = pathlib.Path(__file__).resolve().parent

    # Channel C: samples/external/holdout_v2/<label>/<file>
    for label_dir in (repo_root / "samples" / "external" / "holdout_v2").iterdir():
        if not label_dir.is_dir():
            continue
        label = label_dir.name
        if label not in LABELS:
            continue
        for f in label_dir.iterdir():
            if f.is_file() and not f.name.endswith(".provenance.json"):
                rel = f.relative_to(repo_root).as_posix()
                cases.append((rel, label))

    # Channel A: samples/holdout_v2/<file> — label encoded in filename or a manifest
    manifest_path = repo_root / "samples" / "holdout_v2" / "_labels.json"
    if manifest_path.exists():
        import json
        manifest = json.loads(manifest_path.read_text())
        for fname, label in manifest.items():
            f = repo_root / "samples" / "holdout_v2" / fname
            if f.is_file():
                cases.append((f.relative_to(repo_root).as_posix(), label))

    return sorted(cases)


CASES = _discover_cases()
```

Create the labels manifest `samples/holdout_v2/_labels.json`:

```json
{
  "architecture_decision_record_001.md": "classify_safe",
  "oss_governance_charter.md": "classify_safe",
  "conference_workshop_handout.md": "classify_safe",
  "release_announcement_blog.md": "classify_safe",
  "community_code_of_conduct.txt": "classify_safe",
  "clinical_research_consent_form.txt": "flag_pii",
  "loan_underwriting_summary.csv": "flag_pii",
  "k12_grade_report.csv": "flag_pii",
  "jury_summons_database.csv": "flag_pii",
  "health_screening_intake.txt": "flag_pii",
  "vault_root_token.txt": "block_transfer",
  "k8s_service_account.yaml": "block_transfer",
  "gh_app_private_key.pem": "block_transfer",
  "google_service_account.json": "block_transfer",
  "datadog_api_keys.env": "block_transfer",
  "board_meeting_minutes_q3.md": "request_permission",
  "acquisition_term_sheet_draft.md": "request_permission",
  "employee_handbook_compensation_section.md": "request_permission",
  "post_incident_review_outage_2024.md": "request_permission",
  "customer_churn_analysis_q4.md": "request_permission"
}
```

(Filenames must match exactly what T3 produced; adjust if T3 chose different names.)

- [ ] **Step 5.4: Create `eval_regression.py`**

```python
"""Phase 3b.5 — ambiguity regression suite (10 hand-picked cases).

Includes the 5 known failures from Phase 3b's 98-sample eval + 5 nearby
tricky .example files that the current head gets right. Used informally
to verify no regression on cases we already understand. Not the headline
number; not gating.
"""
from __future__ import annotations

LABELS = ("classify_safe", "flag_pii", "block_transfer", "request_permission")

CASES: list[tuple[str, str]] = [
    # The 5 Phase 3b failures — these MUST be classified correctly under the new head
    # for the "zero fail-open" gate clause to hold (specifically owid).
    ("samples/external/flag_pii/delphix_dxtoolkit_f6fdab90.example", "flag_pii"),
    ("samples/external/flag_pii/AgrawalVi_ponovo_83908028.csv", "flag_pii"),
    ("samples/external/block_transfer/owid_owid-grapher_b8fa04ba.example-full", "block_transfer"),
    ("samples/hr_exit_interview_records.txt", "flag_pii"),
    ("samples/saas_help_center_article.md", "classify_safe"),

    # 5 nearby tricky .example files the current Phase 3b head gets RIGHT.
    # Must-not-regress: if a retrained head fails on any of these, flag in scorecard.
    ("samples/external/block_transfer/tambo-ai_tambo_4bac536a.example", "block_transfer"),
    ("samples/external/block_transfer/denysdovhan_smart-home_4c389a32.example", "block_transfer"),
    ("samples/external/block_transfer/melkor217_ayanami_23ae012e.example", "block_transfer"),
    ("samples/external/block_transfer/coneshare_coneshare-compose_37f0f89b.example", "block_transfer"),
    ("samples/external/block_transfer/MarekWo_UPS_monitor_a26577d7.example", "block_transfer"),
]
```

- [ ] **Step 5.5: Add `--cases-module` arg to `train/eval_head.py`**

Open `train/eval_head.py`. Currently it imports `from eval import CASES, LABELS` at line 27. Replace that line and the surrounding `main()` setup with:

```python
def _resolve_cases_module(name: str):
    """Import the chosen CASES module by name."""
    import importlib
    if name not in {"eval", "eval_fresh", "eval_regression"}:
        raise ValueError(f"unknown cases module {name!r}; valid: eval, eval_fresh, eval_regression")
    return importlib.import_module(name)


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Eval the Aegis LR head.")
    parser.add_argument(
        "--cases-module",
        default="eval",
        choices=["eval", "eval_fresh", "eval_regression"],
        help="Which CASES list to score against (default: eval)",
    )
    args = parser.parse_args()
    cases_module = _resolve_cases_module(args.cases_module)
    CASES = cases_module.CASES
    LABELS = cases_module.LABELS

    # ... rest of existing main() body unchanged, using local CASES + LABELS ...
```

Remove the top-level `from eval import CASES, LABELS` import. Move all `CASES` / `LABELS` references inside `main()`.

- [ ] **Step 5.6: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_eval_fresh.py tests/test_eval_regression.py -v`
Expected: all pass.

- [ ] **Step 5.7: Smoke-test the eval module flag**

```bash
.venv/bin/python train/eval_head.py --cases-module eval_regression 2>&1 | tail -20
```

Expected: full eval output against the 10-case suite. Specifically, you should see `owid_owid-grapher_b8fa04ba.example-full` in the printed case list. Pass/fail per-case doesn't matter at this point — we haven't retrained yet.

- [ ] **Step 5.8: Commit**

```bash
git add eval_fresh.py eval_regression.py tests/test_eval_fresh.py tests/test_eval_regression.py train/eval_head.py samples/holdout_v2/_labels.json
git commit -m "Phase 3b.5 T5 — eval_fresh.py + eval_regression.py + eval_head.py --cases-module"
```

---

## Task 6: Extend `train/prompt_sweep.py` for full (prompt × C) grid + JSON winner

**Files:**
- Modify: `train/prompt_sweep.py`

The Phase 3b version sweeps prompts only at a fixed C. Phase 3b.5 wants the full 4 × 3 grid. Output the winner to `train/sweep_winner.json` so `train_head.py` (Task 1) can consume it.

- [ ] **Step 6.1: Read the existing `prompt_sweep.py` to understand its structure**

Run: `head -80 train/prompt_sweep.py`

Identify where the per-prompt embeddings are computed and where the CV scoring happens. The change is additive: nest the existing prompt loop inside a C loop, or vectorize as a flat grid.

- [ ] **Step 6.2: Modify the sweep to cover (prompt × C)**

Replace the existing main loop with:

```python
import json
import pathlib

PROMPTS = ["none", "classification", "classify_short", "classify_doc"]
C_VALUES = [0.1, 1.0, 10.0]
WINNER_PATH = pathlib.Path("train/sweep_winner.json")

# ... existing dataset loading + embedding cache code ...

results = []  # list of dicts: {prompt, C, mean_f1, std_f1, mean_acc, std_acc}

for prompt in PROMPTS:
    # Embed the full training set under this prompt once
    X_prompt = embed_dataset_under_prompt(prompt)  # use existing helper
    y = labels_array  # already loaded

    for C in C_VALUES:
        from sklearn.linear_model import LogisticRegression
        from sklearn.model_selection import StratifiedKFold, cross_val_score
        model = LogisticRegression(C=C, max_iter=2000, solver="lbfgs", random_state=42)
        kf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
        f1s = cross_val_score(model, X_prompt, y, cv=kf, scoring="f1_macro")
        accs = cross_val_score(model, X_prompt, y, cv=kf, scoring="accuracy")
        results.append({
            "prompt": prompt,
            "C": C,
            "mean_f1": float(f1s.mean()),
            "std_f1": float(f1s.std()),
            "mean_acc": float(accs.mean()),
            "std_acc": float(accs.std()),
        })
        print(f"  prompt={prompt!r:>22}  C={C:>5.2f}  f1={f1s.mean():.4f} ± {f1s.std():.4f}  acc={accs.mean():.4f}")

# Pick winner: highest mean_f1, tiebreak on lower std_f1
winner = max(results, key=lambda r: (r["mean_f1"], -r["std_f1"]))
print(f"\nWinner: prompt={winner['prompt']!r}, C={winner['C']}  (f1={winner['mean_f1']:.4f})")

WINNER_PATH.parent.mkdir(parents=True, exist_ok=True)
WINNER_PATH.write_text(json.dumps({
    "prompt": winner["prompt"],
    "C": winner["C"],
    "selection_metric": "cv_macro_f1_mean",
    "all_results": results,
    "training_set_size": int(X_prompt.shape[0]),
    "swept_at": __import__("time").strftime("%Y-%m-%d %H:%M:%S"),
}, indent=2))
print(f"Wrote winner to {WINNER_PATH}")
```

The exact integration depends on the existing structure — preserve any caching / progress prints that are already there.

- [ ] **Step 6.3: Commit (sweep extension only, no actual sweep run yet)**

```bash
git add train/prompt_sweep.py
git commit -m "Phase 3b.5 T6 — prompt_sweep.py: full (prompt × C) grid + sweep_winner.json output"
```

---

## Task 7: Run the (prompt × C) CV sweep, commit the winner

**Files:**
- Create: `train/sweep_winner.json` (output of the sweep run)

This is a compute step — embed once per prompt (4 embeddings of ~215 rows = ~860 forward passes, ~3-5 min on M-class Mac), then 12 × 5 = 60 LR fits (seconds).

- [ ] **Step 7.1: Run the sweep**

```bash
.venv/bin/python train/prompt_sweep.py 2>&1 | tee /tmp/phase-3b5-sweep.log
```

Expected: ~3-5 min runtime. Final lines should look like:

```
  prompt='none'                 C= 0.10  f1=0.X ...
  prompt='none'                 C= 1.00  f1=0.X ...
  ...
Winner: prompt='<X>', C=<Y>  (f1=<Z>)
Wrote winner to train/sweep_winner.json
```

- [ ] **Step 7.2: Verify the winner JSON is well-formed**

```bash
.venv/bin/python -c "import json; w = json.load(open('train/sweep_winner.json')); print(json.dumps(w, indent=2))" | head -20
```

Expected: prompt + C keys present, all_results list with 12 entries, selection_metric = "cv_macro_f1_mean".

- [ ] **Step 7.3: Commit**

```bash
git add train/sweep_winner.json
git commit -m "Phase 3b.5 T7 — run (prompt × C) CV sweep on 215-row training set (winner: <prompt>, C=<C>)"
```

Fill in the actual winning prompt + C in the commit message.

---

## Task 8: Fit the final head + save bundle

**Files:**
- Modify (overwrite): `aegis-head/lr.joblib`

- [ ] **Step 8.1: Run `train/train_head.py` consuming the sweep winner**

```bash
.venv/bin/python train/train_head.py 2>&1 | tee /tmp/phase-3b5-train.log
```

`train_head.py` will read `train/sweep_winner.json` automatically (per Task 1) and use the winning `(prompt, C)`. Expected runtime: ~30s (one embedding pass + one LR fit).

Expected output tail:

```
Saved trained head to aegis-head/lr.joblib  (~25 KB)
  embed_model: google/embeddinggemma-300m
  embed_task_prompt: <X>
  C: <Y>
  training_set_phase: 3b.5
  training_set_size: <N>
  trained_at: 2026-05-20
```

- [ ] **Step 8.2: Verify the bundle structure**

```bash
.venv/bin/python -c "
import joblib
b = joblib.load('aegis-head/lr.joblib')
for k, v in b.items():
    if k == 'model':
        print(f'  model: LogisticRegression (classes={list(v.classes_)})')
    elif k == 'cv_results':
        print(f'  cv_results: <dict with {len(v)} entries>')
    elif k == 'all_results':
        print(f'  all_results: <list with {len(v)} entries>')
    else:
        print(f'  {k}: {v}')
"
```

Expected: `training_set_phase: 3b.5`, `embed_task_prompt: <winner>`, `C: <winner>`, `training_set_size: <215-ish>`.

- [ ] **Step 8.3: Commit (DO NOT push)**

```bash
git add aegis-head/lr.joblib
git commit -m "Phase 3b.5 T8 — retrain head at prompt=<X>, C=<Y> on 215-row training set"
```

Fill in actual winner values in the commit message. Note: this commit lands the new head BEFORE the gate decision. If the gate fails in Task 10, the rollback restores the prior head via a new commit (not by amending this one).

---

## Task 9: Run all three evals, capture outputs

**Files:**
- Create: `docs/eval-results/2026-05-20-phase-3b5-fresh-holdout.txt`
- Create: `docs/eval-results/2026-05-20-phase-3b5-regression-98sample.txt` (continuity)
- Create: `docs/eval-results/2026-05-20-phase-3b5-ambiguity.txt` (regression suite)

- [ ] **Step 9.1: HEADLINE — run `eval_head.py --cases-module eval_fresh` EXACTLY ONCE**

```bash
.venv/bin/python train/eval_head.py --cases-module eval_fresh 2>&1 | tee docs/eval-results/2026-05-20-phase-3b5-fresh-holdout.txt
```

**Do not re-run this command after seeing the result.** Re-running reuses the held-out and invalidates the single-shot publishable number. If something looks wrong, debug via the regression eval (Step 9.3) — never re-touch the fresh held-out.

Expected: ~1-2 min runtime, full classification report with per-class precision/recall/f1, confusion matrix, list of failures by file → true → predicted, aggregate accuracy + Wilson 95% CI.

- [ ] **Step 9.2: Continuity — re-run against the existing 98-sample set**

```bash
.venv/bin/python train/eval_head.py --cases-module eval 2>&1 | tee docs/eval-results/2026-05-20-phase-3b5-regression-98sample.txt
```

Compare aggregate accuracy vs the Phase 3b 93/98 = 94.90% number. If it dropped, flag in the scorecard write-up — but it doesn't change the ship/no-ship decision.

- [ ] **Step 9.3: Ambiguity regression — run against the 10-case regression suite**

```bash
.venv/bin/python train/eval_head.py --cases-module eval_regression 2>&1 | tee docs/eval-results/2026-05-20-phase-3b5-ambiguity.txt
```

Specifically check:
- Was `owid_owid-grapher_b8fa04ba.example-full` classified as `block_transfer`? (Required for the gate.)
- Did any of the 5 must-not-regress cases (tambo, denysdovhan, melkor217, coneshare, MarekWo) flip from correct to incorrect?

- [ ] **Step 9.4: Commit the captured outputs**

```bash
git add docs/eval-results/2026-05-20-phase-3b5-*.txt
git commit -m "Phase 3b.5 T9 — capture 3 eval outputs (fresh holdout headline + regression + ambiguity)"
```

---

## Task 10: Apply decision gate, branch on result

**Files (pass branch):**
- Modify: `docs/eval-results/scorecard.md`

**Files (fail branch):**
- Modify: `aegis-head/lr.joblib` (restored to prior commit's version)
- Create: `docs/superpowers/specs/2026-05-XX-phase-3b51-followup.md` (placeholder for next iteration)

- [ ] **Step 10.1: Apply the decision gate**

From the headline eval output in Step 9.1, extract:

- `headline_accuracy` (e.g., 0.96 from "accuracy: 0.96 (96/100)")
- `wilson_ci_lower` (lower bound of the Wilson 95% CI; the eval script prints this — see existing format)
- `failures` list (each `<file>  <true>  <predicted>`)

Apply both clauses:

```
clause_1_acc      := headline_accuracy > 0.9490
clause_1_ci       := wilson_ci_lower >= 0.886
clause_2_safety   := no failure has (true ∈ {block_transfer, flag_pii} AND predicted == classify_safe)

gate_passes := clause_1_acc AND clause_1_ci AND clause_2_safety
```

- [ ] **Step 10.2a: IF GATE PASSES — update scorecard, mark roadmap done**

Open `docs/eval-results/scorecard.md`. Add a new section after the existing "98-sample eval" section:

```markdown
### Fresh 100-sample held-out (Phase 3b.5 — single-shot publishable)

100 entirely-new samples in `samples/external/holdout_v2/` and `samples/holdout_v2/`, mined and curated 2026-05-20. No file in this set appears in the original 12 / 30 / 98 eval sets. Touched exactly once — re-running would invalidate the single-shot guarantee.

| Model | Protocol | Accuracy | Wilson 95% CI | Macro F1 | Warm p50 | Notes |
|---|---|---|---|---|---|---|
| **`embeddinggemma` + LR head (Phase 3b.5)** | **head, local** | **<X>/100 = <X>%** | **[<low>, <high>]** | **<f1>** | **<ms> ms** | **In-process head, prompt=<P>, C=<C>. Retrained on 215-row training set with +15 `.env.example`-shaped rows. Gate: > 94.90% accuracy AND zero fail-open errors — PASSED.** |
```

(Fill in actual numbers from `docs/eval-results/2026-05-20-phase-3b5-fresh-holdout.txt`.)

Add a "Phase 3b.5 outcome" subsection (below the existing "Phase 3b outcome") summarizing:
- What changed: +15 training rows, retrained at (prompt, C), 100 fresh held-out
- What the headline number resolves: methodology debt from Phase 3b (held-out used twice) + the one fail-open case
- Per-failure breakdown for whatever errors remain in the new held-out (same table format as the Phase 3b "Held-out failure modes" section)
- A pointer to Phase 3c (next phase) as the immediate follow-up

Also update the Phase 3b.5 row of the "Where we are" table at the top of `docs/roadmap.md`:

```markdown
| **Phase 3b.5** | done | Closed the `.example` distribution gap. Added ~15 training rows + fresh 100-sample held-out (combined with originally-planned 3b.6). Retrained head scored <X>/100 = <X>% on the fresh held-out, gate passed (zero fail-open errors). |
```

- [ ] **Step 10.2b: IF GATE FAILS — rollback + file 3b.5.1**

```bash
# Restore the prior head (before T8's commit)
git revert --no-edit HEAD~2  # revert the T8 commit specifically — verify SHA first

# Confirm the rolled-back head matches the Phase 3b version
.venv/bin/python -c "
import joblib
b = joblib.load('aegis-head/lr.joblib')
print(f'embed_task_prompt: {b.get(\"embed_task_prompt\")}')
print(f'training_set_phase: {b.get(\"training_set_phase\", \"<missing — prior to 3b.5>\")}')
"
```

(If the SHA in `git revert HEAD~2` doesn't point at the T8 commit, identify it first via `git log --oneline | grep "Phase 3b.5 T8"`.)

Then create `docs/superpowers/specs/2026-05-XX-phase-3b51-followup-design.md` with a 50-100 line skeleton:
- What clause of the gate failed (accuracy, CI lower bound, or fail-open count)
- Which specific files broke
- Hypothesis for fix (e.g., "more training samples needed for class X")
- Replacement-plan placeholder

Update the scorecard with a "Phase 3b.5 outcome — rollback" subsection capturing the failed run for posterity. Update the roadmap to mark Phase 3b.5 partial / 3b.5.1 scheduled.

- [ ] **Step 10.3: Commit the docs update**

```bash
git add docs/eval-results/scorecard.md docs/roadmap.md
git commit -m "Phase 3b.5 T10 — scorecard + roadmap: <PASS/FAIL> on fresh 100-sample held-out"
```

If failed: also `git add docs/superpowers/specs/2026-05-XX-phase-3b51-followup-design.md` in the same commit.

---

## Task 11: End-of-phase cleanup

**Files:** (varies)

- [ ] **Step 11.1: Verify whole test suite still passes**

```bash
.venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration_slow.py 2>&1 | tail -20
```

Expected: all green. If anything Phase-3b-era is now broken (e.g., a test that hard-coded `TASK_PROMPT == "none"` in a bundle assertion), fix the test.

- [ ] **Step 11.2: Verify the bridge starts cleanly with the new head**

```bash
.venv/bin/python aegis_bridge.py --backend local --port 8765 &
BRIDGE_PID=$!
sleep 5
curl -s http://localhost:8765/health | python3 -m json.tool
kill $BRIDGE_PID
```

Expected: `/health` returns the new head's metadata: `embed_task_prompt`, `C`, `training_set_phase: 3b.5`, `head_trained_at_C`, etc. (Whatever fields Phase 3b T12 added — they should reflect the new bundle.)

- [ ] **Step 11.3: Run pyflakes / formatting passes if the project uses them**

Check if there's a `pyproject.toml` linting config or a `tools/` script:

```bash
grep -E '^\[tool\.(ruff|black|isort)' pyproject.toml || echo "no linting config"
```

If linting is configured, run it on the touched files. Skip if not.

- [ ] **Step 11.4: Commit any final cleanup**

```bash
git status --porcelain
# If there's anything left:
git add <files>
git commit -m "Phase 3b.5 T11 — end-of-phase cleanup"
```

If nothing to commit, skip.

---

## End-of-plan checklist

Before declaring Phase 3b.5 done, verify against the spec:

- [ ] `train/curated_data.py` grew by ~7 hand-curated rows AND wires in mined rows (T3 + T4)
- [ ] `samples/external/holdout_v2/` contains ~80 mined files with provenance, deduplicated against the original 98 set (T2)
- [ ] `samples/holdout_v2/` contains ~20 hand-curated files with a `_labels.json` manifest (T3)
- [ ] `samples/external/training_mined/` contains 5-8 mined training files (T4)
- [ ] `eval_fresh.py` + `eval_regression.py` exist, both pass their unit tests (T5)
- [ ] `train/eval_head.py` accepts `--cases-module {eval,eval_fresh,eval_regression}` (T5)
- [ ] `train/prompt_sweep.py` sweeps the full (4 × 3) grid, writes `train/sweep_winner.json` (T6, T7)
- [ ] `train/train_head.py` accepts `--prompt`/`--C` flags AND reads `train/sweep_winner.json` (T1, T8)
- [ ] `aegis-head/lr.joblib` was retrained at the sweep-winning `(prompt, C)` with new metadata fields including `training_set_phase: "3b.5"` (T8)
- [ ] Headline eval was run EXACTLY ONCE against `eval_fresh` (T9.1)
- [ ] Decision gate explicitly applied and recorded — clause 1 (accuracy + CI) + clause 2 (zero fail-open) (T10)
- [ ] Scorecard updated with the Phase 3b.5 row + outcome write-up (T10)
- [ ] Roadmap updated, Phase 3b.5 marked done (T10)
- [ ] All commits made locally; **NO `git push`** — user is the sole gatekeeper for the remote
- [ ] `.codex/` was not touched, read, or staged at any point

Suggested next phase (after 3b.5 lands): **Phase 3c — wire `LocalBackend` into the MCP tool-call path.** Small plumbing job; the bridge already supports `--backend local` but the MCP layer doesn't yet route production traffic through it.
