"""Chunk storage behind a small interface: PostgreSQL + pgvector in production,
an in-memory implementation (real BM25 + brute-force cosine) for tests and offline demos."""

import math
import threading
from collections import Counter
from dataclasses import dataclass
from typing import Protocol

import numpy as np

from .chunker import Chunk
from .text import tokenize


@dataclass(frozen=True)
class Hit:
    chunk_id: int
    document: str
    heading: str
    text: str
    score: float


@dataclass(frozen=True)
class DocumentInfo:
    id: int
    name: str
    chunks: int


class Store(Protocol):
    name: str

    def add_document(self, name: str, chunks: list[Chunk], embeddings: np.ndarray) -> int:
        """Insert a document (replacing any existing document with the same name)."""

    def list_documents(self) -> list[DocumentInfo]: ...
    def count_chunks(self) -> int: ...
    def vector_search(self, query_vec: np.ndarray, k: int) -> list[Hit]:
        """Hits ordered by cosine similarity; `score` is the similarity."""

    def text_search(self, query: str, k: int) -> list[Hit]:
        """Hits ordered by lexical relevance; `score` is backend-specific."""


@dataclass
class _Row:
    id: int
    doc_id: int
    document: str
    chunk: Chunk
    tf: Counter
    length: int


class InMemoryStore:
    name = "memory"

    def __init__(self, k1: float = 1.2, b: float = 0.75) -> None:
        self.k1, self.b = k1, b
        self._lock = threading.Lock()
        self._docs: dict[int, str] = {}
        self._rows: list[_Row] = []
        self._vecs = np.zeros((0, 0), dtype=np.float32)
        self._next_doc = self._next_chunk = 1

    def add_document(self, name, chunks, embeddings):
        with self._lock:
            keep = [i for i, r in enumerate(self._rows) if r.document != name]
            self._rows = [self._rows[i] for i in keep]
            self._vecs = self._vecs[keep] if len(self._vecs) else embeddings[:0]
            self._docs = {i: n for i, n in self._docs.items() if n != name}
            doc_id, self._next_doc = self._next_doc, self._next_doc + 1
            self._docs[doc_id] = name
            for c in chunks:
                toks = tokenize(c.indexed_text)
                self._rows.append(_Row(self._next_chunk, doc_id, name, c, Counter(toks), len(toks)))
                self._next_chunk += 1
            self._vecs = np.vstack([self._vecs, embeddings]) if len(self._vecs) else embeddings
            return doc_id

    def list_documents(self):
        counts = Counter(r.doc_id for r in self._rows)
        return [DocumentInfo(i, n, counts[i]) for i, n in sorted(self._docs.items())]

    def count_chunks(self):
        return len(self._rows)

    def _hit(self, row: _Row, score: float) -> Hit:
        return Hit(row.id, row.document, row.chunk.heading, row.chunk.text, float(score))

    def vector_search(self, query_vec, k):
        if not self._rows:
            return []
        sims = self._vecs @ query_vec
        order = np.argsort(-sims)[:k]
        return [self._hit(self._rows[i], sims[i]) for i in order]

    def text_search(self, query, k):
        terms = set(tokenize(query))
        n = len(self._rows)
        if not terms or not n:
            return []
        avgdl = sum(r.length for r in self._rows) / n
        df = {t: sum(1 for r in self._rows if t in r.tf) for t in terms}
        scored = []
        for r in self._rows:
            s = 0.0
            for t in terms:
                f = r.tf.get(t, 0)
                if f:
                    idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                    s += idf * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * r.length / avgdl))
            if s > 0:
                scored.append((s, r))
        scored.sort(key=lambda x: -x[0])
        return [self._hit(r, s) for s, r in scored[:k]]


SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS documents (
    id         serial PRIMARY KEY,
    name       text NOT NULL UNIQUE,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS chunks (
    id          serial PRIMARY KEY,
    document_id int NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ordinal     int NOT NULL,
    heading     text NOT NULL,
    content     text NOT NULL,
    embedding   vector({dim}) NOT NULL,
    tsv         tsvector GENERATED ALWAYS AS (
                    setweight(to_tsvector('english', heading), 'A') ||
                    setweight(to_tsvector('english', content), 'B')) STORED
);
CREATE INDEX IF NOT EXISTS chunks_tsv_idx ON chunks USING gin (tsv);
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks USING hnsw (embedding vector_cosine_ops);
"""


class PgStore:
    """PostgreSQL store: pgvector HNSW for cosine search, a GIN-indexed tsvector for full text.

    Full-text ranking uses ts_rank: term frequency weighted by tsvector weight (heading=A,
    body=B), with no length normalization since chunks are already size-bounded. It is not
    BM25 (no IDF). ts_rank_cd (cover density) measured worse on the eval set (fulltext MRR@10
    0.741 vs 0.845) because it rewards all terms appearing close together, which suits AND
    queries, not the OR-of-terms queries built below.
    """

    name = "postgres"

    def __init__(self, url: str, dim: int = 384) -> None:
        import psycopg
        from pgvector.psycopg import register_vector

        # ponytail: one autocommit connection (psycopg serializes access across threads);
        # switch to psycopg_pool if concurrent request throughput matters.
        self.conn = psycopg.connect(url, autocommit=True)
        self.conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(self.conn)
        self.conn.execute(SCHEMA.format(dim=dim))

    def reset(self) -> None:
        self.conn.execute("TRUNCATE documents, chunks RESTART IDENTITY CASCADE")

    def add_document(self, name, chunks, embeddings):
        with self.conn.transaction():
            self.conn.execute("DELETE FROM documents WHERE name = %s", (name,))
            doc_id = self.conn.execute("INSERT INTO documents (name) VALUES (%s) RETURNING id", (name,)).fetchone()[0]
            with self.conn.cursor() as cur:
                cur.executemany(
                    "INSERT INTO chunks (document_id, ordinal, heading, content, embedding)"
                    " VALUES (%s, %s, %s, %s, %s)",
                    [(doc_id, c.ordinal, c.heading, c.text, e) for c, e in zip(chunks, embeddings, strict=True)],
                )
        return doc_id

    def list_documents(self):
        rows = self.conn.execute(
            "SELECT d.id, d.name, count(c.id) FROM documents d"
            " LEFT JOIN chunks c ON c.document_id = d.id GROUP BY d.id ORDER BY d.id"
        ).fetchall()
        return [DocumentInfo(*r) for r in rows]

    def count_chunks(self):
        return self.conn.execute("SELECT count(*) FROM chunks").fetchone()[0]

    def vector_search(self, query_vec, k):
        rows = self.conn.execute(
            "SELECT c.id, d.name, c.heading, c.content, 1 - (c.embedding <=> %s) AS sim"
            " FROM chunks c JOIN documents d ON d.id = c.document_id"
            " ORDER BY c.embedding <=> %s LIMIT %s",
            (query_vec, query_vec, k),
        ).fetchall()
        return [Hit(*r) for r in rows]

    def text_search(self, query, k):
        terms = tokenize(query)
        if not terms:
            return []
        # OR the terms together: websearch_to_tsquery ANDs them, which is far too strict for
        # natural-language questions. Each term goes through plainto_tsquery so punctuation
        # inside identifiers is handled by Postgres' own parser and stemming.
        rows = self.conn.execute(
            """
            WITH q AS (
                SELECT string_agg('(' || plainto_tsquery('english', t)::text || ')', ' | ')::tsquery AS q
                FROM unnest(%s::text[]) t
                WHERE plainto_tsquery('english', t)::text <> ''
            )
            SELECT c.id, d.name, c.heading, c.content, ts_rank(c.tsv, q.q) AS rank
            FROM chunks c JOIN documents d ON d.id = c.document_id, q
            WHERE c.tsv @@ q.q
            ORDER BY rank DESC
            LIMIT %s
            """,
            (terms, k),
        ).fetchall()
        return [Hit(*r) for r in rows]
