FROM python:3.12-slim

RUN pip install --no-cache-dir uv
WORKDIR /app

# 1) Install dependencies only — cached unless pyproject.toml / uv.lock change.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2) Install the project itself (needs src/ + README.md present).
COPY . .
RUN uv sync --frozen --no-dev

ENTRYPOINT ["uv", "run", "verasig"]
