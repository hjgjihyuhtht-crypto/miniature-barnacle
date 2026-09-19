"""Embedding providers for memory retrieval."""

from __future__ import annotations

import abc
import asyncio
import hashlib
import logging
import struct
from typing import Any, Optional

import math

from backend.config import Settings, get_settings

logger = logging.getLogger("nexus.embeddings")


class EmbeddingProvider(abc.ABC):
    @abc.abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    @abc.abstractmethod
    async def health(self) -> dict[str, Any]: ...


class HashEmbeddingProvider(EmbeddingProvider):
    """Deterministic local fallback embeddings (no external deps)."""

    def __init__(self, dim: int = 256):
        self.dim = dim

    async def embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = text.lower().split()
        if not tokens:
            return vec
        for tok in tokens:
            digest = hashlib.sha256(tok.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    async def health(self) -> dict[str, Any]:
        return {"status": "ok", "provider": "hash", "dim": self.dim}


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None

    async def _ensure(self) -> None:
        if self._model is not None:
            return

        def _load() -> None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)

        await asyncio.to_thread(_load)

    async def embed(self, text: str) -> list[float]:
        await self._ensure()

        def _run() -> list[float]:
            assert self._model is not None
            vec = self._model.encode(text, normalize_embeddings=True)
            return [float(x) for x in vec]

        return await asyncio.to_thread(_run)

    async def health(self) -> dict[str, Any]:
        try:
            import sentence_transformers  # noqa: F401

            return {"status": "ok", "provider": "sentence_transformers", "model": self.model_name}
        except Exception:
            return {"status": "offline", "provider": "sentence_transformers"}


def pack_embedding(vec: list[float]) -> bytes:
    return struct.pack(f"{len(vec)}f", *vec)


def unpack_embedding(blob: bytes) -> list[float]:
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def cosine(a: list[float], b: list[float]) -> float:
    n = min(len(a), len(b))
    if n == 0:
        return 0.0
    dot = sum(a[i] * b[i] for i in range(n))
    na = math.sqrt(sum(a[i] * a[i] for i in range(n))) or 1.0
    nb = math.sqrt(sum(b[i] * b[i] for i in range(n))) or 1.0
    return dot / (na * nb)


def create_embedding_provider(settings: Optional[Settings] = None) -> EmbeddingProvider:
    settings = settings or get_settings()
    if settings.embedding_provider == "none":
        return HashEmbeddingProvider()
    try:
        import sentence_transformers  # noqa: F401

        return SentenceTransformerProvider(settings.embedding_model)
    except Exception:
        logger.info("sentence-transformers unavailable; using hash embeddings")
        return HashEmbeddingProvider()
