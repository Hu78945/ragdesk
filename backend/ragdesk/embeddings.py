"""Embedders. `fastembed` runs BAAI/bge-small-en-v1.5 locally via ONNX (no API key);
`hash` is a deterministic, dependency-free fallback used by tests and fully-offline runs."""

import hashlib
from itertools import pairwise
from typing import Protocol

import numpy as np

from .text import tokenize

DIM = 384


class Embedder(Protocol):
    name: str
    dim: int

    def embed_documents(self, texts: list[str]) -> np.ndarray: ...
    def embed_query(self, text: str) -> np.ndarray: ...


def _normalize(m: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(m, axis=-1, keepdims=True)
    return (m / np.where(norms == 0, 1, norms)).astype(np.float32)


class HashEmbedder:
    """Feature hashing of unigrams + bigrams into a signed 384-d vector.

    Captures lexical overlap only (no synonyms), so it is a weak semantic retriever —
    but it is deterministic, instant, and needs no model download.
    """

    name = "hash"
    dim = DIM

    def _vec(self, text: str) -> np.ndarray:
        v = np.zeros(self.dim, dtype=np.float32)
        toks = tokenize(text)
        for feat in toks + [f"{a} {b}" for a, b in pairwise(toks)]:
            h = int.from_bytes(hashlib.blake2b(feat.encode(), digest_size=8).digest(), "little")
            v[h % self.dim] += 1.0 if (h >> 63) & 1 else -1.0
        return v

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return _normalize(np.stack([self._vec(t) for t in texts]))

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed_documents([text])[0]


class FastEmbedder:
    name = "fastembed"
    dim = DIM

    def __init__(self, model: str = "BAAI/bge-small-en-v1.5") -> None:
        from fastembed import TextEmbedding

        self.model = TextEmbedding(model)

    def embed_documents(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dim), dtype=np.float32)
        return _normalize(np.stack(list(self.model.passage_embed(texts))))

    def embed_query(self, text: str) -> np.ndarray:
        return _normalize(next(iter(self.model.query_embed(text))))


def get_embedder(name: str) -> Embedder:
    if name == "hash":
        return HashEmbedder()
    if name == "fastembed":
        return FastEmbedder()
    raise ValueError(f"unknown embedder {name!r} (expected 'fastembed' or 'hash')")
