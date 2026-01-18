#!/usr/bin/env python3
"""
CRITICAL: Excel Parity Tests

These tests MUST pass before ANY deployment to production.
They validate that calculations match the 225 Worth Ave Excel workbook exactly.

Source of truth: /Users/tooeycourtemanche/Desktop/Models XLS/225 Worth Ave_Model(revised).xlsx

If these tests fail:
1. DO NOT deploy to production
2. Investigate the calculation discrepancy
3. Fix the issue and re-run tests
4. Only deploy when all tests pass

Run standalone: python tests/test_excel_parity_critical.py
Run with pytest: pytest tests/test_excel_parity_critical.py -v --ignore=tests/conftest.py
"""

import sys
import os

# Ensure we can run standalone without pytest/conftest dependencies
try:
    import pytest
    HAS_PYTEST = True
except ImportError:
    HAS_PYTEST = False

import requests
from datetime import date
from typing import Dict, Any

# =============================================================================
# EXCEL BENCHMARK VALUES - From actual Excel file (NOT PRD documentation)
# =============================================================================

# Actual Excel parameters (verified from 225 Worth Ave_Model(revised).xlsx)
EXCEL_PARAMS = {
    "acquisition_date": "2026-03-31",
    "hold_period_months": 120,
    "purchase_price": 41500,      # $41,500K
    "closing_costs": 500,          # $500K (PRD incorrectly says $950K)
    "total_sf": 9932,
    "in_place_rent_psf": 193.22,
    "market_rent_psf": 300,
    "vacancy_rate": 0.0,
    "fixed_opex_psf": 36.0,
    "management_fee_percent": 0.04,
    "property_tax_amount": 622.5,
    "capex_reserve_psf": 5.0,
    "rent_growth": 0.025,
    "expense_growth": 0.025,
    "exit_cap_rate": 0.05,
    "sales_cost_percent": 0.01,
    "loan_amount": 16937.18,       # $16,937K at 40% LTC (PRD incorrectly says $23,535K)
    "interest_rate": 0.0525,       # 5.25%
    "io_months": 120,
    "amortization_years": 30,
    "nnn_lease": True,
    "use_actual_365": True,
    "tenants": [
        {
            "name": "Peter Millar",
            "rsf": 2300,
            "in_place_rent_psf": 201.45,
            "market_rent_psf": 300.00,
            "lease_end_month": 83,
            "apply_rollover_costs": False,
            "free_rent_months": 0,
            "ti_buildout_months": 0
        },
        {
            "name": "J McLaughlin",
            "rsf": 1868,
            "in_place_rent_psf": 200.47,
            "market_rent_psf": 300.00,
            "lease_end_month": 50,
            "apply_rollover_costs": True,
            "free_rent_months": 10,
            "ti_buildout_months": 6
        },
        {
            "name": "Gucci",
            "rsf": 5950,
            "in_place_rent_psf": 187.65,
            "market_rent_psf": 300.00,
            "lease_end_month": 210,  # Beyond hold period
            "apply_rollover_costs": True,
            "free_rent_months": 10,
            "ti_buildout_months": 6
        }
    ]
}

# Excel benchmark values (from actual workbook cells)
EXCEL_BENCHMARKS = {
    # IRR Targets (from Excel)
    "unleveraged_irr": 0.0857,     # 8.57% (cell reference: Model sheet IRR)
    "leveraged_irr": 0.1009,       # 10.09%
    "lp_irr": 0.0939,              # 9.39%
    "gp_irr": 0.1502,              # 15.02%

    # Month 1 Values (from Excel L column)
    "month_1_noi": 158.97,         # $158.97K (L72)
    "month_1_interest": 73.09,     # $73.09K (L122)
    "month_1_base_rent_a": 38.69,  # Space A (L46)
    "month_1_base_rent_b": 31.27,  # Space B (L47)
    "month_1_base_rent_c": 93.24,  # Space C (L48)

    # Month 120 Values (from Excel EA column)
    "month_120_noi": 247.80,       # $247.80K (EA72)

    # Exit Values (from Excel Assumptions sheet)
    "forward_noi": 3079.84,        # $3,079.84K (AA14)
    "gross_exit_value": 61596.78,  # $61,596.78K (AA16)
    "exit_proceeds": 60980.82,     # $60,980.82K (AA18)

    # Equity Values
    "total_equity": 25405.78,      # $25,405.78K (L13)
}

# Tolerances for matching (some calculations have minor rounding differences)
TOLERANCES = {
    "irr": 0.003,           # 0.3% tolerance for IRR (e.g., 8.57% ± 0.3% = 8.27% to 8.87%)
    "noi": 0.5,             # $0.5K tolerance for NOI
    "interest": 0.5,        # $0.5K tolerance for interest
    "exit_proceeds": 50,    # $50K tolerance for exit proceeds (~0.08%)
    "forward_noi": 5,       # $5K tolerance for forward NOI (~0.16%)
}


# =============================================================================
# Test Configuration
# =============================================================================

# API endpoints to test
LOCAL_API = "http://localhost:8000/api/calculate/cashflows"
PROD_API = "https://re-fin-model-225worth-3348ecdc48e8.herokuapp.com/api/calculate/cashflows"

def get_api_url():
    """Get the API URL based on environment."""
    import os
    if os.environ.get("TEST_PRODUCTION"):
        return PROD_API
    # Try local first, fall back to production
    try:
        requests.get("http://localhost:8000/health", timeout=2)
        return LOCAL_API
    except:
        return PROD_API


def call_api(params: Dict[str, Any]) -> Dict[str, Any]:
    """Call the cashflows API and return the response."""
    url = get_api_url()
    response = requests.post(url, json=params, timeout=60)
    response.raise_for_status()
    return response.json()


# =============================================================================
# CRITICAL TESTS - Must pass before deployment
# =============================================================================

class TestExcelParityCritical:
    """
    Critical tests that validate Excel parity.

    THESE TESTS MUST PASS BEFORE ANY PRODUCTION DEPLOYMENT.
    """

    @pytest.fixture(scope="class")
    def api_response(self):
        """Call API once and cache the response for all tests."""
        return call_api(EXCEL_PARAMS)

    # -------------------------------------------------------------------------
    # IRR Tests
    # -------------------------------------------------------------------------

    def test_unleveraged_irr(self, api_response):
        """Unleveraged IRR must match Excel within tolerance."""
        actual = api_response["metrics"]["unleveraged_irr"]
        expected = EXCEL_BENCHMARKS["unleveraged_irr"]
        tolerance = TOLERANCES["irr"]

        assert abs(actual - expected) <= tolerance, (
            f"CRITICAL: Unleveraged IRR mismatch!\n"
            f"  Expected: {expected*100:.2f}%\n"
            f"  Actual:   {actual*100:.2f}%\n"
            f"  Diff:     {(actual-expected)*100:+.2f}%\n"
            f"  Tolerance: ±{tolerance*100:.2f}%"
        )

    def test_leveraged_irr(self, api_response):
        """Leveraged IRR must match Excel within tolerance."""
        actual = api_response["metrics"]["leveraged_irr"]
        expected = EXCEL_BENCHMARKS["leveraged_irr"]
        tolerance = TOLERANCES["irr"]

        assert abs(actual - expected) <= tolerance, (
            f"CRITICAL: Leveraged IRR mismatch!\n"
            f"  Expected: {expected*100:.2f}%\n"
            f"  Actual:   {actual*100:.2f}%\n"
            f"  Diff:     {(actual-expected)*100:+.2f}%\n"
            f"  Tolerance: ±{tolerance*100:.2f}%"
        )

    def test_lp_irr(self, api_response):
        """LP IRR must match Excel within tolerance."""
        actual = api_response["metrics"]["lp_irr"]
        expected = EXCEL_BENCHMARKS["lp_irr"]
        tolerance = TOLERANCES["irr"]

        assert abs(actual - expected) <= tolerance, (
            f"CRITICAL: LP IRR mismatch!\n"
            f"  Expected: {expected*100:.2f}%\n"
            f"  Actual:   {actual*100:.2f}%\n"
            f"  Diff:     {(actual-expected)*100:+.2f}%\n"
            f"  Tolerance: ±{tolerance*100:.2f}%"
        )

    def test_gp_irr(self, api_response):
        """GP IRR must match Excel within tolerance."""
        actual = api_response["metrics"]["gp_irr"]
        expected = EXCEL_BENCHMARKS["gp_irr"]
        tolerance = TOLERANCES["irr"]

        assert abs(actual - expected) <= tolerance, (
            f"CRITICAL: GP IRR mismatch!\n"
            f"  Expected: {expected*100:.2f}%\n"
            f"  Actual:   {actual*100:.2f}%\n"
            f"  Diff:     {(actual-expected)*100:+.2f}%\n"
            f"  Tolerance: ±{tolerance*100:.2f}%"
        )

    # -------------------------------------------------------------------------
    # Month 1 NOI Tests
    # -------------------------------------------------------------------------

    def test_month_1_noi(self, api_response):
        """Month 1 NOI must match Excel exactly."""
        actual = api_response["monthly_cashflows"][1]["noi"]
        expected = EXCEL_BENCHMARKS["month_1_noi"]
        tolerance = TOLERANCES["noi"]

        assert abs(actual - expected) <= tolerance, (
            f"CRITICAL: Month 1 NOI mismatch!\n"
            f"  Expected: ${expected:.2f}K\n"
            f"  Actual:   ${actual:.2f}K\n"
            f"  Diff:     ${actual-expected:+.2f}K\n"
            f"  Tolerance: ±${tolerance:.2f}K"
        )

    def test_month_1_interest(self, api_response):
        """Month 1 Interest must match Excel exactly."""
        actual = api_response["monthly_cashflows"][1]["interest_expense"]
        expected = EXCEL_BENCHMARKS["month_1_interest"]
        tolerance = TOLERANCES["interest"]

        assert abs(actual - expected) <= tolerance, (
            f"CRITICAL: Month 1 Interest mismatch!\n"
            f"  Expected: ${expected:.2f}K\n"
            f"  Actual:   ${actual:.2f}K\n"
            f"  Diff:     ${actual-expected:+.2f}K\n"
            f"  Tolerance: ±${tolerance:.2f}K"
        )

    # -------------------------------------------------------------------------
    # Month 120 (Exit) Tests
    # -------------------------------------------------------------------------

    def test_month_120_noi(self, api_response):
        """Month 120 NOI must match Excel exactly."""
        actual = api_response["monthly_cashflows"][120]["noi"]
        expected = EXCEL_BENCHMARKS["month_120_noi"]
        tolerance = TOLERANCES["noi"]

        assert abs(actual - expected) <= tolerance, (
            f"CRITICAL: Month 120 NOI mismatch!\n"
            f"  Expected: ${expected:.2f}K\n"
            f"  Actual:   ${actual:.2f}K\n"
            f"  Diff:     ${actual-expected:+.2f}K\n"
            f"  Tolerance: ±${tolerance:.2f}K"
        )

    def test_exit_proceeds(self, api_response):
        """Exit proceeds must match Excel within tolerance."""
        actual = api_response["monthly_cashflows"][120]["exit_proceeds"]
        expected = EXCEL_BENCHMARKS["exit_proceeds"]
        tolerance = TOLERANCES["exit_proceeds"]

        assert abs(actual - expected) <= tolerance, (
            f"CRITICAL: Exit Proceeds mismatch!\n"
            f"  Expected: ${expected:.2f}K\n"
            f"  Actual:   ${actual:.2f}K\n"
            f"  Diff:     ${actual-expected:+.2f}K\n"
            f"  Tolerance: ±${tolerance:.2f}K"
        )

    # -------------------------------------------------------------------------
    # Month 0 Tests (Acquisition)
    # -------------------------------------------------------------------------

    def test_month_0_noi_is_zero(self, api_response):
        """Month 0 NOI must be zero (acquisition month, no operations)."""
        actual = api_response["monthly_cashflows"][0]["noi"]

        assert actual == 0.0, (
            f"CRITICAL: Month 0 NOI should be $0 (acquisition month)!\n"
            f"  Actual: ${actual:.2f}K"
        )

    def test_month_0_acquisition_costs(self, api_response):
        """Month 0 acquisition costs must equal purchase + closing."""
        actual = api_response["monthly_cashflows"][0]["acquisition_costs"]
        expected = EXCEL_PARAMS["purchase_price"] + EXCEL_PARAMS["closing_costs"]

        assert actual == expected, (
            f"CRITICAL: Month 0 Acquisition costs mismatch!\n"
            f"  Expected: ${expected:.2f}K\n"
            f"  Actual:   ${actual:.2f}K"
        )


# =============================================================================
# Summary Report
# =============================================================================

def test_generate_parity_report(api_response=None):
    """Generate a summary report of Excel parity status."""
    if api_response is None:
        api_response = call_api(EXCEL_PARAMS)

    print("\n" + "="*70)
    print("EXCEL PARITY REPORT")
    print("="*70)

    metrics = api_response["metrics"]
    cfs = api_response["monthly_cashflows"]

    # IRRs
    print("\nIRR COMPARISON:")
    print("-"*50)
    irr_tests = [
        ("Unleveraged IRR", metrics["unleveraged_irr"], EXCEL_BENCHMARKS["unleveraged_irr"]),
        ("Leveraged IRR", metrics["leveraged_irr"], EXCEL_BENCHMARKS["leveraged_irr"]),
        ("LP IRR", metrics["lp_irr"], EXCEL_BENCHMARKS["lp_irr"]),
        ("GP IRR", metrics["gp_irr"], EXCEL_BENCHMARKS["gp_irr"]),
    ]

    all_pass = True
    for name, actual, expected in irr_tests:
        diff = actual - expected
        status = "✓" if abs(diff) <= TOLERANCES["irr"] else "✗"
        if status == "✗":
            all_pass = False
        print(f"  {name:20} {actual*100:6.2f}%  (Excel: {expected*100:.2f}%)  {diff*100:+.2f}%  {status}")

    # Key Values
    print("\nKEY VALUES:")
    print("-"*50)
    value_tests = [
        ("Month 1 NOI", cfs[1]["noi"], EXCEL_BENCHMARKS["month_1_noi"], TOLERANCES["noi"]),
        ("Month 1 Interest", cfs[1]["interest_expense"], EXCEL_BENCHMARKS["month_1_interest"], TOLERANCES["interest"]),
        ("Month 120 NOI", cfs[120]["noi"], EXCEL_BENCHMARKS["month_120_noi"], TOLERANCES["noi"]),
        ("Exit Proceeds", cfs[120]["exit_proceeds"], EXCEL_BENCHMARKS["exit_proceeds"], TOLERANCES["exit_proceeds"]),
    ]

    for name, actual, expected, tol in value_tests:
        diff = actual - expected
        status = "✓" if abs(diff) <= tol else "✗"
        if status == "✗":
            all_pass = False
        print(f"  {name:20} ${actual:10.2f}K  (Excel: ${expected:.2f}K)  {status}")

    print("\n" + "="*70)
    if all_pass:
        print("STATUS: ALL TESTS PASSED - Safe to deploy")
    else:
        print("STATUS: TESTS FAILED - DO NOT DEPLOY")
    print("="*70 + "\n")

    return all_pass


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    """Run parity check from command line."""
    import sys

    print("Running Excel Parity Check...")
    print(f"API: {get_api_url()}")

    try:
        response = call_api(EXCEL_PARAMS)
        passed = test_generate_parity_report(response)
        sys.exit(0 if passed else 1)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)
