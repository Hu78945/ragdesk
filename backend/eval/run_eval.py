"""Retrieval + refusal evaluation over the bundled corpus, with an optional LLM-as-judge
faithfulness check (only when ANTHROPIC_API_KEY is set and --judge is passed).

    uv run python -m eval.run_eval                       # in-memory store
    uv run python -m eval.run_eval --database-url URL    # Postgres + pgvector (TRUNCATES its tables)
"""

import argparse
import json
import os
import statistics
import time
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from ragdesk.answer import ExtractiveAnswerer
from ragdesk.config import Settings
from ragdesk.embeddings import get_embedder
from ragdesk.rag import RAG
from ragdesk.retrieval import CrossEncoderReranker
from ragdesk.store import Hit, InMemoryStore, PgStore

from .golden import GOLDEN

K = 10


def is_relevant(hit: Hit, relevant: list[dict]) -> bool:
    return any(hit.document == r["doc"] and r["contains"].lower() in hit.text.lower() for r in relevant)


def first_relevant_rank(hits: list[Hit], relevant: list[dict]) -> int | None:
    return next((i for i, h in enumerate(hits, start=1) if is_relevant(h, relevant)), None)


def retrieval_metrics(rag: RAG, mode: str, rerank: bool) -> tuple[dict, list[int | None]]:
    ranks, latencies = [], []
    for item in (g for g in GOLDEN if g["relevant"]):
        t0 = time.perf_counter()
        hits = rag.retriever.retrieve(item["q"], K, mode, rerank).hits
        latencies.append((time.perf_counter() - t0) * 1000)
        ranks.append(first_relevant_rank(hits, item["relevant"]))
    n = len(ranks)
    row = {"mode": mode + ("+rerank" if rerank else "")}
    for k in (1, 3, 5):
        row[f"recall@{k}"] = round(sum(1 for r in ranks if r and r <= k) / n, 3)
    row[f"mrr@{K}"] = round(sum(1 / r for r in ranks if r) / n, 3)
    row["latency_ms_p50"] = round(statistics.median(latencies), 1)
    return row, ranks


def refusal_metrics(rag: RAG, floor: float) -> dict:
    conf = [(rag.retriever.retrieve(g["q"], 1, "vector").confidence, bool(g["relevant"])) for g in GOLDEN]
    in_scope = [c for c, ok in conf if ok]
    out_scope = [c for c, ok in conf if not ok]

    def at(t: float) -> dict:
        answered = sum(c >= t for c in in_scope) / len(in_scope)
        refused = sum(c < t for c in out_scope) / len(out_scope)
        return {
            "threshold": round(t, 3),
            "in_scope_answered": round(answered, 3),
            "out_of_scope_refused": round(refused, 3),
        }

    best = max((at(t / 100) for t in range(101)), key=lambda m: m["in_scope_answered"] + m["out_of_scope_refused"])
    return {
        "configured": at(floor),
        "best_threshold_on_this_set": best,
        "in_scope_confidence": [round(min(in_scope), 3), round(max(in_scope), 3)],
        "out_of_scope_confidence": [round(min(out_scope), 3), round(max(out_scope), 3)],
    }


def answer_metrics(rag: RAG, rerank: bool) -> dict:
    """Offline answer check: does the extractive answer quote the gold evidence?"""
    hits_found = 0
    in_scope = [g for g in GOLDEN if g["relevant"]]
    for item in in_scope:
        hits = rag.retriever.retrieve(item["q"], rag.settings.top_k, "hybrid", rerank).hits
        answer = "".join(ExtractiveAnswerer().stream(item["q"], hits)).lower()
        hits_found += any(r["contains"].lower() in answer for r in item["relevant"])
    return {
        "answerer": "extractive",
        "retrieval": "hybrid" + ("+rerank" if rerank else ""),
        "evidence_in_answer": round(hits_found / len(in_scope), 3),
    }


JUDGE_PROMPT = """You are grading a retrieval-augmented answer for faithfulness.

<sources>
{sources}
</sources>

<question>{question}</question>
<answer>{answer}</answer>

Is every factual claim in the answer supported by the sources? Citations like [2] refer to source ids.
An answer that says it doesn't know is faithful."""

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "faithful": {"type": "boolean"},
        "unsupported_claims": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["faithful", "unsupported_claims"],
    "additionalProperties": False,
}


def judge_faithfulness(rag: RAG, settings: Settings) -> dict:
    import anthropic

    from ragdesk.answer import ClaudeAnswerer, format_sources

    answerer = ClaudeAnswerer(settings.anthropic_api_key, settings.anthropic_model)
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    judge_model = os.environ.get("JUDGE_MODEL", "claude-opus-5-5")
    verdicts = []
    for item in (g for g in GOLDEN if g["relevant"]):
        hits = rag.retriever.retrieve(item["q"], settings.top_k).hits
        answer = "".join(answerer.stream(item["q"], hits))
        resp = client.beta.messages.create(
            model=judge_model,
            max_tokens=4096,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"format": {"type": "json_schema", "schema": JUDGE_SCHEMA}},
            messages=[
                {
                    "role": "user",
                    "content": JUDGE_PROMPT.format(sources=format_sources(hits), question=item["q"], answer=answer),
                }
            ],
        )
        if resp.stop_reason == "refusal":
            continue
        text = next(b.text for b in resp.content if b.type == "text")
        verdicts.append({"q": item["q"], "answer": answer, **json.loads(text)})
    return {
        "answer_model": settings.anthropic_model,
        "judge_model": judge_model,
        "judged": len(verdicts),
        "faithful_rate": round(sum(v["faithful"] for v in verdicts) / max(len(verdicts), 1), 3),
        "unfaithful": [v for v in verdicts if not v["faithful"]],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--embedder", default=os.environ.get("EMBEDDER", "fastembed"))
    p.add_argument("--database-url", help="Postgres URL to evaluate against; its tables are TRUNCATED")
    p.add_argument("--rerank", action="store_true", help="also evaluate hybrid + cross-encoder rerank")
    p.add_argument("--judge", action="store_true", help="LLM-as-judge faithfulness (needs ANTHROPIC_API_KEY)")
    p.add_argument("--out", type=Path, default=Path(__file__).parent / "results.json")
    args = p.parse_args()

    settings = replace(Settings(), embedder=args.embedder, database_url=args.database_url)
    embedder = get_embedder(args.embedder)
    if args.database_url:
        store = PgStore(args.database_url, embedder.dim)
        store.reset()
    else:
        store = InMemoryStore()
    reranker = CrossEncoderReranker() if args.rerank else None
    rag = RAG(store, embedder, ExtractiveAnswerer(), settings, reranker)
    docs = rag.ingest_dir(settings.corpus_dir)

    configs = [("vector", False), ("fulltext", False), ("hybrid", False)]
    if args.rerank:
        configs.append(("hybrid", True))
    rows, per_mode_ranks = [], {}
    for mode, rerank in configs:
        row, ranks = retrieval_metrics(rag, mode, rerank)
        rows.append(row)
        per_mode_ranks[row["mode"]] = ranks

    answerable = [g for g in GOLDEN if g["relevant"]]
    results = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "store": store.name,
        "embedder": embedder.name,
        "corpus": {"documents": len(docs), "chunks": store.count_chunks()},
        "questions": {"in_scope": len(answerable), "out_of_scope": len(GOLDEN) - len(answerable)},
        "k": K,
        "retrieval": rows,
        "refusal": refusal_metrics(rag, settings.similarity_floor),
        "extractive_answers": answer_metrics(rag, args.rerank),
        "faithfulness": None,
        "per_question": [
            {"q": g["q"], "ranks": {m: r[i] for m, r in per_mode_ranks.items()}} for i, g in enumerate(answerable)
        ],
    }
    if args.judge:
        if not settings.anthropic_api_key:
            raise SystemExit("--judge needs ANTHROPIC_API_KEY")
        results["faithfulness"] = judge_faithfulness(rag, settings)

    args.out.write_text(json.dumps(results, indent=2) + "\n")
    print(f"{store.name} / {embedder.name}: {results['corpus']}")
    for row in rows:
        print("  ".join(f"{k}={v}" for k, v in row.items()))
    print("refusal:", json.dumps(results["refusal"]))
    print("extractive answers:", json.dumps(results["extractive_answers"]))
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
