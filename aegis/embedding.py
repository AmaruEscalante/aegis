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
        # Phase 3b prompt-sweep candidates.
        "none":            "",
        "classify_short":  "Classify: ",
        "classify_doc":    "Classify the following document: ",
        "classification":  "task: classification | query: ",   # original 3b attempt; underperformed at 28/30
        "retrieval":       "task: retrieval | query: ",
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
                f"Hint: run `uv sync` (project) or `npx aegis-gate` (end user)."
            ) from e

    @property
    def dim(self) -> int:
        return self._model.get_sentence_embedding_dimension()

    @property
    def device(self) -> str:
        """The torch device the underlying model is running on (e.g. 'cpu', 'mps', 'cuda:0')."""
        return str(self._model.device)

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
