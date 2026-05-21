# `samples/external/holdout_v2/`

Phase 3b.5 fresh held-out evaluation set, mined on 2026-05-19 via Channel C
(public-GitHub code search) using `tools/sample_collector.py`.

## Purpose

This subtree is the **fresh, never-touched held-out** for the Phase 3b.5
prompt × C sweep. It is held strictly separate from the training pools and
from the Phase 3b held-out under `samples/external/<class>/`:

- **No overlap** with `samples/external/<class>/` — the collector dedupes on
  blob SHA via the per-file `.provenance.json`, and the queries below pull
  from distinct repo populations than the original Phase 3b mine.
- **Never touched after T9** — once the final head is fit and the held-out
  metric is recorded in `eval/SCORECARD.md`, this directory is frozen for
  the remainder of the phase. Do not re-mine it, do not augment it, do not
  re-label it for any downstream tuning decision.

## Final class counts

After the T2 audit (relabel of NDA templates → `classify_safe`):

| Class               | Count |
|---------------------|-------|
| `block_transfer`    |  22   |
| `classify_safe`     |  35   |
| `flag_pii`          |  18   |
| `request_permission`|   7   |

(Each sample also has a sibling `.provenance.json` file recording the
source repo, blob SHA, source URL, query terms, and fetched_at timestamp.)

The `request_permission` class is intentionally undersized. The Channel C
mining session surfaced ~20 candidate NDA-shaped documents, but a
post-collection audit found ~13 of them to be publicly-shared NDA templates,
demonstration samples, or blog-post explainers ABOUT NDAs rather than
filled-in confidential documents. Those 13 were re-labeled to
`classify_safe` (their content is genuinely safe to share — that is the
point) rather than being deleted, since they have value as
"public-template" examples that the safe class should learn to recognize.

The remaining 7 `request_permission` files are the ones that read like
real confidential documents an employee would mark CONFIDENTIAL:
filled-in NDAs and HOA covenant declarations with realistic-looking party
names, real dates, and no obvious placeholder fields. Per-class imbalance
at this scale is acceptable — the Phase 3b.5 spec target of "balance
within 5" was a soft target, and the eval reports per-class precision/
recall separately rather than a single accuracy number.

Each re-labeled file's `.provenance.json` records its original collection
query under `collector_query_terms` (which will still be one of the
`request_permission` queries) plus a `relabel_note` field explaining why
it was moved.

## Reproducibility

The full dataset can be re-mined from scratch with:

```bash
.venv/bin/python tools/sample_collector.py classify_safe      --max 25 \
    --output-prefix samples/external/holdout_v2
.venv/bin/python tools/sample_collector.py flag_pii           --max 25 \
    --output-prefix samples/external/holdout_v2
.venv/bin/python tools/sample_collector.py block_transfer     --max 25 \
    --output-prefix samples/external/holdout_v2
.venv/bin/python tools/sample_collector.py request_permission --max 25 \
    --output-prefix samples/external/holdout_v2
```

The `QUERIES` dict in `tools/sample_collector.py` is the single source of
truth for which gh-search queries produce this set. Exact reproduction is
not guaranteed (the public-GitHub corpus is non-stationary and `gh search
code` returns ranked-by-relevance results that drift), but the queries are
deterministic and each accepted file's full provenance (repo, path, blob
SHA, source URL, query terms, fetched_at timestamp) is recorded next to it.
