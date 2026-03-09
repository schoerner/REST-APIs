#!/bin/bash
set -e

DOMAIN=${DOMAIN:-http://localhost:8000}
# Derive bare hostname (no protocol, no port) for use in HTTP Host: headers
DOMAIN_HOST=$(echo "$DOMAIN" | sed 's|^https\?://||' | cut -d: -f1 | cut -d/ -f1)

echo "==> Domain: ${DOMAIN}"
echo "==> Domain host: ${DOMAIN_HOST}"

# Substitute placeholders in all Quarto source files and the OpenAPI spec
echo "==> Substituting domain placeholders..."
find /app/quarto -name "*.qmd" -o -name "*.json" | xargs sed -i \
    -e "s|DOMAIN_PLACEHOLDER|${DOMAIN}|g" \
    -e "s|DOMAIN_HOST_PLACEHOLDER|${DOMAIN_HOST}|g"

# Render the Quarto site (output goes to quarto/_site)
echo "==> Rendering Quarto site..."
cd /app && quarto render quarto/

# Start the FastAPI server
echo "==> Starting server on port ${PORT:-8000}..."
exec uv run uvicorn messageboard.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}"
