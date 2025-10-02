#!/bin/bash

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║              REFACTORING VERIFICATION SCRIPT                             ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASSED=0
FAILED=0

# Test function
run_test() {
    local test_name="$1"
    local test_command="$2"

    echo -n "Testing: $test_name... "

    if eval "$test_command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        ((FAILED++))
        return 1
    fi
}

echo "1. SYNTAX VALIDATION"
echo "────────────────────"
run_test "constants.py syntax" "python3 -m py_compile inventory/constants.py"
run_test "utils.py syntax" "python3 -m py_compile inventory/utils.py"
run_test "views/__init__.py syntax" "python3 -m py_compile inventory/views/__init__.py"
run_test "views/helpers.py syntax" "python3 -m py_compile inventory/views/helpers.py"
run_test "views/inventory.py syntax" "python3 -m py_compile inventory/views/inventory.py"
run_test "views/sharing.py syntax" "python3 -m py_compile inventory/views/sharing.py"
run_test "views/api.py syntax" "python3 -m py_compile inventory/views/api.py"
run_test "views/settings.py syntax" "python3 -m py_compile inventory/views/settings.py"
run_test "views/auth.py syntax" "python3 -m py_compile inventory/views/auth.py"
run_test "views/errors.py syntax" "python3 -m py_compile inventory/views/errors.py"
echo ""

echo "2. FILE STRUCTURE"
echo "─────────────────"
run_test "constants.py exists" "test -f inventory/constants.py"
run_test "views/ directory exists" "test -d inventory/views"
run_test "views/__init__.py exists" "test -f inventory/views/__init__.py"
run_test "views/helpers.py exists" "test -f inventory/views/helpers.py"
run_test "views/inventory.py exists" "test -f inventory/views/inventory.py"
run_test "views/sharing.py exists" "test -f inventory/views/sharing.py"
run_test "views/api.py exists" "test -f inventory/views/api.py"
run_test "views/settings.py exists" "test -f inventory/views/settings.py"
run_test "views/auth.py exists" "test -f inventory/views/auth.py"
run_test "views/errors.py exists" "test -f inventory/views/errors.py"
run_test "views_old.py backup exists" "test -f inventory/views_old.py"
echo ""

echo "3. CONSTANTS VALIDATION"
echo "───────────────────────"
run_test "LOOKUP_LIMIT_PER_MIN defined" "grep -q 'LOOKUP_LIMIT_PER_MIN = 60' inventory/constants.py"
run_test "CSV_IMPORT_MAX_ROWS defined" "grep -q 'CSV_IMPORT_MAX_ROWS = 10_000' inventory/constants.py"
run_test "MAX_TEXT_LENGTH defined" "grep -q 'MAX_TEXT_LENGTH = 10_000' inventory/constants.py"
run_test "EXTERNAL_API_TIMEOUT defined" "grep -q 'EXTERNAL_API_TIMEOUT = 10' inventory/constants.py"
echo ""

echo "4. TYPE HINTS VALIDATION"
echo "────────────────────────"
run_test "helpers.py has type hints" "grep -q 'def.*->.*:' inventory/views/helpers.py"
run_test "inventory.py has type hints" "grep -q 'def.*->.*:' inventory/views/inventory.py"
run_test "sharing.py has type hints" "grep -q 'def.*->.*:' inventory/views/sharing.py"
run_test "api.py has type hints" "grep -q 'def.*->.*:' inventory/views/api.py"
run_test "settings.py has type hints" "grep -q 'def.*->.*:' inventory/views/settings.py"
echo ""

echo "5. IMPORTS VALIDATION"
echo "─────────────────────"
run_test "helpers.py imports from constants" "grep -q 'from ..constants import' inventory/views/helpers.py"
run_test "inventory.py imports from constants" "grep -q 'from ..constants import' inventory/views/inventory.py"
run_test "api.py imports from constants" "grep -q 'from ..constants import' inventory/views/api.py"
run_test "utils.py imports from constants" "grep -q 'from .constants import' inventory/utils.py"
echo ""

echo "6. ERROR HANDLING VALIDATION"
echo "─────────────────────────────"
run_test "inventory.py uses logger.exception" "grep -q 'logger.exception' inventory/views/inventory.py"
run_test "sharing.py uses logger.exception" "grep -q 'logger.exception' inventory/views/sharing.py"
run_test "api.py uses logger.exception" "grep -q 'logger.exception' inventory/views/api.py"
run_test "settings.py uses logger.exception" "grep -q 'logger.exception' inventory/views/settings.py"
echo ""

echo "7. EXPORTS VALIDATION"
echo "─────────────────────"
run_test "inventory_list exported" "grep -q 'inventory_list' inventory/views/__init__.py"
run_test "lookup_part exported" "grep -q 'lookup_part' inventory/views/__init__.py"
run_test "shared_inventory exported" "grep -q 'shared_inventory' inventory/views/__init__.py"
run_test "settings_view exported" "grep -q 'settings_view' inventory/views/__init__.py"
run_test "signup exported" "grep -q 'signup' inventory/views/__init__.py"
echo ""

echo "╔══════════════════════════════════════════════════════════════════════════╗"
echo "║                              TEST SUMMARY                                ║"
echo "╚══════════════════════════════════════════════════════════════════════════╝"
echo ""
echo -e "  ${GREEN}Passed: $PASSED${NC}"
echo -e "  ${RED}Failed: $FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL TESTS PASSED!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Start development server: python manage.py runserver"
    echo "  2. Test all features in browser"
    echo "  3. See REFACTORING_SUMMARY.md for detailed testing checklist"
    echo ""
    exit 0
else
    echo -e "${RED}✗ SOME TESTS FAILED${NC}"
    echo ""
    echo "Please review the failures above before proceeding."
    echo ""
    exit 1
fi
