import numpy as np
import pytest

from ragdesk.chunker import Chunk
from ragdesk.embeddings import HashEmbedder
from ragdesk.retrieval import Retriever, reciprocal_rank_fusion
from ragdesk.store import Hit


def hit(i: int) -> Hit:
    return Hit(i, "d", "", f"chunk {i}", 0.0)


def test_rrf_scores_match_formula():
    fused = reciprocal_rank_fusion([[hit(1), hit(2)], [hit(2), hit(3)]], k=60)
    scores = {h.chunk_id: h.score for h in fused}
    assert scores[2] == pytest.approx(1 / 62 + 1 / 61)
    assert scores[1] == pytest.approx(1 / 61)
    assert scores[3] == pytest.approx(1 / 62)
    assert [h.chunk_id for h in fused] == [2, 1, 3]


def test_rrf_rewards_agreement_over_a_single_top_rank():
    # 7 is first in one list only; 9 is second in both -> 9 wins.
    fused = reciprocal_rank_fusion([[hit(7), hit(9)], [hit(8), hit(9)]])
    assert fused[0].chunk_id == 9


def test_rrf_handles_empty_rankings():
    assert reciprocal_rank_fusion([[], []]) == []
    assert [h.chunk_id for h in reciprocal_rank_fusion([[hit(1)], []])] == [1]


def _load(store, texts: dict[str, str]):
    emb = HashEmbedder()
    for name, text in texts.items():
        chunk = Chunk(0, name, text)
        store.add_document(name, [chunk], emb.embed_documents([chunk.indexed_text]))
    return emb


DOCS = {
    "retries.md": "Exponential backoff doubles the delay after each failed attempt.",
    "tls.md": "TLS 1.2 is the minimum protocol version accepted by the API server.",
    "metrics.md": "Prometheus metrics include kestrel_queue_depth and run durations.",
}


def test_store_text_search_ranks_exact_terms_first(store):
    _load(store, DOCS)
    hits = store.text_search("which metric is kestrel_queue_depth", 3)
    assert hits[0].document == "metrics.md"


def test_store_vector_search_returns_cosine_similarity(store):
    emb = _load(store, DOCS)
    hits = store.vector_search(emb.embed_query(f"tls.md\n{DOCS['tls.md']}"), 3)
    assert hits[0].document == "tls.md"
    assert hits[0].score == pytest.approx(1.0, abs=1e-4)
    assert hits[0].score >= hits[1].score >= hits[2].score


def test_store_replaces_document_with_same_name(store):
    emb = _load(store, DOCS)
    store.add_document("tls.md", [Chunk(0, "tls.md", "new text")], emb.embed_documents(["new text"]))
    docs = {d.name: d.chunks for d in store.list_documents()}
    assert docs == {"retries.md": 1, "tls.md": 1, "metrics.md": 1}
    assert store.count_chunks() == 3


def test_store_text_search_with_only_stopwords_is_empty(store):
    _load(store, DOCS)
    assert store.text_search("what is the", 5) == []


def test_hybrid_retrieval_on_bundled_corpus(rag):
    result = rag.retriever.retrieve("What does error KST-2003 indicate?", k=3)
    assert result.hits[0].document == "api.html"
    assert "KST-2003" in result.hits[0].text


@pytest.mark.parametrize("mode", ["vector", "fulltext", "hybrid"])
def test_every_mode_returns_k_hits(rag, mode):
    result = rag.retriever.retrieve("how do retries back off", k=4, mode=mode)
    assert len(result.hits) == 4
    assert 0 < result.confidence <= 1


def test_rerank_without_reranker_is_an_error(rag):
    with pytest.raises(ValueError, match="reranker"):
        rag.retriever.retrieve("anything", rerank=True)


def test_empty_store_returns_nothing():
    from ragdesk.store import InMemoryStore

    result = Retriever(InMemoryStore(), HashEmbedder()).retrieve("hello")
    assert result.hits == [] and result.confidence == 0.0


def test_hash_embedder_is_deterministic_and_normalized():
    a, b = HashEmbedder().embed_documents(["same text", "same text"])
    assert np.array_equal(a, b)
    assert np.linalg.norm(a) == pytest.approx(1.0)
