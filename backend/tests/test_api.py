import json

import pytest
from fastapi.testclient import TestClient

from ragdesk.api import create_app

from .conftest import make_pdf


@pytest.fixture
def client(rag):
    with TestClient(create_app(rag)) as c:
        yield c


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["store"] == "memory" and body["answerer"] == "extractive"
    assert body["chunks"] > 0


def test_upload_and_list_documents(client):
    files = [
        ("files", ("notes.md", b"# Notes\nThe flux capacitor needs 1.21 gigawatts.", "text/markdown")),
        ("files", ("manual.pdf", make_pdf("Warp drive requires dilithium"), "application/pdf")),
    ]
    resp = client.post("/api/documents", files=files)
    assert resp.status_code == 201
    assert [d["name"] for d in resp.json()] == ["notes.md", "manual.pdf"]
    names = {d["name"] for d in client.get("/api/documents").json()}
    assert {"notes.md", "manual.pdf", "retries.md"} <= names

    hits = client.post("/api/search", json={"query": "gigawatts flux capacitor", "k": 1}).json()["hits"]
    assert hits[0]["document"] == "notes.md"


def test_upload_rejects_unsupported_and_empty_files(client):
    assert client.post("/api/documents", files=[("files", ("x.png", b"\x89PNG", "image/png"))]).status_code == 400
    assert client.post("/api/documents", files=[("files", ("empty.md", b"   ", "text/markdown"))]).status_code == 400


def test_search_validates_mode(client):
    assert client.post("/api/search", json={"query": "x", "mode": "magic"}).status_code == 422


def test_ask_streams_sources_tokens_and_done(client):
    resp = client.post("/api/ask", json={"question": "How long are dead-lettered runs kept?"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(resp.text)
    kinds = [e for e, _ in events]
    assert kinds[0] == "sources" and kinds[-1] == "done" and "token" in kinds
    sources = events[0][1]["sources"]
    assert [s["n"] for s in sources] == list(range(1, len(sources) + 1))
    answer = "".join(d["text"] for e, d in events if e == "token")
    assert "14 days" in answer and "[" in answer
    assert events[-1][1]["refused"] is False


def test_ask_refuses_off_topic_questions(client):
    events = parse_sse(client.post("/api/ask", json={"question": "What is the capital of Australia?"}).text)
    assert events[0][1]["sources"] == []
    assert events[-1][1]["refused"] is True
    assert "I don't know" in "".join(d["text"] for e, d in events if e == "token")


def test_ask_reports_answerer_failure_as_sse_error(client, rag, monkeypatch):
    def boom(*_):
        raise RuntimeError("upstream down")
        yield  # pragma: no cover

    monkeypatch.setattr(rag.answerer, "stream", boom)
    events = parse_sse(client.post("/api/ask", json={"question": "How often do workers heartbeat?"}).text)
    assert events[-1][0] == "error"


def test_ask_validates_question(client):
    assert client.post("/api/ask", json={"question": ""}).status_code == 422


def test_latest_eval(client, settings):
    assert client.get("/api/evals/latest").status_code == 404
    settings.eval_results.write_text(json.dumps({"retrieval": []}))
    assert client.get("/api/evals/latest").json() == {"retrieval": []}
