import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent

# Cosine-similarity floor below which we answer "I don't know". The two embedders
# live on different scales, so each gets its own default. The gate only filters clearly
# off-topic questions; finer "is this actually answered?" judgement is left to the LLM.
DEFAULT_MIN_SIMILARITY = {"fastembed": 0.65, "hash": 0.10}


def _env(name: str, default: str) -> str:
    return os.environ.get(name) or default


@dataclass(frozen=True)
class Settings:
    database_url: str | None = field(default_factory=lambda: os.environ.get("DATABASE_URL") or None)
    embedder: str = field(default_factory=lambda: _env("EMBEDDER", "fastembed"))
    anthropic_api_key: str | None = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY") or None)
    anthropic_model: str = field(default_factory=lambda: _env("ANTHROPIC_MODEL", "claude-haiku-5-5"))
    top_k: int = field(default_factory=lambda: int(_env("TOP_K", "5")))
    rerank: bool = field(default_factory=lambda: _env("RERANK", "0") == "1")
    min_similarity: float | None = field(
        default_factory=lambda: float(v) if (v := os.environ.get("MIN_SIMILARITY")) else None
    )
    seed_corpus: bool = field(default_factory=lambda: _env("SEED_CORPUS", "1") == "1")
    corpus_dir: Path = field(default_factory=lambda: Path(_env("CORPUS_DIR", str(BACKEND_DIR / "corpus"))))
    eval_results: Path = field(
        default_factory=lambda: Path(_env("EVAL_RESULTS", str(BACKEND_DIR / "eval" / "results.json")))
    )
    cors_origins: list[str] = field(default_factory=lambda: _env("CORS_ORIGINS", "http://localhost:3000").split(","))

    @property
    def similarity_floor(self) -> float:
        if self.min_similarity is not None:
            return self.min_similarity
        return DEFAULT_MIN_SIMILARITY.get(self.embedder, 0.0)
