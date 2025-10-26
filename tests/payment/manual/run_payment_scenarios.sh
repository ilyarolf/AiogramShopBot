#!/bin/bash
#
# Payment Validation Test Scenarios Runner
#
# Runs all payment validation scenarios against the webhook endpoint
# to test the complete payment validation system.
#
# Usage:
#   ./tests/manual/run_payment_scenarios.sh
#
# Environment Variables:
#   WEBHOOK_URL - Webhook endpoint URL (required)
#   KRYPTO_EXPRESS_API_SECRET - API secret for HMAC signature (optional)
#   PAYMENT_ID - Payment ID to use (default: 999999)
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
WEBHOOK_URL=${WEBHOOK_URL:-"http://localhost:8000/webhook/cryptoprocessing/event"}
PAYMENT_ID=${PAYMENT_ID:-999999}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SIMULATOR="$SCRIPT_DIR/simulate_payment_webhook.py"

echo "================================================================"
echo "   Payment Validation Test Scenarios"
echo "================================================================"
echo ""
echo "Webhook URL: $WEBHOOK_URL"
echo "Payment ID: $PAYMENT_ID"
echo ""
echo "================================================================"
echo ""

# Check if simulator exists
if [ ! -f "$SIMULATOR" ]; then
    echo -e "${RED}ERROR: Webhook simulator not found at: $SIMULATOR${NC}"
    exit 1
fi

# Check if webhook URL is set
if [ -z "$WEBHOOK_URL" ]; then
    echo -e "${RED}ERROR: WEBHOOK_URL environment variable not set${NC}"
    echo "Example: export WEBHOOK_URL='http://localhost:8000/webhook/cryptoprocessing/event'"
    exit 1
fi

# Function to run scenario
run_scenario() {
    local name="$1"
    shift
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Scenario: $name${NC}"
    echo -e "${BLUE}========================================${NC}"
    python3 "$SIMULATOR" "$@" --url "$WEBHOOK_URL"
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✅ Success${NC}"
    else
        echo -e "${RED}❌ Failed (exit code: $exit_code)${NC}"
    fi

    echo ""
    sleep 2
    return $exit_code
}

# Track results
PASSED=0
FAILED=0

echo "Starting test scenarios..."
echo ""

# Scenario 1: Exact Payment
if run_scenario "Exact Payment (0.001 BTC)" \
    --payment-id $PAYMENT_ID \
    --amount-paid 0.001 \
    --amount-required 0.001 \
    --fiat-amount 50.0; then
    ((PASSED++))
else
    ((FAILED++))
fi

# Scenario 2: Minor Overpayment (0.05% - forfeits to shop)
((PAYMENT_ID++))
if run_scenario "Minor Overpayment (0.05% - forfeits)" \
    --payment-id $PAYMENT_ID \
    --amount-paid 0.0010005 \
    --amount-required 0.001 \
    --fiat-amount 50.025; then
    ((PASSED++))
else
    ((FAILED++))
fi

# Scenario 3: Significant Overpayment (10% - wallet credit)
((PAYMENT_ID++))
if run_scenario "Significant Overpayment (10% - wallet credit)" \
    --payment-id $PAYMENT_ID \
    --amount-paid 0.0011 \
    --amount-required 0.001 \
    --fiat-amount 55.0; then
    ((PASSED++))
else
    ((FAILED++))
fi

# Scenario 4: Underpayment (90% - first attempt)
((PAYMENT_ID++))
if run_scenario "Underpayment - First Attempt (90%)" \
    --payment-id $PAYMENT_ID \
    --amount-paid 0.0009 \
    --amount-required 0.001 \
    --fiat-amount 45.0; then
    ((PASSED++))
else
    ((FAILED++))
fi

# Scenario 5: Currency Mismatch
((PAYMENT_ID++))
if run_scenario "Currency Mismatch (paid LTC, expected BTC)" \
    --payment-id $PAYMENT_ID \
    --amount-paid 0.05 \
    --amount-required 0.001 \
    --crypto LTC \
    --fiat-amount 50.0; then
    ((PASSED++))
else
    ((FAILED++))
fi

# Scenario 6: Payment Expired (isPaid=false)
((PAYMENT_ID++))
if run_scenario "Payment Expired" \
    --payment-id $PAYMENT_ID \
    --amount-paid 0.001 \
    --amount-required 0.001 \
    --fiat-amount 50.0 \
    --not-paid; then
    ((PASSED++))
else
    ((FAILED++))
fi

# Summary
echo ""
echo "================================================================"
echo "   Test Results Summary"
echo "================================================================"
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo "Total:  $((PASSED + FAILED))"
echo "================================================================"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✅ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}❌ Some tests failed!${NC}"
    exit 1
fi
