"""Hybrid retrieval: full-text + vector candidates fused with Reciprocal Rank Fusion,
optionally re-scored by a local cross-encoder."""

from collections import defaultdict
from dataclasses import dataclass, replace
from typing import Literal

from .embeddings import Embedder
from .store import Hit, Store

Mode = Literal["vector", "fulltext", "hybrid"]
MODES: tuple[Mode, ...] = ("vector", "fulltext", "hybrid")


def reciprocal_rank_fusion(rankings: list[list[Hit]], k: int = 60) -> list[Hit]:
    """score(d) = sum over rankings of 1 / (k + rank(d)), ranks starting at 1.

    RRF only looks at ranks, so it fuses scores on incomparable scales (cosine vs ts_rank)
    without any normalization. k=60 is the constant from Cormack et al. (2009).
    """
    scores: dict[int, float] = defaultdict(float)
    first: dict[int, Hit] = {}
    for ranking in rankings:
        for rank, hit in enumerate(ranking, start=1):
            scores[hit.chunk_id] += 1.0 / (k + rank)
            first.setdefault(hit.chunk_id, hit)
    ordered = sorted(scores.items(), key=lambda kv: -kv[1])
    return [replace(first[cid], score=s) for cid, s in ordered]


class CrossEncoderReranker:
    def __init__(self, model: str = "Xenova/ms-marco-MiniLM-L-6-v2") -> None:
        from fastembed.rerank.cross_encoder import TextCrossEncoder

        self.model = TextCrossEncoder(model)

    def rerank(self, query: str, hits: list[Hit]) -> list[Hit]:
        scores = list(self.model.rerank(query, [f"{h.heading}\n{h.text}" for h in hits]))
        return [replace(h, score=float(s)) for s, h in sorted(zip(scores, hits, strict=True), key=lambda x: -x[0])]


@dataclass(frozen=True)
class Retrieval:
    hits: list[Hit]
    confidence: float  # best cosine similarity between the query and any chunk


class Retriever:
    def __init__(self, store: Store, embedder: Embedder, reranker: CrossEncoderReranker | None = None):
        self.store = store
        self.embedder = embedder
        self.reranker = reranker

    def retrieve(self, query: str, k: int = 5, mode: Mode = "hybrid", rerank: bool = False) -> Retrieval:
        pool = max(4 * k, 20)
        vector_hits = self.store.vector_search(self.embedder.embed_query(query), pool)
        confidence = vector_hits[0].score if vector_hits else 0.0
        if mode == "vector":
            hits = vector_hits
        elif mode == "fulltext":
            hits = self.store.text_search(query, pool)
        elif mode == "hybrid":
            hits = reciprocal_rank_fusion([vector_hits, self.store.text_search(query, pool)])
        else:
            raise ValueError(f"unknown mode {mode!r}")
        if rerank:
            if self.reranker is None:
                raise ValueError("reranking requested but no reranker is configured")
            hits = self.reranker.rerank(query, hits[:pool])
        return Retrieval(hits[:k], confidence)
