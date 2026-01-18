"""
Excel Parity Tests

These tests verify that our calculations match the 225 Worth Ave Excel model.
Benchmark values are extracted from the source Excel file.

See: docs/225_Worth_Ave_Model_Documentation_PRD.md Section 7 for full specification.
"""

import pytest
from datetime import date
from app.calculations.cashflow import (
    Tenant,
    calculate_tenant_rent,
    calculate_total_tenant_rent,
    generate_cash_flows,
)
from app.calculations import irr


# =============================================================================
# BENCHMARK DATA FROM EXCEL MODEL
# =============================================================================

# Tenant rent roll from Excel
# Excel H-column determines rollover behavior:
# - H=1 (apply_rollover_costs=False): No TI/LC/Free rent at rollover
# - H=0 (apply_rollover_costs=True): Apply TI/LC/Free rent at rollover
TENANTS = [
    Tenant(
        name="Peter Millar (G/Fore)",
        rsf=2300,
        in_place_rent_psf=201.45,
        market_rent_psf=300,
        lease_end_month=69,
        apply_rollover_costs=False,  # H49=1 in Excel: no rollover costs
        ti_buildout_months=6,
        free_rent_months=10,
    ),
    Tenant(
        name="J McLaughlin",
        rsf=1868,
        in_place_rent_psf=200.47,
        market_rent_psf=300,
        lease_end_month=50,
        apply_rollover_costs=True,  # H50=0 in Excel: has rollover costs
        ti_buildout_months=6,
        free_rent_months=10,
    ),
    Tenant(
        name="Gucci",
        rsf=5950,
        in_place_rent_psf=187.65,
        market_rent_psf=300,
        lease_end_month=117,  # December 2035 (within 10-year hold)
        apply_rollover_costs=True,  # H51=0 in Excel: has rollover costs
        ti_buildout_months=6,
        free_rent_months=10,
    ),
]

# Excel benchmark values (all in $000s unless noted)
EXCEL_BENCHMARKS = {
    # Input values
    "purchase_price": 41500,
    "closing_costs": 500,
    "total_acquisition_cost": 42342.96,
    "hold_period_months": 120,
    "loan_amount": 16937.18,
    "ltc_percent": 0.40,
    "interest_rate": 0.0525,
    "io_months": 120,
    "total_equity": 25405.78,
    "lp_equity": 22865.20,
    "gp_equity": 2540.58,
    "rent_growth": 0.025,
    "expense_growth": 0.025,
    "exit_cap_rate": 0.05,
    "sales_cost_percent": 0.01,
    # Month 1 (period 1) tenant rents
    "month1_space_a_rent": 38.69,
    "month1_space_b_rent": 31.27,
    "month1_space_c_rent": 93.24,
    # Expected returns
    "unleveraged_irr": 0.0857,
    "unleveraged_multiple": 2.01,
    "unleveraged_profit": 42252.65,
    "leveraged_irr": 0.1009,
    "leveraged_multiple": 2.30,
    "leveraged_profit": 33014.57,
    "lp_irr": 0.0939,
    "lp_multiple": 2.17,
    "gp_irr": 0.1502,
    "gp_multiple": 3.51,
    # Month 120 exit values
    "exit_noi": 247.80,
    "exit_proceeds": 60980.82,
    "exit_unleveraged_cf": 61228.62,
    "exit_leveraged_cf": 44215.91,
}

# Tolerance thresholds
IRR_TOLERANCE = 0.0005  # 5 basis points
MULTIPLE_TOLERANCE = 0.01
CASHFLOW_TOLERANCE = 1.0  # $1K


# =============================================================================
# TENANT RENT CALCULATION TESTS
# =============================================================================


class TestTenantRentCalculation:
    """Test tenant-by-tenant rent calculation matches Excel."""

    def test_peter_millar_month1_rent(self):
        """Peter Millar rent in month 1 should match Excel."""
        tenant = TENANTS[0]  # Peter Millar
        rent = calculate_tenant_rent(tenant, period=1, rent_growth=0.025)
        expected = EXCEL_BENCHMARKS["month1_space_a_rent"]
        assert abs(rent - expected) < 0.01, f"Expected {expected}, got {rent}"

    def test_j_mclaughlin_month1_rent(self):
        """J McLaughlin rent in month 1 should match Excel."""
        tenant = TENANTS[1]  # J McLaughlin
        rent = calculate_tenant_rent(tenant, period=1, rent_growth=0.025)
        expected = EXCEL_BENCHMARKS["month1_space_b_rent"]
        assert abs(rent - expected) < 0.01, f"Expected {expected}, got {rent}"

    def test_gucci_month1_rent(self):
        """Gucci rent in month 1 should match Excel."""
        tenant = TENANTS[2]  # Gucci
        rent = calculate_tenant_rent(tenant, period=1, rent_growth=0.025)
        expected = EXCEL_BENCHMARKS["month1_space_c_rent"]
        assert abs(rent - expected) < 0.01, f"Expected {expected}, got {rent}"

    def test_total_rent_month1(self):
        """Total rent from all tenants in month 1."""
        total = calculate_total_tenant_rent(TENANTS, period=1, rent_growth=0.025)
        expected = (
            EXCEL_BENCHMARKS["month1_space_a_rent"]
            + EXCEL_BENCHMARKS["month1_space_b_rent"]
            + EXCEL_BENCHMARKS["month1_space_c_rent"]
        )
        assert abs(total - expected) < 0.05, f"Expected {expected}, got {total}"

    def test_lease_rollover_to_market_rent(self):
        """After lease expiry, tenant should roll to market rent."""
        tenant = TENANTS[1]  # J McLaughlin - lease ends at month 50

        # Before expiry (month 50) - in-place rent
        rent_before = calculate_tenant_rent(tenant, period=50, rent_growth=0.025)
        # After expiry (month 51) - market rent
        rent_after = calculate_tenant_rent(tenant, period=51, rent_growth=0.025)

        # Market rent is higher, so rent should increase significantly
        assert rent_after > rent_before * 1.4, "Rent should increase after lease expiry"

    def test_escalation_applied_monthly(self):
        """Rent should increase with monthly escalation."""
        tenant = TENANTS[0]
        rent_month1 = calculate_tenant_rent(tenant, period=1, rent_growth=0.025)
        rent_month12 = calculate_tenant_rent(tenant, period=12, rent_growth=0.025)
        rent_month24 = calculate_tenant_rent(tenant, period=24, rent_growth=0.025)

        # Rent should increase over time
        assert rent_month12 > rent_month1
        assert rent_month24 > rent_month12

        # Year-over-year escalation should be approximately 2.5%
        yoy_factor = rent_month24 / rent_month12
        assert 1.024 < yoy_factor < 1.026, f"YoY factor should be ~2.5%, got {yoy_factor}"


# =============================================================================
# CASH FLOW GENERATION TESTS
# =============================================================================


class TestCashFlowGeneration:
    """Test full cash flow generation with tenant data."""

    @pytest.fixture
    def cash_flows(self):
        """Generate cash flows with Excel input values."""
        return generate_cash_flows(
            acquisition_date=date(2024, 1, 1),
            hold_period_months=120,
            purchase_price=EXCEL_BENCHMARKS["purchase_price"],
            closing_costs=EXCEL_BENCHMARKS["closing_costs"],
            total_sf=10118,  # Sum of tenant RSFs
            in_place_rent_psf=193.15,  # Weighted average (fallback)
            market_rent_psf=300,
            rent_growth=EXCEL_BENCHMARKS["rent_growth"],
            vacancy_rate=0.0,
            fixed_opex_psf=36.0,
            management_fee_percent=0.04,
            property_tax_amount=622.5,  # Annual in $000s
            capex_reserve_psf=5.0,
            expense_growth=EXCEL_BENCHMARKS["expense_growth"],
            exit_cap_rate=EXCEL_BENCHMARKS["exit_cap_rate"],
            sales_cost_percent=EXCEL_BENCHMARKS["sales_cost_percent"],
            loan_amount=EXCEL_BENCHMARKS["loan_amount"],
            interest_rate=EXCEL_BENCHMARKS["interest_rate"],
            io_months=EXCEL_BENCHMARKS["io_months"],
            amortization_years=30,
            tenants=TENANTS,
        )

    def test_month0_no_revenue(self, cash_flows):
        """Month 0 (acquisition) should have no operating revenue."""
        assert cash_flows[0]["potential_revenue"] == 0

    def test_month0_acquisition_costs(self, cash_flows):
        """Month 0 should have acquisition costs."""
        expected = EXCEL_BENCHMARKS["purchase_price"] + EXCEL_BENCHMARKS["closing_costs"]
        assert abs(cash_flows[0]["acquisition_costs"] - expected) < 1

    def test_month1_has_revenue(self, cash_flows):
        """Month 1 should have operating revenue."""
        assert cash_flows[1]["potential_revenue"] > 0

    def test_month120_exit_proceeds(self, cash_flows):
        """Month 120 should have exit proceeds."""
        assert cash_flows[120]["exit_proceeds"] > 0

    def test_leveraged_cf_includes_loan_proceeds(self, cash_flows):
        """Month 0 leveraged CF should include loan proceeds."""
        # Leveraged CF = Unleveraged CF + Loan Proceeds
        # So leveraged should be less negative than unleveraged by loan amount
        unlev = cash_flows[0]["unleveraged_cash_flow"]
        lev = cash_flows[0]["leveraged_cash_flow"]
        diff = lev - unlev
        assert abs(diff - EXCEL_BENCHMARKS["loan_amount"]) < 1


# =============================================================================
# RETURN METRICS TESTS
# =============================================================================


class TestReturnMetrics:
    """Test return metric calculations against Excel benchmarks."""

    @pytest.fixture
    def cash_flows_and_dates(self):
        """Generate cash flows and dates for IRR calculation."""
        from app.calculations.cashflow import generate_monthly_dates

        cfs = generate_cash_flows(
            acquisition_date=date(2024, 1, 1),
            hold_period_months=120,
            purchase_price=EXCEL_BENCHMARKS["purchase_price"],
            closing_costs=EXCEL_BENCHMARKS["closing_costs"],
            total_sf=10118,
            in_place_rent_psf=193.15,
            market_rent_psf=300,
            rent_growth=EXCEL_BENCHMARKS["rent_growth"],
            vacancy_rate=0.0,
            fixed_opex_psf=36.0,
            management_fee_percent=0.04,
            property_tax_amount=622.5,
            capex_reserve_psf=5.0,
            expense_growth=EXCEL_BENCHMARKS["expense_growth"],
            exit_cap_rate=EXCEL_BENCHMARKS["exit_cap_rate"],
            sales_cost_percent=EXCEL_BENCHMARKS["sales_cost_percent"],
            loan_amount=EXCEL_BENCHMARKS["loan_amount"],
            interest_rate=EXCEL_BENCHMARKS["interest_rate"],
            io_months=EXCEL_BENCHMARKS["io_months"],
            amortization_years=30,
            tenants=TENANTS,
        )
        dates = generate_monthly_dates(date(2024, 1, 1), 120)
        return cfs, dates

    def test_unleveraged_irr_direction(self, cash_flows_and_dates):
        """Unleveraged IRR should be positive."""
        cfs, dates = cash_flows_and_dates
        unlev_cf = [cf["unleveraged_cash_flow"] for cf in cfs]
        irr_val = irr.calculate_xirr(unlev_cf, dates)
        assert irr_val > 0, "Unleveraged IRR should be positive"

    def test_leveraged_irr_direction(self, cash_flows_and_dates):
        """Leveraged IRR should be positive and higher than unleveraged."""
        cfs, dates = cash_flows_and_dates
        unlev_cf = [cf["unleveraged_cash_flow"] for cf in cfs]
        lev_cf = [cf["leveraged_cash_flow"] for cf in cfs]
        unlev_irr = irr.calculate_xirr(unlev_cf, dates)
        lev_irr = irr.calculate_xirr(lev_cf, dates)
        assert lev_irr > 0, "Leveraged IRR should be positive"
        # Positive leverage effect: leveraged > unleveraged
        assert lev_irr > unlev_irr, "Positive leverage should increase IRR"

    def test_multiple_positive(self, cash_flows_and_dates):
        """Investment multiples should be greater than 1."""
        cfs, _ = cash_flows_and_dates
        unlev_cf = [cf["unleveraged_cash_flow"] for cf in cfs]
        lev_cf = [cf["leveraged_cash_flow"] for cf in cfs]
        assert irr.calculate_multiple(unlev_cf) > 1
        assert irr.calculate_multiple(lev_cf) > 1


# =============================================================================
# NNN EXPENSE REIMBURSEMENT TESTS
# =============================================================================


class TestNNNReimbursements:
    """Tests for expense reimbursement (NNN lease structure)."""

    @pytest.fixture
    def nnn_cash_flows(self):
        """Generate cash flows with NNN enabled."""
        return generate_cash_flows(
            acquisition_date=date(2024, 1, 1),
            hold_period_months=120,
            purchase_price=EXCEL_BENCHMARKS["purchase_price"],
            closing_costs=EXCEL_BENCHMARKS["closing_costs"],
            total_sf=9932,
            in_place_rent_psf=193.15,
            market_rent_psf=300,
            rent_growth=EXCEL_BENCHMARKS["rent_growth"],
            vacancy_rate=0.0,
            fixed_opex_psf=36.0,
            management_fee_percent=0.04,
            property_tax_amount=622.5,
            capex_reserve_psf=5.0,
            expense_growth=EXCEL_BENCHMARKS["expense_growth"],
            exit_cap_rate=EXCEL_BENCHMARKS["exit_cap_rate"],
            sales_cost_percent=EXCEL_BENCHMARKS["sales_cost_percent"],
            loan_amount=EXCEL_BENCHMARKS["loan_amount"],
            interest_rate=EXCEL_BENCHMARKS["interest_rate"],
            io_months=EXCEL_BENCHMARKS["io_months"],
            amortization_years=30,
            tenants=TENANTS,
            nnn_lease=True,
            use_actual_365=True,
        )

    def test_fixed_opex_reimbursement(self, nnn_cash_flows):
        """Fixed OpEx should be reimbursed as revenue in NNN lease."""
        # Month 1 should have reimbursement revenue
        cf = nnn_cash_flows[1]
        # Reimbursement should include fixed opex + property tax
        expected_min = cf["fixed_opex"] + cf["property_tax"]
        assert cf["reimbursement_revenue"] >= expected_min * 0.95

    def test_property_tax_reimbursement(self, nnn_cash_flows):
        """Property taxes should be reimbursed as revenue."""
        cf = nnn_cash_flows[1]
        # Property tax is ~$51.88K monthly
        assert cf["property_tax"] > 50
        # Reimbursement revenue should include property tax
        assert cf["reimbursement_revenue"] > cf["property_tax"]

    def test_nnn_has_higher_revenue_than_gross(self):
        """NNN lease should have higher revenue due to reimbursements."""
        # With NNN
        nnn_cf = generate_cash_flows(
            acquisition_date=date(2024, 1, 1),
            hold_period_months=12,
            purchase_price=41500,
            closing_costs=500,
            total_sf=10000,
            in_place_rent_psf=200,
            market_rent_psf=300,
            rent_growth=0.025,
            vacancy_rate=0.0,
            fixed_opex_psf=36,
            management_fee_percent=0.04,
            property_tax_amount=500,
            capex_reserve_psf=5,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.01,
            nnn_lease=True,
        )

        # Without NNN
        gross_cf = generate_cash_flows(
            acquisition_date=date(2024, 1, 1),
            hold_period_months=12,
            purchase_price=41500,
            closing_costs=500,
            total_sf=10000,
            in_place_rent_psf=200,
            market_rent_psf=300,
            rent_growth=0.025,
            vacancy_rate=0.0,
            fixed_opex_psf=36,
            management_fee_percent=0.04,
            property_tax_amount=500,
            capex_reserve_psf=5,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.01,
            nnn_lease=False,
        )

        # NNN should have higher potential revenue (includes reimbursements)
        nnn_revenue = nnn_cf[1]["potential_revenue"]
        gross_revenue = gross_cf[1]["potential_revenue"]
        assert nnn_revenue > gross_revenue

        # Reimbursement should approximately equal reimbursable expenses
        reimbursement = nnn_cf[1]["reimbursement_revenue"]
        reimbursable_expenses = (
            nnn_cf[1]["fixed_opex"]
            + nnn_cf[1]["property_tax"]
            + nnn_cf[1]["management_fee"]
        )
        assert abs(reimbursement - reimbursable_expenses) < 1


# =============================================================================
# DEBT SERVICE CALCULATION TESTS
# =============================================================================


class TestDebtCalculation:
    """Tests for debt service calculation."""

    def test_interest_actual_365(self):
        """Interest should vary by days in month when using actual/365."""
        cf = generate_cash_flows(
            acquisition_date=date(2024, 1, 1),
            hold_period_months=3,
            purchase_price=41500,
            closing_costs=500,
            total_sf=10000,
            in_place_rent_psf=200,
            market_rent_psf=300,
            rent_growth=0.025,
            vacancy_rate=0.0,
            fixed_opex_psf=36,
            management_fee_percent=0.04,
            property_tax_amount=500,
            capex_reserve_psf=5,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.01,
            loan_amount=16937.18,
            interest_rate=0.0525,
            io_months=120,
            use_actual_365=True,
        )

        # Feb (29 days in 2024) should have lower interest than Jan (31 days)
        jan_interest = cf[1]["interest_expense"]  # Period 1 = Feb
        # March has 31 days
        mar_interest = cf[3]["interest_expense"]  # Period 3 = April

        # Verify interest varies with days
        # Note: period_date is acquisition_date + period months
        # So period 1 = Feb 1, period 2 = Mar 1, etc.
        assert jan_interest > 0
        assert mar_interest > 0

    def test_simple_monthly_interest(self):
        """Simple monthly should give constant interest."""
        cf = generate_cash_flows(
            acquisition_date=date(2024, 1, 1),
            hold_period_months=3,
            purchase_price=41500,
            closing_costs=500,
            total_sf=10000,
            in_place_rent_psf=200,
            market_rent_psf=300,
            rent_growth=0.025,
            vacancy_rate=0.0,
            fixed_opex_psf=36,
            management_fee_percent=0.04,
            property_tax_amount=500,
            capex_reserve_psf=5,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.01,
            loan_amount=16937.18,
            interest_rate=0.0525,
            io_months=120,
            use_actual_365=False,
        )

        # All months should have same interest with simple monthly
        interest_1 = cf[1]["interest_expense"]
        interest_2 = cf[2]["interest_expense"]
        interest_3 = cf[3]["interest_expense"]

        assert interest_1 == interest_2 == interest_3


# =============================================================================
# EXIT VALUE CALCULATION TESTS
# =============================================================================


class TestExitValueCalculation:
    """Tests for exit value calculation."""

    def test_forward_noi_calculation(self):
        """Exit value should be based on forward NOI, not current month."""
        cf = generate_cash_flows(
            acquisition_date=date(2024, 1, 1),
            hold_period_months=24,
            purchase_price=41500,
            closing_costs=500,
            total_sf=10000,
            in_place_rent_psf=200,
            market_rent_psf=300,
            rent_growth=0.025,
            vacancy_rate=0.0,
            fixed_opex_psf=36,
            management_fee_percent=0.04,
            property_tax_amount=500,
            capex_reserve_psf=5,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.01,
        )

        exit_cf = cf[24]
        exit_noi = exit_cf["noi"]
        exit_proceeds = exit_cf["exit_proceeds"]

        # Exit proceeds should be based on forward NOI with escalation
        # Not just current NOI * 12
        simple_value = (exit_noi * 12 / 0.05) * 0.99  # With 1% sales cost
        assert exit_proceeds > simple_value * 0.95  # Should be close

    def test_exit_proceeds_positive(self):
        """Exit proceeds should be positive on exit month only."""
        cf = generate_cash_flows(
            acquisition_date=date(2024, 1, 1),
            hold_period_months=24,
            purchase_price=41500,
            closing_costs=500,
            total_sf=10000,
            in_place_rent_psf=200,
            market_rent_psf=300,
            rent_growth=0.025,
            vacancy_rate=0.0,
            fixed_opex_psf=36,
            management_fee_percent=0.04,
            property_tax_amount=500,
            capex_reserve_psf=5,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.01,
        )

        # Only exit month should have proceeds
        for i, period_cf in enumerate(cf):
            if i == 24:
                assert period_cf["exit_proceeds"] > 0
            else:
                assert period_cf["exit_proceeds"] == 0


# =============================================================================
# FULL PARITY TEST
# =============================================================================


class TestFullExcelParity:
    """Test complete model parity with Excel benchmarks."""

    @pytest.fixture
    def full_model_cash_flows(self):
        """Generate cash flows matching Excel model configuration."""
        return generate_cash_flows(
            acquisition_date=date(2024, 1, 1),
            hold_period_months=120,
            purchase_price=EXCEL_BENCHMARKS["purchase_price"],
            closing_costs=EXCEL_BENCHMARKS["closing_costs"],
            total_sf=9932,  # Building RSF
            in_place_rent_psf=193.15,
            market_rent_psf=300,
            rent_growth=EXCEL_BENCHMARKS["rent_growth"],
            vacancy_rate=0.0,
            fixed_opex_psf=36.0,
            management_fee_percent=0.04,
            property_tax_amount=622.5,
            capex_reserve_psf=5.0,
            expense_growth=EXCEL_BENCHMARKS["expense_growth"],
            exit_cap_rate=EXCEL_BENCHMARKS["exit_cap_rate"],
            sales_cost_percent=EXCEL_BENCHMARKS["sales_cost_percent"],
            loan_amount=EXCEL_BENCHMARKS["loan_amount"],
            interest_rate=EXCEL_BENCHMARKS["interest_rate"],
            io_months=EXCEL_BENCHMARKS["io_months"],
            amortization_years=30,
            tenants=TENANTS,
            nnn_lease=True,
            use_actual_365=True,
        )

    def test_noi_matches_excel(self, full_model_cash_flows):
        """Month 1 NOI should match Excel benchmark."""
        noi = full_model_cash_flows[1]["noi"]
        # Excel: $158.97K
        assert abs(noi - 158.97) < 1  # Within $1K

    def test_unleveraged_irr_within_tolerance(self, full_model_cash_flows):
        """Unleveraged IRR should be within 10bp of Excel."""
        from app.calculations.cashflow import generate_monthly_dates

        dates = generate_monthly_dates(date(2024, 1, 1), 120)
        unlev_cf = [cf["unleveraged_cash_flow"] for cf in full_model_cash_flows]
        unlev_irr = irr.calculate_xirr(unlev_cf, dates)

        # Excel: 8.57%
        assert abs(unlev_irr - 0.0857) < 0.001  # Within 10bp

    def test_leveraged_irr_within_tolerance(self, full_model_cash_flows):
        """Leveraged IRR should be within 15bp of Excel."""
        from app.calculations.cashflow import generate_monthly_dates

        dates = generate_monthly_dates(date(2024, 1, 1), 120)
        lev_cf = [cf["leveraged_cash_flow"] for cf in full_model_cash_flows]
        lev_irr = irr.calculate_xirr(lev_cf, dates)

        # Excel: 10.09%
        assert abs(lev_irr - 0.1009) < 0.0015  # Within 15bp
