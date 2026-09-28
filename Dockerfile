FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY src ./src

RUN uv sync --frozen --no-dev --no-install-project \
    && uv sync --frozen --no-dev

ENV GOPROPLUS_DATA_DIR=/data

ENTRYPOINT ["uv", "run", "--no-sync", "gpp"]
CMD ["sync"]
