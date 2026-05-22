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
