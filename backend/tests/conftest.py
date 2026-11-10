import os
from dataclasses import replace

import pytest

from ragdesk.answer import ExtractiveAnswerer
from ragdesk.config import Settings
from ragdesk.embeddings import HashEmbedder
from ragdesk.rag import RAG
from ragdesk.store import InMemoryStore, PgStore


def make_pdf(text: str) -> bytes:
    """Smallest valid single-page PDF with one line of Helvetica text."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >>>>>>",
        b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n%s\nendobj\n" % (i, obj)
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, xref)
    return bytes(out)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return replace(
        Settings(),
        embedder="hash",
        database_url=None,
        anthropic_api_key=None,
        rerank=False,
        min_similarity=None,
        eval_results=tmp_path / "results.json",
    )


@pytest.fixture
def rag(settings) -> RAG:
    r = RAG(InMemoryStore(), HashEmbedder(), ExtractiveAnswerer(), settings)
    r.ingest_dir(settings.corpus_dir)
    return r


def _pg_url() -> str | None:
    if url := os.environ.get("RAGDESK_TEST_DATABASE_URL"):
        return url
    try:
        import pgserver  # bundled Postgres + pgvector, so this runs without Docker
    except ImportError:
        return None
    return pgserver.get_server(os.path.join(os.path.dirname(__file__), "..", ".pgdata"), cleanup_mode="stop").get_uri()


@pytest.fixture(params=["memory", "postgres"])
def store(request):
    if request.param == "memory":
        yield InMemoryStore()
        return
    url = _pg_url()
    if not url:
        pytest.skip("no Postgres available (set RAGDESK_TEST_DATABASE_URL or install pgserver)")
    s = PgStore(url, HashEmbedder.dim)
    s.reset()
    yield s
    s.reset()
    s.conn.close()
