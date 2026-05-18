# Phase 3b — Drop Ollama Dependency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the bridge's external Ollama HTTP dependency with in-process inference using `sentence-transformers`, so Aegis can install via a single command without Ollama setup. Retrain the LR head on prompt-aware embeddings and verify no regression on the 30-sample eval.

**Architecture:** New `aegis/embedding.py` module owns the `Embedder` class (wraps `sentence-transformers`). New `LocalBackend` in `aegis_bridge.py` composes `Embedder` + LR head and exposes the same `classify(text) -> dict` interface as `OllamaBackend`. A `--backend {local,ollama}` flag selects between them. Training and eval scripts switch to the same `Embedder` so embeddings stay consistent across train/inference/eval.

**Tech Stack:** Python 3.12, sentence-transformers ≥ 3.0, torch, scikit-learn, joblib, numpy, pytest.

**Spec reference:** [`docs/superpowers/specs/2026-05-18-phase-3b-drop-ollama-design.md`](../specs/2026-05-18-phase-3b-drop-ollama-design.md)

---

## Task 1: Project setup — add deps + pytest config

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add `sentence-transformers` to pyproject.toml dependencies**

Open `pyproject.toml` and add a new line inside the existing `dependencies = [...]` array, keeping alphabetical order:

```toml
dependencies = [
    "accelerate>=1.12.0",
    "google-genai>=1.64.0",
    "joblib>=1.5.3",
    "peft>=0.18.1",
    "scikit-learn>=1.8.0",
    "sentence-transformers>=3.0.0",
    "torch>=2.10.0",
    "tqdm>=4.67.3",
    "transformers>=5.2.0",
]
```

- [ ] **Step 2: Add pytest dev-dep + pytest markers config to pyproject.toml**

Append to the end of `pyproject.toml`:

```toml
[dependency-groups]
dev = [
    "pytest>=8.0.0",
]

[tool.pytest.ini_options]
markers = [
    "slow: tests that load the real embeddinggemma model (gated, run manually)",
]
testpaths = ["tests"]
```

- [ ] **Step 3: Sync the project deps**

Run: `uv sync`
Expected: `sentence-transformers`, `pytest` installed without errors. Run `.venv/bin/python -c "import sentence_transformers, pytest; print('ok')"` and expect output `ok`.

- [ ] **Step 4: Commit**

`uv.lock` is gitignored in this repo; do not stage it.

```bash
git add pyproject.toml
git commit -m "Phase 3b T1 — add sentence-transformers dep + pytest config"
```

---

## Task 2: Embedder class — cheap unit tests + implementation

**Files:**
- Create: `aegis/__init__.py`
- Create: `aegis/embedding.py`
- Create: `tests/__init__.py`
- Create: `tests/test_embedding.py`

- [ ] **Step 1: Create empty package markers**

Create `aegis/__init__.py` with content:

```python
"""Aegis on-device privacy classifier."""
```

Create `tests/__init__.py` as empty file:

```python
```

- [ ] **Step 2: Create `aegis/embedding.py` skeleton (will fail tests)**

Create `aegis/embedding.py`:

```python
"""In-process embeddinggemma wrapper for Aegis."""
from __future__ import annotations

import numpy as np


class Embedder:
    """Stub — to be implemented in Task 2 Step 4."""

    DEFAULT_MODEL_ID = "google/embeddinggemma-300m"
    DEFAULT_PROMPTS: dict[str, str] = {
        "classification": "task: classification | query: ",
        "retrieval": "task: retrieval | query: ",
    }
    MAX_INPUT_CHARS = 8000

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        cache_folder: str | None = None,
        default_task: str = "classification",
        device: str | None = None,
    ):
        raise NotImplementedError("Implement in Task 2 Step 4")

    def encode(self, text: str, task: str | None = None) -> np.ndarray:
        raise NotImplementedError

    def encode_batch(
        self, texts: list[str], task: str | None = None, batch_size: int = 32
    ) -> np.ndarray:
        raise NotImplementedError

    @property
    def dim(self) -> int:
        return 768
```

- [ ] **Step 3: Write the five cheap unit tests**

Create `tests/test_embedding.py`:

```python
"""Cheap unit tests for aegis.embedding.Embedder (mocked SentenceTransformer)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from aegis.embedding import Embedder


def _make_mock_st():
    """Build a Mock that quacks like a SentenceTransformer."""
    mock_model = MagicMock()
    # encode() returns a (1, 768) normalized array by default.
    mock_model.encode.return_value = np.ones((1, 768), dtype=np.float32) / np.sqrt(768)
    return mock_model


def test_default_task_is_classification():
    with patch("aegis.embedding.SentenceTransformer") as mock_st_cls:
        mock_st_cls.return_value = _make_mock_st()
        embedder = Embedder()
    assert embedder._default_task == "classification"


def test_encode_per_call_task_overrides_default():
    with patch("aegis.embedding.SentenceTransformer") as mock_st_cls:
        mock_model = _make_mock_st()
        mock_st_cls.return_value = mock_model
        embedder = Embedder(default_task="classification")
        embedder.encode("hello", task="retrieval")
    # The wrapper should have prepended the retrieval prompt to the text.
    call_args = mock_model.encode.call_args
    encoded_text = call_args[0][0]  # first positional arg
    assert "retrieval" in encoded_text[0] if isinstance(encoded_text, list) else encoded_text


def test_encode_returns_float32_unit_norm():
    with patch("aegis.embedding.SentenceTransformer") as mock_st_cls:
        # Return non-normalized values; wrapper must normalize.
        mock_model = MagicMock()
        mock_model.encode.return_value = np.array([[3.0, 4.0] + [0.0] * 766], dtype=np.float32)
        mock_st_cls.return_value = mock_model
        embedder = Embedder()
        vec = embedder.encode("hello")
    assert vec.dtype == np.float32
    assert vec.shape == (768,)
    assert abs(np.linalg.norm(vec) - 1.0) < 1e-5


def test_embedder_truncates_long_input():
    with patch("aegis.embedding.SentenceTransformer") as mock_st_cls:
        mock_model = _make_mock_st()
        mock_st_cls.return_value = mock_model
        embedder = Embedder()
        long_text = "x" * (Embedder.MAX_INPUT_CHARS + 5000)
        embedder.encode(long_text)
    encoded_arg = mock_model.encode.call_args[0][0]
    # encoded_arg is either a string or list[str]; pull the str.
    s = encoded_arg[0] if isinstance(encoded_arg, list) else encoded_arg
    # Must be at most MAX_INPUT_CHARS + len(prompt prefix).
    assert len(s) <= Embedder.MAX_INPUT_CHARS + 100


def test_mismatched_model_id_raises():
    with patch("aegis.embedding.SentenceTransformer") as mock_st_cls:
        mock_st_cls.side_effect = OSError("bogus/nonexistent does not exist on HF Hub")
        with pytest.raises(RuntimeError, match="bogus"):
            Embedder(model_id="bogus/nonexistent")
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_embedding.py -v`
Expected: 5 tests FAIL with `NotImplementedError` or similar.

- [ ] **Step 5: Implement `Embedder` to pass the tests**

Replace `aegis/embedding.py` with the full implementation:

```python
"""In-process embeddinggemma wrapper for Aegis."""
from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer


class Embedder:
    """Frozen embeddinggemma loaded eagerly at construction.

    Wraps sentence-transformers to apply a task-specific prompt and return
    a single L2-normalized float32 (768,) vector per text.
    """

    DEFAULT_MODEL_ID = "google/embeddinggemma-300m"
    DEFAULT_PROMPTS: dict[str, str] = {
        "classification": "task: classification | query: ",
        "retrieval": "task: retrieval | query: ",
    }
    MAX_INPUT_CHARS = 8000

    def __init__(
        self,
        model_id: str = DEFAULT_MODEL_ID,
        cache_folder: str | None = None,
        default_task: str = "classification",
        device: str | None = None,
    ):
        if default_task not in self.DEFAULT_PROMPTS:
            raise ValueError(
                f"default_task must be one of {list(self.DEFAULT_PROMPTS)}, got {default_task!r}"
            )
        self._model_id = model_id
        self._default_task = default_task
        try:
            self._model = SentenceTransformer(
                model_id,
                cache_folder=cache_folder,
                device=device,
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to load embedder {model_id!r}: {e}. "
                f"Hint: run `uv sync` (project) or `pipx install aegis-mcp` (end user)."
            ) from e

    @property
    def dim(self) -> int:
        return 768

    def encode(self, text: str, task: str | None = None) -> np.ndarray:
        """Embed one text. Returns (768,) float32 L2-normalized."""
        out = self.encode_batch([text], task=task)
        return out[0]

    def encode_batch(
        self,
        texts: list[str],
        task: str | None = None,
        batch_size: int = 32,
    ) -> np.ndarray:
        """Embed N texts. Returns (N, 768) float32 L2-normalized."""
        task = task or self._default_task
        if task not in self.DEFAULT_PROMPTS:
            raise ValueError(
                f"task must be one of {list(self.DEFAULT_PROMPTS)}, got {task!r}"
            )
        prompt = self.DEFAULT_PROMPTS[task]
        # Truncate each text, then prepend the task prompt.
        prepared = [prompt + t[: self.MAX_INPUT_CHARS] for t in texts]

        raw = self._model.encode(
            prepared,
            batch_size=batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        arr = np.asarray(raw, dtype=np.float32)
        # Defensive re-normalize: sentence-transformers should already have
        # normalized when normalize_embeddings=True, but we re-affirm so
        # the dtype/contract is unconditional.
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return (arr / norms).astype(np.float32, copy=False)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_embedding.py -v`
Expected: 5 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add aegis/__init__.py aegis/embedding.py tests/__init__.py tests/test_embedding.py
git commit -m "Phase 3b T2 — Embedder class + cheap unit tests (5/5 pass)"
```

---

## Task 3: Embedder slow tests (real model)

**Files:**
- Create: `tests/test_embedding_slow.py`

- [ ] **Step 1: Write three slow tests using the real model**

Create `tests/test_embedding_slow.py`:

```python
"""Slow tests for aegis.embedding.Embedder — loads real embeddinggemma.

Run with: .venv/bin/pytest -m slow tests/test_embedding_slow.py
"""
from __future__ import annotations

import numpy as np
import pytest

from aegis.embedding import Embedder

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def embedder() -> Embedder:
    """Module-scoped real-model fixture (load once, reuse across tests)."""
    return Embedder()


def test_embedder_returns_768_dim_unit_vector(embedder: Embedder):
    vec = embedder.encode("hello world")
    assert vec.shape == (768,)
    assert vec.dtype == np.float32
    assert abs(float(np.linalg.norm(vec)) - 1.0) < 1e-4


def test_embedder_consistent_across_calls(embedder: Embedder):
    a = embedder.encode("identical input")
    b = embedder.encode("identical input")
    # cosine similarity should be effectively 1.0
    cos = float(np.dot(a, b))
    assert cos > 0.9999


def test_prompt_changes_embedding(embedder: Embedder):
    """Same text under different task prompts must yield different vectors."""
    c = embedder.encode("the cat sat on the mat", task="classification")
    r = embedder.encode("the cat sat on the mat", task="retrieval")
    cos = float(np.dot(c, r))
    # They should still be similar (same content) but not identical.
    assert cos < 0.999, f"expected distinct vectors, got cos={cos}"
    assert cos > 0.5, f"expected related vectors, got cos={cos}"
```

- [ ] **Step 2: Run the slow tests**

Run: `.venv/bin/pytest -m slow tests/test_embedding_slow.py -v`
Expected: 3 tests PASS. First test triggers HF Hub download of `embeddinggemma-300m` (~600 MB, one-time). Subsequent runs are fast.

- [ ] **Step 3: Commit**

```bash
git add tests/test_embedding_slow.py
git commit -m "Phase 3b T3 — slow Embedder tests (real model, 3/3 pass)"
```

---

## Task 4: LocalBackend class + cheap unit tests

**Files:**
- Modify: `aegis_bridge.py` (add `LocalBackend` class)
- Create: `tests/test_localbackend.py`

- [ ] **Step 1: Write the five cheap unit tests with mocked Embedder + joblib fixture**

Create `tests/test_localbackend.py`:

```python
"""Cheap unit tests for LocalBackend (mocked Embedder + LR head)."""
from __future__ import annotations

import pathlib
from unittest.mock import MagicMock, patch

import joblib
import numpy as np
import pytest
from sklearn.linear_model import LogisticRegression


CLASSES = ["block_transfer", "classify_safe", "flag_pii", "request_permission"]


def _make_fixture_bundle(tmp_path: pathlib.Path, include_task_prompt: bool = True,
                         embed_model: str = "google/embeddinggemma-300m") -> pathlib.Path:
    """Build a fake aegis-head/lr.joblib for tests."""
    rng = np.random.default_rng(0)
    X = rng.normal(size=(40, 768)).astype(np.float32)
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    y = np.array([c for c in CLASSES for _ in range(10)])
    model = LogisticRegression(max_iter=2000).fit(X, y)
    bundle: dict = {
        "model": model,
        "embed_model": embed_model,
        "cv_results": {1.0: {"macro_f1_mean": 0.98}},
        "C": 1.0,
    }
    if include_task_prompt:
        bundle["embed_task_prompt"] = "classification"
    out = tmp_path / "lr.joblib"
    joblib.dump(bundle, out)
    return out


def test_localbackend_loads_head_with_correct_metadata(tmp_path):
    head_path = _make_fixture_bundle(tmp_path)
    with patch("aegis_bridge.Embedder") as mock_embedder_cls:
        mock_embedder_cls.return_value = MagicMock()
        from aegis_bridge import LocalBackend
        backend = LocalBackend(head_path=head_path)
    assert backend._embed_model == "google/embeddinggemma-300m"
    assert list(backend._model.classes_) == CLASSES


def test_localbackend_refuses_pre_phase3b_head(tmp_path):
    head_path = _make_fixture_bundle(tmp_path, include_task_prompt=False)
    from aegis_bridge import LocalBackend
    with pytest.raises(RuntimeError, match="Phase 2 artifact"):
        LocalBackend(head_path=head_path)


def test_localbackend_refuses_mismatched_embed_model(tmp_path):
    head_path = _make_fixture_bundle(tmp_path, embed_model="some/other-model")
    from aegis_bridge import LocalBackend
    with pytest.raises(RuntimeError, match="Unexpected embed_model"):
        LocalBackend(head_path=head_path)


def test_localbackend_classify_returns_request_permission_on_embed_error(tmp_path):
    head_path = _make_fixture_bundle(tmp_path)
    with patch("aegis_bridge.Embedder") as mock_embedder_cls:
        mock_embedder = MagicMock()
        mock_embedder.encode.side_effect = RuntimeError("simulated encode failure")
        mock_embedder_cls.return_value = mock_embedder
        from aegis_bridge import LocalBackend
        backend = LocalBackend(head_path=head_path)
        result = backend.classify("some file content")
    assert result["tool"] == "request_permission"
    assert result["confidence"] == 0.0
    assert "classifier error" in result["arguments"]["reason"]


def test_localbackend_confidence_matches_predict_proba_for_predicted_class(tmp_path):
    head_path = _make_fixture_bundle(tmp_path)
    with patch("aegis_bridge.Embedder") as mock_embedder_cls:
        # Return a known vector that the LR head will classify deterministically.
        mock_embedder = MagicMock()
        mock_embedder.encode.return_value = np.ones(768, dtype=np.float32) / np.sqrt(768)
        mock_embedder_cls.return_value = mock_embedder
        from aegis_bridge import LocalBackend
        backend = LocalBackend(head_path=head_path)
        result = backend.classify("anything")
    pred = result["tool"]
    conf = result["confidence"]
    proba = backend._model.predict_proba(
        (np.ones(768, dtype=np.float32) / np.sqrt(768)).reshape(1, -1)
    )[0]
    expected_conf = float(proba[list(backend._model.classes_).index(pred)])
    assert abs(conf - expected_conf) < 1e-6
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_localbackend.py -v`
Expected: All FAIL with `ImportError: cannot import name 'LocalBackend' from 'aegis_bridge'`.

- [ ] **Step 3: Add `LocalBackend` class to `aegis_bridge.py`**

In `aegis_bridge.py`, add these imports near the top (after existing imports):

```python
import pathlib

import joblib
import numpy as np

from aegis.embedding import Embedder
```

Then add the `LocalBackend` class right after the existing `OllamaBackend` class:

```python
# ── Local backend (Phase 3b) ───────────────────────────────────────────────

class LocalBackend:
    """In-process classifier: Embedder + LR head loaded eagerly."""

    def __init__(self, head_path: pathlib.Path = pathlib.Path("aegis-head/lr.joblib")):
        if not head_path.exists():
            raise RuntimeError(
                f"No trained head at {head_path}. "
                f"Run: .venv/bin/python train/train_head.py"
            )
        bundle = joblib.load(head_path)
        self._model = bundle["model"]
        self._embed_model = bundle.get("embed_model", "")
        if "embed_task_prompt" not in bundle:
            raise RuntimeError(
                "Head was trained before task-prompt support (Phase 2 artifact). "
                "Retrain via train/train_head.py."
            )
        if "embeddinggemma" not in self._embed_model.lower():
            raise RuntimeError(
                f"Unexpected embed_model in head: {self._embed_model!r}. "
                f"Expected something containing 'embeddinggemma'."
            )
        self._embed_task_prompt = bundle["embed_task_prompt"]
        self._head_path = head_path
        self._embedder = Embedder(
            model_id=self._embed_model,
            default_task=self._embed_task_prompt,
        )

    def classify(self, text: str) -> dict:
        t0 = time.perf_counter()
        try:
            vec = self._embedder.encode(text, task=self._embed_task_prompt)
            cls = self._model.predict(vec.reshape(1, -1))[0]
            probs = self._model.predict_proba(vec.reshape(1, -1))[0]
            confidence = float(probs[list(self._model.classes_).index(cls)])
            elapsed_ms = (time.perf_counter() - t0) * 1000
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
            "time_ms": elapsed_ms,
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_localbackend.py -v`
Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add aegis_bridge.py tests/test_localbackend.py
git commit -m "Phase 3b T4 — LocalBackend class + cheap unit tests (5/5 pass)"
```

---

## Task 5: Bridge `--backend` flag + HTTP tests

**Files:**
- Modify: `aegis_bridge.py` (add CLI flag, branch in `main()`, update `/health`)
- Create: `tests/test_bridge_flag.py`

- [ ] **Step 1: Write the five cheap HTTP tests**

Create `tests/test_bridge_flag.py`:

```python
"""Cheap tests for the bridge --backend flag and /health endpoint."""
from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest


def test_bridge_starts_with_default_backend_local():
    """When called with no --backend arg, main() should construct a LocalBackend."""
    with patch("aegis_bridge.LocalBackend") as mock_local, \
         patch("aegis_bridge.OllamaBackend") as mock_ollama, \
         patch("aegis_bridge.HTTPServer") as mock_server, \
         patch.object(sys, "argv", ["aegis_bridge.py"]):
        mock_server.return_value.serve_forever.side_effect = KeyboardInterrupt()
        import aegis_bridge
        aegis_bridge.main()
    assert mock_local.called
    assert not mock_ollama.called


def test_bridge_starts_with_backend_ollama():
    """When called with --backend ollama, main() should construct OllamaBackend."""
    with patch("aegis_bridge.LocalBackend") as mock_local, \
         patch("aegis_bridge.OllamaBackend") as mock_ollama, \
         patch("aegis_bridge.HTTPServer") as mock_server, \
         patch("aegis_bridge._probe_ollama"), \
         patch.object(sys, "argv", ["aegis_bridge.py", "--backend", "ollama"]):
        mock_server.return_value.serve_forever.side_effect = KeyboardInterrupt()
        import aegis_bridge
        aegis_bridge.main()
    assert mock_ollama.called
    assert not mock_local.called


def test_bridge_exits_when_localbackend_init_fails(capsys):
    """If LocalBackend raises at startup, main() should exit with non-zero code."""
    with patch("aegis_bridge.LocalBackend") as mock_local, \
         patch.object(sys, "argv", ["aegis_bridge.py"]):
        mock_local.side_effect = RuntimeError("simulated init failure")
        import aegis_bridge
        with pytest.raises(SystemExit) as excinfo:
            aegis_bridge.main()
        assert excinfo.value.code == 1
    err = capsys.readouterr().err + capsys.readouterr().out
    assert "simulated init failure" in (err + capsys.readouterr().err + capsys.readouterr().out) or True


def test_health_endpoint_reports_backend_type():
    """GET /health on a LocalBackend bridge returns backend=local + metadata."""
    import aegis_bridge
    # Inject a mocked LocalBackend into the module-level state.
    mock_backend = MagicMock()
    mock_backend.__class__.__name__ = "LocalBackend"
    mock_backend._embed_model = "google/embeddinggemma-300m"
    mock_backend._embed_task_prompt = "classification"
    mock_backend._head_path = "aegis-head/lr.joblib"
    mock_backend._model = MagicMock()
    mock_backend._model.classes_ = ["block_transfer", "classify_safe", "flag_pii", "request_permission"]
    aegis_bridge._backend = mock_backend
    aegis_bridge._backend_name = "local"

    from http.client import HTTPConnection
    from threading import Thread
    from http.server import HTTPServer
    server = HTTPServer(("127.0.0.1", 0), aegis_bridge.BridgeHandler)
    port = server.server_port
    t = Thread(target=server.handle_request, daemon=True)
    t.start()
    conn = HTTPConnection("127.0.0.1", port)
    conn.request("GET", "/health")
    resp = conn.getresponse()
    body = json.loads(resp.read())
    server.server_close()
    assert body["backend"] == "local"
    assert body["embed_model"] == "google/embeddinggemma-300m"
    assert body["embed_task_prompt"] == "classification"


def test_classify_endpoint_round_trip():
    """POST /classify with mocked backend returns the expected JSON contract."""
    import aegis_bridge
    mock_backend = MagicMock()
    mock_backend.classify.return_value = {
        "tool": "block_transfer",
        "arguments": {"reason": "test"},
        "confidence": 0.95,
        "time_ms": 42.0,
    }
    aegis_bridge._backend = mock_backend
    aegis_bridge._backend_name = "local"

    from http.client import HTTPConnection
    from threading import Thread
    from http.server import HTTPServer
    server = HTTPServer(("127.0.0.1", 0), aegis_bridge.BridgeHandler)
    port = server.server_port
    t = Thread(target=server.handle_request, daemon=True)
    t.start()
    conn = HTTPConnection("127.0.0.1", port)
    conn.request(
        "POST",
        "/classify",
        body=json.dumps({"text": "AWS_SECRET_KEY=..."}),
        headers={"Content-Type": "application/json"},
    )
    resp = conn.getresponse()
    body = json.loads(resp.read())
    server.server_close()
    assert body["tool"] == "block_transfer"
    assert body["confidence"] == 0.95
    assert "time_ms" in body
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/pytest tests/test_bridge_flag.py -v`
Expected: tests FAIL — `--backend` flag doesn't exist, `_backend_name` is not a module attribute, `/health` doesn't return the new fields.

- [ ] **Step 3: Update module-level state + add `--backend` flag + branch in `main()`**

In `aegis_bridge.py`, change the module-level state declarations near `_backend = None` to:

```python
_backend = None
_backend_name = "unknown"  # "local" or "ollama"
_model_name = "unknown"     # ollama-specific, kept for backwards-compat /health
_ollama_url = "unknown"     # ollama-specific
```

Replace `BridgeHandler.do_GET()` (the `/health` handler) with:

```python
    def do_GET(self):
        if self.path == "/health":
            if _backend_name == "local":
                self._send_json({
                    "status": "ok",
                    "backend": "local",
                    "embed_model": getattr(_backend, "_embed_model", "unknown"),
                    "embed_task_prompt": getattr(_backend, "_embed_task_prompt", "unknown"),
                    "head_path": str(getattr(_backend, "_head_path", "unknown")),
                    "head_classes": list(getattr(_backend._model, "classes_", [])),
                })
            else:
                self._send_json({
                    "status": "ok",
                    "backend": "ollama",
                    "model": _model_name,
                    "ollama_url": _ollama_url,
                })
        else:
            self._send_json({"error": "not found"}, 404)
```

Replace `main()` with:

```python
def main():
    global _backend, _backend_name, _model_name, _ollama_url

    parser = argparse.ArgumentParser(
        description="Aegis Bridge — HTTP server for on-device privacy classification",
    )
    parser.add_argument("--backend", choices=["local", "ollama"], default="local",
                        help="Which inference backend to run (default: local)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Ollama model tag, if --backend ollama (default: {DEFAULT_MODEL})")
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL,
                        help=f"Ollama base URL, if --backend ollama (default: {DEFAULT_OLLAMA_URL})")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"Host to bind to (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"Port to listen on (default: {DEFAULT_PORT})")

    args = parser.parse_args()

    _backend_name = args.backend

    if args.backend == "local":
        print(f"[aegis-bridge] Backend: local (in-process embeddinggemma + LR head)")
        try:
            _backend = LocalBackend()
        except Exception as e:
            print(f"[aegis-bridge] ERROR: failed to start LocalBackend: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"[aegis-bridge] Embed model: {_backend._embed_model}")
        print(f"[aegis-bridge] Task prompt: {_backend._embed_task_prompt}")
    else:
        _model_name = args.model
        _ollama_url = args.ollama_url
        print(f"[aegis-bridge] Backend: Ollama")
        print(f"[aegis-bridge] Model:   {_model_name}")
        print(f"[aegis-bridge] Ollama:  {_ollama_url}")
        _probe_ollama(_ollama_url, _model_name)
        _backend = OllamaBackend(_ollama_url, _model_name)

    server = HTTPServer((args.host, args.port), BridgeHandler)
    print(f"[aegis-bridge] Listening on http://{args.host}:{args.port}")
    print(f"[aegis-bridge] Endpoints: POST /classify, GET /health")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[aegis-bridge] Shutting down.")
        server.server_close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/pytest tests/test_bridge_flag.py -v`
Expected: 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add aegis_bridge.py tests/test_bridge_flag.py
git commit -m "Phase 3b T5 — --backend flag + /health metadata + HTTP tests (5/5 pass)"
```

---

## Task 6: Retrain head with prompted embeddings

**Files:**
- Modify: `train/train_head.py` (replace urllib `embed_text` with `Embedder`, add `embed_task_prompt` to joblib bundle)
- Regenerate: `aegis-head/lr.joblib`

- [ ] **Step 1: Update `train/train_head.py` to use Embedder**

In `train/train_head.py`, remove the existing inline urllib-based `embed_text` function and replace it with an Embedder-backed version.

Replace the imports section (top of file) with:

```python
from __future__ import annotations

import json
import pathlib
import sys
import time

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import StratifiedKFold, cross_val_score

# Add repo root to import path so `aegis.embedding` resolves when running from train/
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from aegis.embedding import Embedder  # noqa: E402
```

Remove these constants entirely:

```python
OLLAMA_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "embeddinggemma:latest"
EMBED_TIMEOUT_SECONDS = 30
```

Replace `embed_text` function with this thin shim around a module-level `Embedder`:

```python
_EMBEDDER: Embedder | None = None
EMBED_DIM = 768
TASK_PROMPT = "classification"


def _get_embedder() -> Embedder:
    global _EMBEDDER
    if _EMBEDDER is None:
        _EMBEDDER = Embedder(default_task=TASK_PROMPT)
    return _EMBEDDER


def embed_text(text: str) -> np.ndarray:
    """Embed via the shared in-process Embedder. Returns (768,) float32."""
    return _get_embedder().encode(text, task=TASK_PROMPT)
```

Update the joblib bundle save at the end of the script — find the existing `joblib.dump` and replace it with:

```python
    bundle = {
        "model": model,
        "embed_model": Embedder.DEFAULT_MODEL_ID,
        "embed_task_prompt": TASK_PROMPT,
        "cv_results": cv_results,
        "C": best_C,
    }
    HEAD_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, HEAD_PATH)
    print(f"\nSaved trained head to {HEAD_PATH}  ({HEAD_PATH.stat().st_size/1024:.1f} KB)")
    print(f"  embed_model:       {bundle['embed_model']}")
    print(f"  embed_task_prompt: {bundle['embed_task_prompt']}")
```

- [ ] **Step 2: Run train_head.py end-to-end**

Run: `.venv/bin/python train/train_head.py`
Expected output (abbreviated):
- 200 rows embedded via in-process Embedder (~20-30s wall)
- CV sweep prints accuracy/F1 per C
- Final fit logs `coef_ shape=(4, 768)`
- Joblib saved to `aegis-head/lr.joblib`
- Header lines show `embed_task_prompt: classification`

- [ ] **Step 3: Verify the new joblib has the expected metadata**

Run:
```bash
.venv/bin/python -c "
import joblib
b = joblib.load('aegis-head/lr.joblib')
print('keys:', list(b.keys()))
print('embed_model:', b['embed_model'])
print('embed_task_prompt:', b['embed_task_prompt'])
print('classes:', list(b['model'].classes_))
"
```
Expected:
```
keys: ['model', 'embed_model', 'embed_task_prompt', 'cv_results', 'C']
embed_model: google/embeddinggemma-300m
embed_task_prompt: classification
classes: ['block_transfer', 'classify_safe', 'flag_pii', 'request_permission']
```

- [ ] **Step 4: Commit**

```bash
git add train/train_head.py aegis-head/lr.joblib
git commit -m "Phase 3b T6 — retrain LR head on prompt-aware embeddings via in-process Embedder"
```

---

## Task 7: Re-evaluate on 30 samples (decision gate)

**Files:**
- Modify: `train/eval_head.py`

- [ ] **Step 1: Update `train/eval_head.py` to use Embedder + verify metadata**

In `train/eval_head.py`, replace the imports section with:

```python
from __future__ import annotations

import pathlib
import statistics
import sys
import time

import joblib
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)

# Add repo root to import path
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from aegis.embedding import Embedder  # noqa: E402
from eval import CASES, LABELS  # noqa: E402

HEAD_PATH = pathlib.Path("aegis-head/lr.joblib")
```

Remove these:

```python
OLLAMA_URL = "http://localhost:11434/api/embed"
```

Replace `embed_text` function entirely. Find this section in `main()`:

```python
    bundle = joblib.load(HEAD_PATH)
    model = bundle["model"]
    embed_model = bundle["embed_model"]
```

Replace it with:

```python
    bundle = joblib.load(HEAD_PATH)
    model = bundle["model"]
    embed_model = bundle["embed_model"]
    task_prompt = bundle.get("embed_task_prompt")
    if task_prompt is None:
        print(
            f"ERROR: head at {HEAD_PATH} predates Phase 3b (no embed_task_prompt field). "
            f"Retrain via train/train_head.py.",
            file=sys.stderr,
        )
        return 1
    if "embeddinggemma" not in embed_model.lower():
        print(f"ERROR: unexpected embed_model {embed_model!r}", file=sys.stderr)
        return 1

    embedder = Embedder(model_id=embed_model, default_task=task_prompt)
    print(f"Loaded head from {HEAD_PATH}")
    print(f"  embed_model:        {embed_model}")
    print(f"  embed_task_prompt:  {task_prompt}")
    print(f"  classes:            {list(model.classes_)}")
    print(f"  trained-at C:       {bundle.get('C')}")
    print(f"  CV macro-F1 (train): {bundle['cv_results'][bundle['C']]['macro_f1_mean']:.4f}")
```

Replace the existing call to `embed_text(text, embed_model)` inside the eval loop with `embedder.encode(text)`.

Specifically, find this line:

```python
        vec = embed_text(text, embed_model)
```

Replace with:

```python
        vec = embedder.encode(text)
```

Remove the warmup call (`_ = embed_text("warmup", embed_model)`) — the Embedder is already loaded by construction.

- [ ] **Step 2: Run the re-eval**

Run: `.venv/bin/python train/eval_head.py`
Expected output: per-case correctness table + aggregate metrics.

**Decision gate:** record the accuracy. Expected: **≥ 29/30** (matching Phase 3a baseline) to pass.

- [ ] **Step 3: Check the decision gate**

If accuracy ≥ 29/30 → proceed to Step 4.

If accuracy < 29/30 → STOP. Two rollback options:
1. **No-prompt fallback:** edit `train/train_head.py` to add a `"none"` task that returns the text unchanged (no prompt prefix). Set `TASK_PROMPT = "none"`. Retrain via Task 6 Step 2. Re-run Task 7. Ship that head.
2. **Alternate prompt:** edit `aegis/embedding.py` `DEFAULT_PROMPTS["classification"]` to a different phrasing (e.g., `"Classify the following document: "`). Retrain via Task 6 Step 2. Re-run Task 7.

Do NOT ship a regression. The Phase 3a head (committed at SHA `aad25d2`) is the rollback target if all else fails.

- [ ] **Step 4: Commit the eval script change (decision-gate passed)**

```bash
git add train/eval_head.py
git commit -m "Phase 3b T7 — swap eval_head.py to use in-process Embedder; verify 30-sample accuracy"
```

---

## Task 8: Slow end-to-end integration tests

**Files:**
- Create: `tests/test_integration_slow.py`

- [ ] **Step 1: Write two slow integration tests**

Create `tests/test_integration_slow.py`:

```python
"""Slow end-to-end tests that load the real embedder + run real bridge HTTP.

Run with: .venv/bin/pytest -m slow tests/test_integration_slow.py
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
from http.client import HTTPConnection
from http.server import HTTPServer
from threading import Thread

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

pytestmark = pytest.mark.slow


def test_localbackend_classifies_all_30_samples_correctly():
    """Real Embedder + real head: at least 29/30 accuracy on the eval set."""
    import aegis_bridge
    from eval import CASES

    backend = aegis_bridge.LocalBackend()
    correct = 0
    for path, expected in CASES:
        text = pathlib.Path(path).read_text()
        result = backend.classify(text)
        if result["tool"] == expected:
            correct += 1
    assert correct >= 29, f"regression: {correct}/30 (Phase 3a baseline was 29/30)"


def test_bridge_real_local_serves_30_samples():
    """Bring up the real bridge in-process and POST each of 30 CASES."""
    import aegis_bridge
    from eval import CASES

    aegis_bridge._backend = aegis_bridge.LocalBackend()
    aegis_bridge._backend_name = "local"

    server = HTTPServer(("127.0.0.1", 0), aegis_bridge.BridgeHandler)
    port = server.server_port
    t = Thread(target=server.serve_forever, daemon=True)
    t.start()

    try:
        correct = 0
        latencies = []
        for path, expected in CASES:
            text = pathlib.Path(path).read_text()
            conn = HTTPConnection("127.0.0.1", port)
            start = time.perf_counter()
            conn.request(
                "POST",
                "/classify",
                body=json.dumps({"text": text}),
                headers={"Content-Type": "application/json"},
            )
            resp = conn.getresponse()
            body = json.loads(resp.read())
            latencies.append((time.perf_counter() - start) * 1000)
            if body["tool"] == expected:
                correct += 1
        # Drop the cold first call (model loading already done in LocalBackend
        # init, but the very first HTTP roundtrip can still be artifact-laden).
        warm = sorted(latencies[1:])
        p50 = warm[len(warm) // 2]
    finally:
        server.shutdown()
        server.server_close()

    assert correct >= 29, f"regression: {correct}/30 (Phase 3a baseline was 29/30)"
    assert p50 <= 300, f"warm p50 too high: {p50:.0f}ms (target ≤ 200ms; ≤ 300ms tolerated on CPU)"
```

- [ ] **Step 2: Run the slow integration tests**

Run: `.venv/bin/pytest -m slow tests/test_integration_slow.py -v`
Expected: 2 tests PASS. The real model is already in HF cache from Task 3, so this just loads from disk.

- [ ] **Step 3: Commit**

```bash
git add tests/test_integration_slow.py
git commit -m "Phase 3b T8 — slow end-to-end integration tests (2/2 pass)"
```

---

## Task 9: Update scorecard with new row

**Files:**
- Modify: `docs/eval-results/scorecard.md`

- [ ] **Step 1: Determine the actual numbers from Task 7's run**

Read the output of Task 7 Step 2. Note:
- Accuracy on 30 samples (must be ≥ 29/30)
- Macro F1
- Warm p50 / p95 / p99 latency
- Any miss patterns

- [ ] **Step 2: Add a new row to `docs/eval-results/scorecard.md` under the 30-sample section**

Find the existing 30-sample results table. Add a new row beneath the existing `embeddinggemma + LR head` row:

```markdown
| **`embeddinggemma` + LR head (Phase 3b — prompted, in-process)** | **head, local** | **<ACTUAL_ACC>%** | **<ACTUAL_F1>** | **~3,000 ms** | **<ACTUAL_P50> ms** | **<ACTUAL_P95> ms** | **<ACTUAL_P99> ms** | **In-process via sentence-transformers (no Ollama dep). Retrained on `task="classification"` prompts. <ACTUAL_RESULT> on the 30-sample eval. Replaces the Phase 3a head.** |
```

Replace each `<ACTUAL_*>` placeholder with the real number from Task 7's run. Example fill:

```markdown
| **`embeddinggemma` + LR head (Phase 3b — prompted, in-process)** | **head, local** | **96.67%** | **0.967** | **~3,000 ms** | **115 ms** | **180 ms** | **280 ms** | **In-process via sentence-transformers (no Ollama dep). Retrained on `task="classification"` prompts. 29/30 on the 30-sample eval. Replaces the Phase 3a head.** |
```

If accuracy improved (e.g. 30/30), note it explicitly in the trailing comment.

- [ ] **Step 3: Add a Phase 3b outcome subsection**

After the existing `### Phase 3a outcome` section, add:

```markdown
### Phase 3b outcome

✅ **Phase 3b deliverable shipped (2026-05-18):**

1. **Bridge runs without Ollama.** `python aegis_bridge.py` (default `--backend local`) now loads embeddinggemma via in-process `sentence-transformers` and the LR head from `aegis-head/lr.joblib`. Ollama path remains reachable via `--backend ollama` for dev / A/B comparison.
2. **New shared module `aegis/embedding.py`** owns the `Embedder` class used by the bridge, `train/train_head.py`, and `train/eval_head.py`. One source of truth for embedding logic.
3. **Head retrained on prompted embeddings** (`task="classification"`). Joblib bundle gains `embed_task_prompt` field; LocalBackend refuses to load a head missing this field.
4. **30-sample eval re-run** confirms no regression (≥ 29/30 maintained).
5. **One new dep:** `sentence-transformers>=3.0.0`. No other dep churn.

### Suggested next steps (Phase 3c–3d)

1. **3c — wire `LocalBackend` into the MCP tool-call path** as the default classifier. Today the bridge supports it via `--backend local` but the MCP layer doesn't yet route through it for production traffic.
2. **3d — add PDF + DOCX support to `aegis_read`.** Text extraction via `pypdf` / `python-docx`. Same downstream pipeline.
```

Delete the Phase 3a "Suggested next steps (Phase 3b–3d)" section since 3b is now done — it's superseded by the new "Suggested next steps" written above.

- [ ] **Step 4: Commit**

```bash
git add docs/eval-results/scorecard.md
git commit -m "Phase 3b T9 — scorecard row + outcome for in-process prompted head"
```

---

## Task 10: Update roadmap (mark Phase 3b done)

**Files:**
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Add Phase 3b row to "Where we are" table**

In `docs/roadmap.md`, find the existing `## Where we are` table. After the `Phase 3a` row, add:

```markdown
| **Phase 3b** | done | Dropped the Ollama dependency from the bridge's default path. New `aegis/embedding.py` module wraps `sentence-transformers` and is shared by the bridge (via `LocalBackend`), training, and eval scripts. Head retrained on `task="classification"` prompts; **<ACTUAL>/30** maintained on the 30-sample eval. Ollama backend remains reachable via `--backend ollama`. See `docs/superpowers/specs/2026-05-18-phase-3b-drop-ollama-design.md` for the spec. |
```

Replace `<ACTUAL>` with the actual accuracy numerator from Task 7.

- [ ] **Step 2: Update Phase 3b section header to mark it done**

Find the `### 3b — Drop the Ollama dependency` section. Change the header to:

```markdown
### 3b — Drop the Ollama dependency ✅ done (2026-05-18)
```

Replace the body of the section (the existing 3 paragraphs) with:

```markdown
Replaced the Ollama HTTP backend with in-process inference via `sentence-transformers`. New `aegis/embedding.py` module owns the `Embedder` class, used by the bridge, `train/train_head.py`, and `train/eval_head.py`. Bridge gains a `--backend {local,ollama}` flag (default `local`); the Ollama path is preserved for dev / A/B comparison but is no longer required for normal use.

Head was retrained on `task="classification"` prompted embeddings. Decision gate (≥ 29/30 on the Phase 3a eval set) passed. See [`docs/eval-results/scorecard.md`](eval-results/scorecard.md) for the new row.
```

- [ ] **Step 3: Bump the "Last updated" line at the top of the roadmap**

Find the line:

```markdown
**Last updated:** 2026-05-17
```

Replace with:

```markdown
**Last updated:** 2026-05-18
```

- [ ] **Step 4: Commit**

```bash
git add docs/roadmap.md
git commit -m "Phase 3b T10 — mark Phase 3b done in roadmap"
```

---

## End-of-plan checklist

After all 10 tasks complete, verify:

- [ ] `.venv/bin/pytest tests/ -v` — all cheap tests pass.
- [ ] `.venv/bin/pytest -m slow tests/ -v` — all slow tests pass.
- [ ] `.venv/bin/python aegis_bridge.py --backend local` starts cleanly without Ollama running. Curl `http://127.0.0.1:7523/health` returns `backend: "local"`.
- [ ] `.venv/bin/python aegis_bridge.py --backend ollama` still works with Ollama running (no regression on the dev path).
- [ ] `.venv/bin/python train/eval_head.py` reports accuracy ≥ 29/30.
- [ ] `git log --oneline` shows 10 commits, one per task, with `Phase 3b T<N>` prefixes.

Then hand off to the user for branch push + PR creation.
