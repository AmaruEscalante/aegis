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
    """Build a fake aegis/head/lr.joblib for tests."""
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
    with patch("aegis.bridge.Embedder") as mock_embedder_cls:
        mock_embedder_cls.return_value = MagicMock()
        from aegis.bridge import LocalBackend
        backend = LocalBackend(head_path=head_path)
    assert backend._embed_model == "google/embeddinggemma-300m"
    assert list(backend._model.classes_) == CLASSES


def test_localbackend_refuses_pre_phase3b_head(tmp_path):
    head_path = _make_fixture_bundle(tmp_path, include_task_prompt=False)
    from aegis.bridge import LocalBackend
    with pytest.raises(RuntimeError, match="Phase 2 artifact"):
        LocalBackend(head_path=head_path)


def test_localbackend_refuses_mismatched_embed_model(tmp_path):
    head_path = _make_fixture_bundle(tmp_path, embed_model="some/other-model")
    from aegis.bridge import LocalBackend
    with pytest.raises(RuntimeError, match="Unexpected embed_model"):
        LocalBackend(head_path=head_path)


def test_localbackend_classify_returns_request_permission_on_embed_error(tmp_path):
    head_path = _make_fixture_bundle(tmp_path)
    with patch("aegis.bridge.Embedder") as mock_embedder_cls:
        mock_embedder = MagicMock()
        mock_embedder.encode.side_effect = RuntimeError("simulated encode failure")
        mock_embedder_cls.return_value = mock_embedder
        from aegis.bridge import LocalBackend
        backend = LocalBackend(head_path=head_path)
        result = backend.classify("some file content")
    assert result["tool"] == "request_permission"
    assert result["confidence"] == 0.0
    assert "classifier error" in result["arguments"]["reason"]


def test_localbackend_confidence_matches_predict_proba_for_predicted_class(tmp_path):
    head_path = _make_fixture_bundle(tmp_path)
    with patch("aegis.bridge.Embedder") as mock_embedder_cls:
        # Return a known vector that the LR head will classify deterministically.
        mock_embedder = MagicMock()
        mock_embedder.encode.return_value = np.ones(768, dtype=np.float32) / np.sqrt(768)
        mock_embedder_cls.return_value = mock_embedder
        from aegis.bridge import LocalBackend
        backend = LocalBackend(head_path=head_path)
        result = backend.classify("anything")
    pred = result["tool"]
    conf = result["confidence"]
    proba = backend._model.predict_proba(
        (np.ones(768, dtype=np.float32) / np.sqrt(768)).reshape(1, -1)
    )[0]
    expected_conf = float(proba[list(backend._model.classes_).index(pred)])
    assert abs(conf - expected_conf) < 1e-6
