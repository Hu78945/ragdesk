import json
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .config import Settings
from .rag import RAG
from .retrieval import Mode

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
log = logging.getLogger("ragdesk")


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    k: int | None = Field(default=None, ge=1, le=20)
    mode: Mode = "hybrid"


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    k: int = Field(default=5, ge=1, le=50)
    mode: Mode = "hybrid"
    rerank: bool = False


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def create_app(rag: RAG | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or (rag.settings if rag else Settings())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.rag = rag or RAG.from_settings(settings)
        if settings.seed_corpus and app.state.rag.store.count_chunks() == 0:
            docs = app.state.rag.ingest_dir(settings.corpus_dir)
            log.info("seeded %d documents from %s", len(docs), settings.corpus_dir)
        yield

    app = FastAPI(title="ragdesk", lifespan=lifespan)
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_methods=["*"], allow_headers=["*"])

    @app.get("/api/health")
    def health():
        r: RAG = app.state.rag
        return {
            "status": "ok",
            "store": r.store.name,
            "embedder": r.embedder.name,
            "answerer": r.answerer.name,
            "rerank": settings.rerank,
            "chunks": r.store.count_chunks(),
        }

    @app.get("/api/documents")
    def list_documents():
        return [asdict(d) for d in app.state.rag.store.list_documents()]

    @app.post("/api/documents", status_code=201)
    async def upload(files: list[UploadFile]):
        results = []
        for f in files:
            data = await f.read(MAX_UPLOAD_BYTES + 1)
            if len(data) > MAX_UPLOAD_BYTES:
                raise HTTPException(413, f"{f.filename} exceeds {MAX_UPLOAD_BYTES // 2**20} MB")
            try:
                results.append(app.state.rag.ingest(f.filename or "upload", data))
            except ValueError as e:
                raise HTTPException(400, str(e)) from e
        return results

    @app.post("/api/search")
    def search(req: SearchRequest):
        try:
            result = app.state.rag.retriever.retrieve(req.query, req.k, req.mode, req.rerank)
        except ValueError as e:
            raise HTTPException(400, str(e)) from e
        return {"confidence": result.confidence, "hits": [asdict(h) for h in result.hits]}

    @app.post("/api/ask")
    def ask(req: AskRequest):
        def events():
            try:
                for event, data in app.state.rag.ask(req.question, req.k, req.mode):
                    yield _sse(event, data)
            except Exception:  # surface failures to the client instead of a silently cut stream
                log.exception("ask failed")
                yield _sse("error", {"message": "answer generation failed"})

        return StreamingResponse(
            events(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/api/evals/latest")
    def latest_eval():
        if not settings.eval_results.exists():
            raise HTTPException(404, "no eval results yet; run `uv run python -m eval.run_eval`")
        return json.loads(settings.eval_results.read_text())

    return app


app = create_app()
