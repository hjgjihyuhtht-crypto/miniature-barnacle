"""Embedding tests."""

import pytest

from backend.memory.embeddings import HashEmbeddingProvider, cosine


@pytest.mark.asyncio
async def test_hash_embeddings_similarity():
    p = HashEmbeddingProvider(dim=128)
    a = await p.embed("projeto nexus ai fastapi")
    b = await p.embed("projeto nexus ai fastapi")
    c = await p.embed("receita de bolo de chocolate")
    assert cosine(a, b) > 0.99
    assert cosine(a, c) < cosine(a, b)
