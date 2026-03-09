ARG QUARTO_VERSION=1.6.40

# ── uv binary ────────────────────────────────────────────────────────────────
FROM ghcr.io/astral-sh/uv:latest AS uv-bin

# ── final image ──────────────────────────────────────────────────────────────
FROM python:3.12-slim

ARG QUARTO_VERSION

# System dependencies (Quarto needs curl/wget + gdebi/dpkg; also needs libglib for deno)
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget \
        ca-certificates \
        libglib2.0-0 \
    && wget -q "https://github.com/quarto-dev/quarto-cli/releases/download/v${QUARTO_VERSION}/quarto-${QUARTO_VERSION}-linux-amd64.deb" \
    && dpkg -i "quarto-${QUARTO_VERSION}-linux-amd64.deb" \
    && rm "quarto-${QUARTO_VERSION}-linux-amd64.deb" \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy uv
COPY --from=uv-bin /uv /usr/local/bin/uv

WORKDIR /app

# Install Python dependencies (cached layer — only invalidated if lock file changes)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copy application source and Quarto sources
COPY python/ python/
COPY quarto/ quarto/

# Entrypoint script
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

ENV PYTHONPATH=/app/python/src
ENV DOMAIN=http://localhost:8000
ENV PORT=8000

EXPOSE 8000

CMD ["./entrypoint.sh"]
