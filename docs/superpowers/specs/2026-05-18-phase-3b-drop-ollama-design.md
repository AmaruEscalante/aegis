# Phase 3b — Drop the Ollama Dependency (Design Spec)

**Date:** 2026-05-18
**Phase:** 3b (of the [Aegis roadmap](../../roadmap.md))
**Status:** Approved — ready to plan
**Predecessor:** Phase 3a (eval expansion to 30 samples, merged in PR #2)
**Successor:** Phase 3c (wire `HeadBackend` into bridge as default) + Phase 3d (PDF/DOCX support)

## Goal

Replace the bridge's external Ollama HTTP dependency with in-process inference using `sentence-transformers`, so a future user can install Aegis with a single command (same UX as Context7 / Superpowers MCP plugins) without separately installing Ollama, pulling `embeddinggemma`, and keeping `ollama serve` running.

Phase 3b is the work that makes Phase 4 (publishing as an MCP marketplace plugin) possible. It is not yet that phase.

## Success criteria

- `python aegis_bridge.py --backend local` (default) starts without Ollama running and serves `/classify` end-to-end at warm p50 ≤ 200 ms.
- `python aegis_bridge.py --backend ollama` keeps the existing dev/escape-hatch path working unchanged.
- Trained head retrained on prompted embeddings scores **≥ 29/30** on the same 30-sample eval set Phase 3a used. If it scores worse, we roll back to a no-prompt variant and ship that instead — we do not ship a regression.
- `pyproject.toml` adds exactly one new dep (`sentence-transformers`); no other deps churn.

## Decisions locked from brainstorming

| Decision | Choice | Rationale |
|---|---|---|
| Install UX | Lean install + first-run HF Hub weight download | Standard Python ML pattern, matches Context7 / Superpowers single-command install |
| Inference library | `sentence-transformers` | Google's canonical inference path for EmbeddingGemma per their official notebook; handles task prompts cleanly; one-line model load |
| Task prompts | Yes, `task="classification"`; retrain head as part of 3b | Google docs explicitly call out classification as a prompt-bonus task; lock in the accuracy upside now |
| Backend toggle | Two backends, `--backend {local,ollama}`, default local | Keep Ollama path reachable for A/B and as escape hatch; new default is shippable |
| Code shape | New shared `aegis/embedding.py` module owns the `Embedder` class; used by `LocalBackend`, `train/train_head.py`, `train/eval_head.py` | One source of truth for embedding logic; future-extensible (Phase 5 vision encoder slots in as a sibling) |
| Weight cache | HuggingFace default (`~/.cache/huggingface/`) | Dedupes with any other HF tool the user runs; zero special handling |
| Other Ollama callers | `train/train_head.py` + `train/eval_head.py` switch (need prompt-aware embeddings); `eval.py` + `benchmark.py` stay (base-model comparison path) | Right tool for each job; minimizes scope creep |
| Startup failure mode | Eager-load model at construction; fail loud with clear hint if anything is wrong | Don't surprise users with a slow first request or partial-working state |

## Architecture

```
                              ┌─────────────────────────────────┐
                              │  aegis/embedding.py  (NEW)      │
                              │                                 │
                              │  class Embedder:                │
                              │    Loads embeddinggemma-300m    │
                              │    via sentence-transformers,   │
                              │    eagerly, with classification │
                              │    prompt as default.           │
                              │    encode(text) -> (768,) f32   │
                              └────────────┬────────────────────┘
                                           │  imports
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
     ┌────────▼─────────┐         ┌────────▼─────────┐         ┌────────▼─────────┐
     │ aegis_bridge.py  │         │ train/           │         │ train/           │
     │                  │         │   train_head.py  │         │   eval_head.py   │
     │ LocalBackend     │         │                  │         │                  │
     │ (NEW)            │         │ retrains head    │         │ re-evals on 30   │
     │   Embedder       │         │ on prompted      │         │ samples; gate    │
     │   + LR head      │         │ embeddings       │         │ ≥ 29/30 to ship  │
     │                  │         │                  │         │                  │
     │ OllamaBackend    │         │                  │         │                  │
     │ (unchanged)      │         │                  │         │                  │
     │                  │         │                  │         │                  │
     │ --backend flag   │         │                  │         │                  │
     │ chooses one      │         │                  │         │                  │
     └──────────────────┘         └──────────────────┘         └──────────────────┘
```

Untouched: `eval.py`, `benchmark.py`, `eval_embeddinggemma.py`, the TypeScript MCP server in `middleware/`, the existing 30-sample eval corpus in `samples/`.

## Components

### `aegis/embedding.py` (NEW)

```python
class Embedder:
    """In-process embeddinggemma wrapper. Loaded eagerly at construction."""

    DEFAULT_MODEL_ID = "google/embeddinggemma-300m"
    DEFAULT_PROMPTS = {
        "classification": "task: classification | query: ",
        "retrieval":      "task: retrieval | query: ",
    }
    MAX_INPUT_CHARS = 8000

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        cache_folder: str | None = None,    # None = HF default
        default_task: str = "classification",
        device: str | None = None,           # None = sentence-transformers auto
    ): ...

    def encode(self, text: str, task: str | None = None) -> np.ndarray:
        """Embed one piece of text. Returns float32 (768,) L2-normalized vector."""

    def encode_batch(
        self, texts: list[str], task: str | None = None, batch_size: int = 32
    ) -> np.ndarray:
        """Embed N texts. Returns float32 (N, 768) array."""

    @property
    def dim(self) -> int:
        return 768
```

Responsibilities: load model, apply task prompt, return float32 L2-normalized vectors, truncate to `MAX_INPUT_CHARS`. Non-responsibilities: HTTP, verdict labels, Ollama.

The prompt string `"task: classification | query: "` follows Google's published example. If empirical results show a different phrasing performs better, that single constant is the only place to change.

### `LocalBackend` in `aegis_bridge.py` (NEW class, additive)

```python
class LocalBackend:
    def __init__(self, head_path: pathlib.Path = pathlib.Path("aegis-head/lr.joblib")):
        bundle = joblib.load(head_path)
        self._model = bundle["model"]
        self._embed_model = bundle["embed_model"]
        if "embed_task_prompt" not in bundle:
            raise RuntimeError(
                "Head was trained before task-prompt support (Phase 2 artifact). "
                "Retrain via train/train_head.py."
            )
        if "embeddinggemma" not in self._embed_model.lower():
            raise RuntimeError(f"Unexpected embed_model in head: {self._embed_model}")
        self._embedder = Embedder(model_id=self._embed_model)

    def classify(self, text: str) -> dict:
        t0 = time.perf_counter()
        try:
            vec = self._embedder.encode(text, task="classification")
            cls = self._model.predict(vec.reshape(1, -1))[0]
            probs = self._model.predict_proba(vec.reshape(1, -1))[0]
            confidence = float(probs[list(self._model.classes_).index(cls)])
        except Exception as e:
            print(f"[aegis-bridge] LocalBackend classify error: {e}")
            return {
                "tool": "request_permission",
                "arguments": {"reason": f"classifier error: {type(e).__name__}"},
                "confidence": 0.0,
                "time_ms": (time.perf_counter() - t0) * 1000,
            }
        return {
            "tool": cls,
            "arguments": {"reason": f"on-device LR head ({self._embed_model})"},
            "confidence": confidence,
            "time_ms": (time.perf_counter() - t0) * 1000,
        }
```

### `aegis_bridge.py` other changes

Two surgical changes to existing `main()`:

1. Add `--backend {local,ollama}` flag, default `local`.
2. Branch on the flag to construct `_backend = LocalBackend()` or `_backend = OllamaBackend(args.ollama_url, args.model)` (existing path).
3. Extend `/health` to report backend-specific metadata (see Section 4 below).

### `train/train_head.py` changes

Replace the inline `embed_text(text)` urllib call with `Embedder().encode(text, task="classification")`. Everything downstream (CV sweep, fit, save) stays. After fitting, write the joblib bundle with a new `embed_task_prompt` field set to `"classification"` so `LocalBackend` can verify compatibility.

### `train/eval_head.py` changes

Same swap. Plus: load the head's `embed_task_prompt` field and pass it as the `Embedder`'s `default_task`. Verify match between head metadata and `Embedder` config at startup.

### `pyproject.toml` change

```toml
"sentence-transformers>=3.0.0",
```

(Floor is the version with stable EmbeddingGemma support per Google's docs.)

### `aegis-head/lr.joblib` regeneration

The committed Phase 2 / 3a joblib was trained on un-prompted Ollama embeddings. Phase 3b replaces it with a prompt-trained head. The regeneration is part of the implementation work; the file itself is committed as a Phase 3b artifact.

## Data flow

### Runtime classification (the hot path)

```
agent → MCP server → POST /classify {text} → BridgeHandler
                                                  │
                                                  ▼
                                            LocalBackend.classify(text)
                                                  │
                                                  ├── Embedder.encode(text, task="classification")
                                                  │     truncate → prompt-prepend → encode → return (768,) f32
                                                  ├── lr_head.predict(vec) → label
                                                  └── lr_head.predict_proba → confidence
                                                  │
                                                  ▼
                            {tool, arguments, confidence, time_ms}
```

Latency budget per call (warm):

| Step | Time |
|---|---|
| HTTP receive + JSON parse | ~1 ms |
| `Embedder.encode` (model already in RAM) | ~80–120 ms |
| LR predict + predict_proba | ~1 ms |
| Response serialize + send | ~1 ms |
| **Total warm p50** | **~85–125 ms** |

First-call cold-start adds ~1.5–3s for the model to materialize.

### Retraining flow

```
.venv/bin/python train/train_head.py
    Read train/dataset.jsonl (200 rows)
    For each row: Embedder.encode(text, task="classification")
    5-fold stratified CV across C ∈ {0.1, 1.0, 10.0}
    Fit final LR on all 200 at winning C
    joblib.dump({
        "model": fitted_lr,
        "embed_model": "google/embeddinggemma-300m",
        "embed_task_prompt": "classification",     ← NEW field
        "cv_results": {...},
        "C": best_C,
    }, "aegis-head/lr.joblib")
```

### Re-evaluation flow

```
.venv/bin/python train/eval_head.py
    Load joblib; verify embed_model + embed_task_prompt match expected
    For each of 30 CASES: encode + predict + record
    Report accuracy, macro F1, p50/p95/p99, confusion matrix
```

**Decision gate after re-eval:**

- accuracy ≥ 29/30 → ship the prompted head. Commit new `lr.joblib`. Update scorecard.
- accuracy < 29/30 → roll back. Two options: (1) revert `default_task` to no-prompt, retrain, ship that — preserves Phase 3a's 29/30; (2) try an alternate prompt string and re-measure.

### Backend selection at startup

```
python aegis_bridge.py [--backend local|ollama]

if local:
    try LocalBackend()                ← eager joblib + sentence-transformers load
    on failure: print clear error + hint, sys.exit(1)
elif ollama:
    _probe_ollama() (existing, warn-don't-fail)
    OllamaBackend(args.ollama_url, args.model)

HTTPServer.serve_forever()
```

## Error handling

### Layer 1 — dependency / import errors

| Failure | Response |
|---|---|
| `sentence-transformers` not installed | Re-raise ImportError with hint about `uv sync` (dev) or `pipx install aegis-mcp` (end user). Exit 1. |
| `torch` not installed / wrong arch | Same pattern. Exit 1. |
| Python < 3.12 | Defensive version check at bridge startup. Exit 1. |

### Layer 2 — model-load errors (`LocalBackend.__init__`)

| Failure | Response |
|---|---|
| `aegis-head/lr.joblib` missing | Print: `"No trained head. Run: .venv/bin/python train/train_head.py"`. Exit 1. |
| Bundle missing `embed_task_prompt` (pre-3b artifact) | Print retrain hint. Exit 1. |
| `embed_model` mismatch | Print actual vs expected. Exit 1. |
| HF Hub download fails (network, gated model) | Print cause + network-check hint. Exit 1. |
| Disk full during download | Print with disk-full hint. Exit 1. |

All Layer 2 failures exit-1. The bridge cannot run with a broken backend; better to refuse than to half-run.

### Layer 3 — request-time errors

| Failure | Response |
|---|---|
| `Embedder.encode` raises (OOM, tokenizer chokes) | LocalBackend.classify catches. Returns `{tool: "request_permission", confidence: 0.0, ...}`. Logs server-side. |
| `lr_head.predict` raises | Same safe-default. |
| Text empty / missing | Bridge already returns 400; unchanged. |
| Text exceeds `MAX_INPUT_CHARS` | Embedder truncates silently (same as OllamaBackend). |

The safe-default verdict is `request_permission` because it correctly surfaces "we don't know" to the human-in-loop. `classify_safe` would be fail-open (silently pass through possibly-sensitive content); `block_transfer` would deny too much.

### Layer 4 — health endpoint

`GET /health` for `--backend local`:

```json
{
  "status": "ok",
  "backend": "local",
  "embed_model": "google/embeddinggemma-300m",
  "embed_task_prompt": "classification",
  "head_path": "aegis-head/lr.joblib",
  "head_classes": ["block_transfer", "classify_safe", "flag_pii", "request_permission"],
  "head_trained_at_C": 10.0,
  "head_cv_macro_f1": 0.98,
  "device": "mps"
}
```

For `--backend ollama` — unchanged from current.

If the bridge fails to start (Layer 1 or 2), there is no `/health`; the error went to stderr. That's the right behavior.

## Testing strategy

### Layer 1 — `aegis/embedding.py` unit tests

**Cheap (every CI):**

- `test_embedder_truncates_long_input` — input > 8000 chars → encode() works, shape (768,).
- `test_default_task_is_classification` — no-args construction → default_task == "classification".
- `test_encode_per_call_task_overrides_default` — task kwarg overrides default.
- `test_encode_returns_float32_unit_norm` — output dtype is float32 AND L2-normalized.
- `test_mismatched_model_id_raises` — bogus model_id → expected exception.

**Slow (gated, manual / nightly):**

- `test_embedder_returns_768_dim_unit_vector` — real load, shape (768,), norm ≈ 1.0.
- `test_embedder_consistent_across_calls` — determinism.
- `test_prompt_changes_embedding` — classification vs retrieval task → distinct vectors.

### Layer 2 — `LocalBackend` integration tests

**Cheap:**

- `test_localbackend_loads_head_with_correct_metadata` — parses joblib metadata.
- `test_localbackend_refuses_pre_phase3b_head` — bundle without `embed_task_prompt` → RuntimeError.
- `test_localbackend_refuses_mismatched_embed_model` — model_id mismatch → RuntimeError.
- `test_localbackend_classify_returns_request_permission_on_embed_error` — embed raises → safe default.
- `test_localbackend_confidence_matches_predict_proba_for_predicted_class` — confidence is the predicted class's probability.

**Slow:**

- `test_localbackend_classifies_all_30_samples_correctly` — real Embedder + real head, accuracy ≥ 29/30.

### Layer 3 — bridge HTTP tests

**Cheap (mock both backends):**

- `test_bridge_starts_with_default_backend_local` — default args → LocalBackend.
- `test_bridge_starts_with_backend_ollama` — flag → OllamaBackend.
- `test_bridge_exits_when_localbackend_init_fails` — startup fail → sys.exit(1) with hint.
- `test_health_endpoint_reports_backend_type` — correct backend in JSON.
- `test_classify_endpoint_round_trip` — POST → 200 + contract shape.

**Slow:**

- `test_bridge_real_local_serves_30_samples` — real bridge + real backend, accuracy ≥ 29/30, p50 ≤ 200 ms.

### Layer 4 — eval-script verification (decision gate)

After implementation, run `train_head.py` then `eval_head.py` on the 30-sample set. Compare accuracy to Phase 3a's 29/30. **Ship only if accuracy ≥ 29/30.** Captured here so the implementer can't ship a regression.

### Test runner

Add to `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "slow: tests that load the real embeddinggemma model (gated, run manually)",
]
```

### What's intentionally not tested

- HF Hub availability (their bug, not ours).
- GPU vs CPU performance variation.
- `OllamaBackend` correctness (unchanged from Phase 2).
- `sentence-transformers` internal correctness (their tests).

## Scope boundaries

**In scope for Phase 3b:**

- Add `sentence-transformers` dep.
- New `aegis/embedding.py` with `Embedder` class.
- New `LocalBackend` in `aegis_bridge.py`.
- `--backend {local,ollama}` flag, default `local`.
- Switch `train/train_head.py` + `train/eval_head.py` to `Embedder`.
- Retrain `aegis-head/lr.joblib` with `task="classification"` prompts.
- Re-eval on 30-sample set; ship if ≥ 29/30, else roll back per decision gate.
- Update `docs/eval-results/scorecard.md` with new row.
- Update `docs/roadmap.md` Phase 3b row to "done."

**Out of scope (deferred):**

- Wiring `LocalBackend` into the MCP tool-call path — that's Phase 3c.
- PDF / DOCX support — Phase 3d.
- Packaging for marketplace distribution — Phase 4.
- Image support — Phase 5.
- Switching `eval.py` / `benchmark.py` off Ollama. They are the base-model comparison path and should remain there.
- Trying alternative embedders (BGE M3, Snowflake Arctic, etc.) — not needed for 3b.
- Production server tier (TEI). Overkill for single-process MCP plugin use case.
- Telemetry, opt-in usage stats, license decisions — all are Phase 4 concerns.

## References

- [Aegis Roadmap](../../roadmap.md) (Phase 3 sub-pieces)
- [Phase 1/2 scorecard](../../eval-results/scorecard.md)
- [Google EmbeddingGemma inference notebook](https://ai.google.dev/gemma/docs/embeddinggemma/inference-embeddinggemma-with-sentence-transformers)
- [Google EmbeddingGemma fine-tuning notebook](https://ai.google.dev/gemma/docs/embeddinggemma/fine-tuning-embeddinggemma-with-sentence-transformers)
- [`google/embeddinggemma-300m` model card](https://huggingface.co/google/embeddinggemma-300m)
- [Sentence Transformers docs — prompts and tasks](https://sbert.net/)

## Open decisions deferred to implementation

- Exact prompt-string variant — `"task: classification | query: "` is the chosen default but the implementer may A/B against `"Classify the following document: "` if the 30-sample eval result is ambiguous. Either way, only one string ships; the choice is empirical, not architectural.
- Device selection — let `sentence-transformers` auto-detect (CUDA > MPS > CPU). Surface the chosen device in `/health` for debuggability.
- `Embedder.encode_batch` batch-size default — 32 is a reasonable starting point; tune only if profiling shows wins.
