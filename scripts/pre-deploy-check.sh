#!/bin/bash
# =============================================================================
# PRE-DEPLOYMENT CHECK SCRIPT
# =============================================================================
# This script runs Excel parity tests before deployment.
# If tests fail, deployment is blocked.
#
# Usage:
#   ./scripts/pre-deploy-check.sh          # Run against local or production API
#   ./scripts/pre-deploy-check.sh local    # Run against local API only
#   ./scripts/pre-deploy-check.sh prod     # Run against production API
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo ""
echo "============================================================"
echo "  EXCEL PARITY CHECK - PRE-DEPLOYMENT VALIDATION"
echo "============================================================"
echo ""

# Determine which API to test
if [ "$1" == "local" ]; then
    export TEST_LOCAL=1
    echo "Testing against: LOCAL API (http://localhost:8000)"
elif [ "$1" == "prod" ]; then
    export TEST_PRODUCTION=1
    echo "Testing against: PRODUCTION API"
else
    echo "Testing against: AUTO-DETECT (local if available, else production)"
fi

echo ""

# Always run Python directly to avoid conftest.py dependency issues
cd "$(dirname "$0")/.."

# Use python3 on macOS, python elsewhere
if command -v python3 &> /dev/null; then
    python3 tests/test_excel_parity_critical.py
else
    python tests/test_excel_parity_critical.py
fi
EXIT_CODE=$?

echo ""
echo "============================================================"

if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}  ALL TESTS PASSED - Deployment approved${NC}"
    echo "============================================================"
    echo ""
    exit 0
else
    echo -e "${RED}  TESTS FAILED - DEPLOYMENT BLOCKED${NC}"
    echo ""
    echo "  DO NOT deploy to production until all tests pass."
    echo "  Fix the calculation discrepancies first."
    echo "============================================================"
    echo ""
    exit 1
fi
