#!/usr/bin/env bash
set -e

echo "==> pytest"
pytest -q

echo "==> coverage"
coverage run -m pytest -q
coverage report --fail-under=85 \
    --include='src/mochi_deckgen_mcp/local/*,src/mochi_deckgen_mcp/mochi/*,src/mochi_deckgen_mcp/sync/*,src/mochi_deckgen_mcp/tools/*'

echo "==> ruff check"
ruff check .

echo "==> ruff format --check"
ruff format --check .

echo "==> mypy --strict"
mypy src/mochi_deckgen_mcp

echo "==> prompt compression"
pytest tests/test_prompt_compression.py -q

echo "==> server registration smoke"
pytest tests/test_server_registration.py -q

echo
echo "ALL GREEN"
