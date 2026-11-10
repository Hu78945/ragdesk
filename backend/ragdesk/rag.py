"""Wires store + embedder + retriever + answerer into ingest / ask operations."""

from collections.abc import Iterator
from dataclasses import asdict
from pathlib import Path

from .answer import REFUSAL, Answerer, ClaudeAnswerer, ExtractiveAnswerer
from .chunker import SUPPORTED_EXTENSIONS, chunk_document
from .config import Settings
from .embeddings import Embedder, get_embedder
from .retrieval import CrossEncoderReranker, Mode, Retriever
from .store import InMemoryStore, PgStore, Store


class RAG:
    def __init__(
        self,
        store: Store,
        embedder: Embedder,
        answerer: Answerer,
        settings: Settings,
        reranker: CrossEncoderReranker | None = None,
    ) -> None:
        self.store = store
        self.embedder = embedder
        self.answerer = answerer
        self.settings = settings
        self.retriever = Retriever(store, embedder, reranker)

    @classmethod
    def from_settings(cls, settings: Settings) -> "RAG":
        embedder = get_embedder(settings.embedder)
        store = PgStore(settings.database_url, embedder.dim) if settings.database_url else InMemoryStore()
        answerer = (
            ClaudeAnswerer(settings.anthropic_api_key, settings.anthropic_model)
            if settings.anthropic_api_key
            else ExtractiveAnswerer()
        )
        reranker = CrossEncoderReranker() if settings.rerank else None
        return cls(store, embedder, answerer, settings, reranker)

    def ingest(self, filename: str, data: bytes) -> dict:
        chunks = chunk_document(filename, data)
        if not chunks:
            raise ValueError(f"no extractable text in {filename}")
        embeddings = self.embedder.embed_documents([c.indexed_text for c in chunks])
        doc_id = self.store.add_document(filename, chunks, embeddings)
        return {"id": doc_id, "name": filename, "chunks": len(chunks)}

    def ingest_dir(self, directory: Path) -> list[dict]:
        return [
            self.ingest(p.name, p.read_bytes())
            for p in sorted(directory.iterdir())
            if p.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

    def ask(self, question: str, k: int | None = None, mode: Mode = "hybrid") -> Iterator[tuple[str, dict]]:
        """Yields SSE-ready (event, payload) pairs: sources, token*, done."""
        result = self.retriever.retrieve(question, k or self.settings.top_k, mode, self.settings.rerank)
        refused = not result.hits or result.confidence < self.settings.similarity_floor
        hits = [] if refused else result.hits
        yield "sources", {"sources": [{"n": n, **asdict(h)} for n, h in enumerate(hits, start=1)]}
        if refused:
            yield "token", {"text": REFUSAL}
        else:
            text = ""
            for delta in self.answerer.stream(question, hits):
                text += delta
                yield "token", {"text": delta}
            refused = text.strip().startswith("I don't know")
        yield (
            "done",
            {
                "refused": refused,
                "answerer": self.answerer.name,
                "confidence": round(result.confidence, 4),
            },
        )
