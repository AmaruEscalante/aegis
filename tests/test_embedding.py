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
    # encode_batch always passes a list; assert against the first (and only) element.
    assert isinstance(encoded_text, list)
    assert "retrieval" in encoded_text[0]


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


def test_encode_batch_returns_n_by_768_array():
    """Direct encode_batch call with multiple texts: verify shape (N, 768) and per-row norms."""
    with patch("aegis.embedding.SentenceTransformer") as mock_st_cls:
        mock_model = MagicMock()
        # Return 3 distinct un-normalized rows.
        mock_model.encode.return_value = np.array(
            [
                [3.0, 4.0] + [0.0] * 766,
                [1.0, 0.0] + [0.0] * 766,
                [0.0, 0.0] + [5.0] + [0.0] * 765,
            ],
            dtype=np.float32,
        )
        mock_st_cls.return_value = mock_model
        embedder = Embedder()
        arr = embedder.encode_batch(["foo", "bar", "baz"])
    assert arr.shape == (3, 768)
    assert arr.dtype == np.float32
    # Each row must be L2-normalized.
    norms = np.linalg.norm(arr, axis=1)
    for n in norms:
        assert abs(float(n) - 1.0) < 1e-5


def test_invalid_default_task_raises_valueerror():
    """Constructor rejects an unknown default_task."""
    with patch("aegis.embedding.SentenceTransformer") as mock_st_cls:
        mock_st_cls.return_value = _make_mock_st()
        with pytest.raises(ValueError, match="default_task"):
            Embedder(default_task="nonsense")


def test_invalid_task_kwarg_on_encode_raises_valueerror():
    """encode(text, task='...') rejects an unknown task."""
    with patch("aegis.embedding.SentenceTransformer") as mock_st_cls:
        mock_st_cls.return_value = _make_mock_st()
        embedder = Embedder()
        with pytest.raises(ValueError, match="task"):
            embedder.encode("hello", task="nonsense")


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


def test_none_task_uses_empty_prefix():
    """`task='none'` must apply no prefix — raw text only."""
    with patch("aegis.embedding.SentenceTransformer") as mock_st_cls:
        mock_model = _make_mock_st()
        mock_st_cls.return_value = mock_model
        embedder = Embedder()
        embedder.encode("hello world", task="none")
    encoded_arg = mock_model.encode.call_args[0][0]
    s = encoded_arg[0] if isinstance(encoded_arg, list) else encoded_arg
    # The prompt for "none" is empty, so the encoded text should be the
    # raw input (possibly truncated to MAX_INPUT_CHARS).
    assert s == "hello world"


def test_classify_short_task_uses_short_prefix():
    """`task='classify_short'` must apply 'Classify: ' prefix."""
    with patch("aegis.embedding.SentenceTransformer") as mock_st_cls:
        mock_model = _make_mock_st()
        mock_st_cls.return_value = mock_model
        embedder = Embedder()
        embedder.encode("hello world", task="classify_short")
    encoded_arg = mock_model.encode.call_args[0][0]
    s = encoded_arg[0] if isinstance(encoded_arg, list) else encoded_arg
    assert s == "Classify: hello world"


def test_classify_doc_task_uses_doc_prefix():
    """`task='classify_doc'` must apply Google's docs-style prefix."""
    with patch("aegis.embedding.SentenceTransformer") as mock_st_cls:
        mock_model = _make_mock_st()
        mock_st_cls.return_value = mock_model
        embedder = Embedder()
        embedder.encode("hello world", task="classify_doc")
    encoded_arg = mock_model.encode.call_args[0][0]
    s = encoded_arg[0] if isinstance(encoded_arg, list) else encoded_arg
    assert s == "Classify the following document: hello world"


def test_all_sweep_tasks_are_supported():
    """The 5 sweep candidates must all be in DEFAULT_PROMPTS."""
    expected = {"none", "classify_short", "classify_doc", "classification", "retrieval"}
    assert expected.issubset(set(Embedder.DEFAULT_PROMPTS))
