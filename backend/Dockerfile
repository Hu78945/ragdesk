FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never \
    FASTEMBED_CACHE_PATH=/models PATH="/app/.venv/bin:$PATH"

COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --frozen --no-dev --no-install-project

# Bake the embedding + reranking models into the image so containers start offline.
RUN python -c "from fastembed import TextEmbedding; from fastembed.rerank.cross_encoder import TextCrossEncoder; \
TextEmbedding('BAAI/bge-small-en-v1.5'); TextCrossEncoder('Xenova/ms-marco-MiniLM-L-6-v2')"

COPY ragdesk ragdesk
COPY corpus corpus
COPY eval eval

EXPOSE 8000
CMD ["uvicorn", "ragdesk.api:app", "--host", "0.0.0.0", "--port", "8000"]
