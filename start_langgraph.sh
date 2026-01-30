#!/bin/bash
# =============================================================================
# LangGraph Development Server Startup Script
# =============================================================================
#
# PROBLEM: The default recursion limit (25) is set at Python import time in
# langgraph-api's config.py module. The .env file is loaded by langgraph dev
# AFTER the module imports, which is too late.
#
# SOLUTION: This script exports LANGGRAPH_DEFAULT_RECURSION_LIMIT BEFORE
# starting the Python process, ensuring it's available at import time.
#
# USAGE:
#   ./start_langgraph.sh              # Start with defaults
#   ./start_langgraph.sh --no-browser # Pass additional args to langgraph dev
#
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================"
echo "  LangGraph Dev Server - Recursion Limit Fix"
echo "================================================"

# Load .env file manually to get all variables BEFORE Python starts
if [ -f .env ]; then
    echo "[1/3] Loading .env file..."
    set -a  # automatically export all variables
    source .env
    set +a
    echo "      Loaded $(grep -c '=' .env 2>/dev/null || echo 0) variables from .env"
else
    echo "[1/3] Warning: .env file not found"
fi

# CRITICAL: Set recursion limit BEFORE langgraph dev imports modules
# This overrides the default of 25 in langgraph_api/utils/config.py
export LANGGRAPH_DEFAULT_RECURSION_LIMIT=${LANGGRAPH_DEFAULT_RECURSION_LIMIT:-250}
export LANGGRAPH_RECURSION_LIMIT=${LANGGRAPH_RECURSION_LIMIT:-250}

echo "[2/3] Recursion limits configured:"
echo "      LANGGRAPH_DEFAULT_RECURSION_LIMIT=$LANGGRAPH_DEFAULT_RECURSION_LIMIT"
echo "      LANGGRAPH_RECURSION_LIMIT=$LANGGRAPH_RECURSION_LIMIT"

# Optional: Clear the in-memory database to force re-registration of assistants
# This ensures any config changes in langgraph.json are applied
# Uncomment if you need to reset assistant configs:
# export LANGGRAPH_CLEAR_DB_ON_START=true

echo "[3/3] Verifying langgraph installation..."
if ! command -v langgraph &> /dev/null; then
    echo "      ERROR: langgraph command not found"
    echo "      Install with: pip install -U 'langgraph-cli[inmem]'"
    exit 1
fi
echo "      langgraph CLI found"

echo "[4/4] Starting langgraph dev..."
echo "      (File server on port ${FILE_SERVER_PORT:-8090} auto-starts via document_tools.py)"
echo "================================================"
echo ""

# Start langgraph dev with any additional arguments
# --host 0.0.0.0 binds to all interfaces (required for external access from Flowise, etc.)
# Note: The embedded file server (port 8090) with skills, feedback, file downloads,
# and notification APIs auto-starts as a daemon thread when document_tools.py is
# imported by the LangGraph graphs. No separate process needed.
exec langgraph dev --host 0.0.0.0 "$@"
