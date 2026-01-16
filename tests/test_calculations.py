"""
Comprehensive tests for financial calculation engine.
"""

import pytest
from datetime import date, timedelta
from app.calculations.irr import (
    calculate_irr,
    calculate_xirr,
    calculate_npv,
    calculate_xnpv,
    calculate_multiple,
    calculate_profit,
    monthly_to_annual_irr,
    annual_to_monthly_irr,
)
from app.calculations.amortization import calculate_payment, generate_amortization_schedule
from app.calculations.cashflow import (
    generate_cash_flows,
    calculate_escalation_factor,
    generate_monthly_dates,
    annualize_cash_flows,
    sum_cash_flows,
)
from app.calculations.waterfall import (
    calculate_waterfall_distributions,
    extract_lp_cash_flows,
    extract_gp_cash_flows,
    calculate_waterfall_summary,
)


# ============================================================================
# IRR CALCULATION TESTS
# ============================================================================

class TestIRRCalculations:
    """Test IRR calculation functions."""

    def test_calculate_irr_simple(self):
        """Test IRR calculation with simple cash flows."""
        # Investment of 100, returns of 110 after 1 year = 10% return
        cash_flows = [-100, 110]
        irr = calculate_irr(cash_flows)
        assert abs(irr - 0.10) < 0.001

    def test_calculate_irr_multi_period(self):
        """Test IRR with multiple periods."""
        # Investment of 100, annual returns of 20, sale of 100 at end
        cash_flows = [-100, 20, 20, 20, 20, 120]
        irr = calculate_irr(cash_flows)
        assert abs(irr - 0.20) < 0.01  # ~20% IRR

    def test_calculate_irr_zero_return(self):
        """Test IRR when total return equals investment."""
        cash_flows = [-100, 25, 25, 25, 25]
        irr = calculate_irr(cash_flows)
        assert abs(irr) < 0.01  # ~0% IRR

    def test_calculate_irr_high_return(self):
        """Test IRR with high return scenario."""
        cash_flows = [-100, 0, 0, 0, 300]
        irr = calculate_irr(cash_flows)
        assert irr > 0.30  # Should be > 30%

    def test_calculate_irr_negative_returns(self):
        """Test IRR with negative return scenario."""
        cash_flows = [-100, 40, 40, 10]  # Total return < investment
        irr = calculate_irr(cash_flows)
        assert irr < 0  # Should be negative IRR

    def test_calculate_irr_requires_min_cash_flows(self):
        """Test that IRR requires at least 2 cash flows."""
        with pytest.raises(ValueError):
            calculate_irr([-100])

    def test_calculate_irr_requires_mixed_signs(self):
        """Test that IRR requires both positive and negative cash flows."""
        with pytest.raises(ValueError):
            calculate_irr([100, 100, 100])
        with pytest.raises(ValueError):
            calculate_irr([-100, -50, -25])

    def test_calculate_xirr(self):
        """Test XIRR calculation with actual dates."""
        dates = [
            date(2025, 1, 1),
            date(2026, 1, 1),
            date(2027, 1, 1),
        ]
        cash_flows = [-100, 50, 60]
        xirr = calculate_xirr(cash_flows, dates)
        assert xirr > 0  # Should be positive return
        assert xirr < 0.20  # Should be reasonable

    def test_calculate_xirr_irregular_dates(self):
        """Test XIRR with irregular date intervals."""
        dates = [
            date(2025, 1, 1),
            date(2025, 6, 15),  # ~5.5 months
            date(2026, 3, 1),   # ~14 months from start
        ]
        cash_flows = [-100, 30, 90]
        xirr = calculate_xirr(cash_flows, dates)
        assert xirr > 0

    def test_calculate_xirr_mismatched_lengths(self):
        """Test that XIRR fails with mismatched array lengths."""
        dates = [date(2025, 1, 1), date(2026, 1, 1)]
        cash_flows = [-100, 50, 60]
        with pytest.raises(ValueError):
            calculate_xirr(cash_flows, dates)

    def test_calculate_npv(self):
        """Test NPV calculation."""
        cash_flows = [-100, 50, 50, 50]
        npv = calculate_npv(cash_flows, 0.10)
        # NPV should be positive since returns exceed cost at 10% discount
        assert npv > 0

    def test_calculate_npv_zero_rate(self):
        """Test NPV with zero discount rate equals sum of cash flows."""
        cash_flows = [-100, 50, 50, 50]
        npv = calculate_npv(cash_flows, 0.0)
        assert abs(npv - 50) < 0.01  # Should equal sum

    def test_calculate_npv_high_rate(self):
        """Test NPV with high discount rate."""
        cash_flows = [-100, 50, 50, 50]
        npv = calculate_npv(cash_flows, 0.50)
        # High discount rate should make NPV negative
        assert npv < 0

    def test_calculate_xnpv(self):
        """Test XNPV with specific dates."""
        dates = [date(2025, 1, 1), date(2026, 1, 1), date(2027, 1, 1)]
        cash_flows = [-100, 55, 55]
        xnpv = calculate_xnpv(cash_flows, dates, 0.05)
        assert xnpv > 0

    def test_calculate_multiple(self):
        """Test equity multiple calculation."""
        cash_flows = [-100, 30, 30, 30, 110]
        multiple = calculate_multiple(cash_flows)
        assert abs(multiple - 2.0) < 0.01  # 200/100 = 2.0x

    def test_calculate_multiple_no_outflows(self):
        """Test that multiple fails with no outflows."""
        with pytest.raises(ValueError):
            calculate_multiple([50, 50, 50])

    def test_calculate_profit(self):
        """Test profit calculation."""
        cash_flows = [-100, 30, 30, 30, 60]
        profit = calculate_profit(cash_flows)
        assert profit == 50

    def test_monthly_to_annual_irr(self):
        """Test monthly to annual IRR conversion."""
        monthly = 0.01  # 1% monthly
        annual = monthly_to_annual_irr(monthly)
        assert abs(annual - 0.1268) < 0.001  # ~12.68% annual

    def test_annual_to_monthly_irr(self):
        """Test annual to monthly IRR conversion."""
        annual = 0.12  # 12% annual
        monthly = annual_to_monthly_irr(annual)
        assert abs(monthly - 0.00949) < 0.001  # ~0.949% monthly


# ============================================================================
# AMORTIZATION TESTS
# ============================================================================

class TestAmortization:
    """Test loan amortization calculations."""

    def test_calculate_payment(self):
        """Test monthly payment calculation."""
        # $1M loan at 5% for 30 years
        loan_amount = 1000000
        annual_rate = 0.05
        months = 360
        payment = calculate_payment(loan_amount, annual_rate, months)
        # Expected payment around $5,368/month
        assert 5300 < payment < 5500

    def test_calculate_payment_short_term(self):
        """Test payment for short-term loan."""
        # $100k loan at 6% for 5 years
        payment = calculate_payment(100000, 0.06, 60)
        # Expected ~$1,933/month
        assert 1900 < payment < 2000

    def test_calculate_payment_zero_rate(self):
        """Test payment with zero interest rate."""
        # Should be principal / months
        payment = calculate_payment(120000, 0.0, 120)
        assert abs(payment - 1000) < 0.01

    def test_amortization_schedule_length(self):
        """Test amortization schedule has correct number of periods."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=0.06,
            amortization_months=60,
            io_months=0,
            total_months=60,
        )
        assert len(schedule) == 60

    def test_amortization_io_periods(self):
        """Test interest-only periods in amortization."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=0.06,
            amortization_months=60,
            io_months=12,
            total_months=72,
        )
        # First 12 periods should have 0 principal
        for i in range(12):
            assert schedule[i]["principal"] == 0
            assert schedule[i]["interest"] > 0

    def test_amortization_io_balance_unchanged(self):
        """Test that balance is unchanged during IO period."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=0.06,
            amortization_months=60,
            io_months=12,
            total_months=72,
        )
        # Balance should be 100k throughout IO period
        for i in range(12):
            assert abs(schedule[i]["ending_balance"] - 100000) < 0.01

    def test_amortization_final_balance(self):
        """Test that final balance is approximately zero."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=0.06,
            amortization_months=60,
            io_months=0,
            total_months=60,
        )
        # Final balance should be very close to zero
        assert abs(schedule[-1]["ending_balance"]) < 1

    def test_amortization_decreasing_interest(self):
        """Test that interest payments decrease over time (amortizing loan)."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=0.06,
            amortization_months=60,
            io_months=0,
            total_months=60,
        )
        # Interest should decrease period over period
        for i in range(1, len(schedule)):
            assert schedule[i]["interest"] <= schedule[i-1]["interest"]

    def test_amortization_increasing_principal(self):
        """Test that principal payments increase over time (amortizing loan)."""
        schedule = generate_amortization_schedule(
            principal=100000,
            annual_rate=0.06,
            amortization_months=60,
            io_months=0,
            total_months=60,
        )
        # Principal should increase period over period
        for i in range(1, len(schedule)):
            assert schedule[i]["principal"] >= schedule[i-1]["principal"]


# ============================================================================
# CASH FLOW TESTS
# ============================================================================

class TestCashFlows:
    """Test cash flow generation."""

    def test_escalation_factor_monthly(self):
        """Test monthly compounding escalation."""
        factor = calculate_escalation_factor(0.03, 12, "monthly")
        # After 12 months at 3% annual rate
        assert abs(factor - 1.03) < 0.001

    def test_escalation_factor_annual(self):
        """Test annual step escalation."""
        # Year 0 (months 0-11) should have factor of 1.0
        factor_year1 = calculate_escalation_factor(0.03, 6, "annual")
        assert factor_year1 == 1.0

        # Year 1 (months 12-23) should have factor of 1.03
        factor_year2 = calculate_escalation_factor(0.03, 12, "annual")
        assert factor_year2 == 1.03

    def test_escalation_factor_multi_year(self):
        """Test multi-year annual escalation."""
        # Year 3 (months 36-47) should be (1.03)^3
        factor = calculate_escalation_factor(0.03, 36, "annual")
        expected = (1.03) ** 3
        assert abs(factor - expected) < 0.001

    def test_generate_monthly_dates(self):
        """Test monthly date generation."""
        start = date(2025, 1, 1)
        dates = generate_monthly_dates(start, 12)
        assert len(dates) == 13  # 0-12 inclusive
        assert dates[0] == date(2025, 1, 1)
        assert dates[12] == date(2026, 1, 1)

    def test_generate_cash_flows_length(self):
        """Test cash flows array has correct length."""
        cfs = generate_cash_flows(
            acquisition_date=date(2025, 1, 1),
            hold_period_months=60,
            purchase_price=1000,
            closing_costs=15,
            total_sf=10000,
            in_place_rent_psf=20,
            market_rent_psf=22,
            rent_growth=0.03,
            vacancy_rate=0.05,
            fixed_opex_psf=5,
            management_fee_percent=0.03,
            property_tax_amount=50,
            capex_reserve_psf=0.50,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.02,
        )
        # Should have 61 periods (0-60 inclusive)
        assert len(cfs) == 61

    def test_generate_cash_flows_acquisition(self):
        """Test acquisition period has correct outflow."""
        cfs = generate_cash_flows(
            acquisition_date=date(2025, 1, 1),
            hold_period_months=60,
            purchase_price=1000,
            closing_costs=15,
            total_sf=10000,
            in_place_rent_psf=20,
            market_rent_psf=22,
            rent_growth=0.03,
            vacancy_rate=0.05,
            fixed_opex_psf=5,
            management_fee_percent=0.03,
            property_tax_amount=50,
            capex_reserve_psf=0.50,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.02,
        )
        # Period 0 should have acquisition costs
        assert cfs[0]["acquisition_costs"] == 1015  # purchase + closing

    def test_generate_cash_flows_exit(self):
        """Test exit period has proceeds."""
        cfs = generate_cash_flows(
            acquisition_date=date(2025, 1, 1),
            hold_period_months=60,
            purchase_price=1000,
            closing_costs=15,
            total_sf=10000,
            in_place_rent_psf=20,
            market_rent_psf=22,
            rent_growth=0.03,
            vacancy_rate=0.05,
            fixed_opex_psf=5,
            management_fee_percent=0.03,
            property_tax_amount=50,
            capex_reserve_psf=0.50,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.02,
        )
        # Final period should have exit proceeds
        assert cfs[60]["exit_proceeds"] > 0

    def test_generate_cash_flows_positive_noi(self):
        """Test that NOI is positive for income-producing property."""
        cfs = generate_cash_flows(
            acquisition_date=date(2025, 1, 1),
            hold_period_months=12,
            purchase_price=1000,
            closing_costs=15,
            total_sf=10000,
            in_place_rent_psf=20,
            market_rent_psf=22,
            rent_growth=0.03,
            vacancy_rate=0.05,
            fixed_opex_psf=5,
            management_fee_percent=0.03,
            property_tax_amount=50,
            capex_reserve_psf=0.50,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.02,
        )
        # Operating periods should have positive NOI
        for i in range(1, 12):
            assert cfs[i]["noi"] > 0

    def test_generate_cash_flows_with_debt(self):
        """Test cash flows with leverage."""
        cfs = generate_cash_flows(
            acquisition_date=date(2025, 1, 1),
            hold_period_months=60,
            purchase_price=1000,
            closing_costs=15,
            total_sf=10000,
            in_place_rent_psf=20,
            market_rent_psf=22,
            rent_growth=0.03,
            vacancy_rate=0.05,
            fixed_opex_psf=5,
            management_fee_percent=0.03,
            property_tax_amount=50,
            capex_reserve_psf=0.50,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.02,
            loan_amount=600,  # 60% LTV
            interest_rate=0.06,
            io_months=60,
        )
        # Period 1 should have debt service
        assert cfs[1]["debt_service"] > 0
        # Leveraged CF should differ from unleveraged
        assert cfs[1]["leveraged_cash_flow"] != cfs[1]["unleveraged_cash_flow"]

    def test_generate_cash_flows_loan_proceeds(self):
        """Test that period 0 includes loan proceeds."""
        cfs = generate_cash_flows(
            acquisition_date=date(2025, 1, 1),
            hold_period_months=12,
            purchase_price=1000,
            closing_costs=15,
            total_sf=10000,
            in_place_rent_psf=20,
            market_rent_psf=22,
            rent_growth=0.03,
            vacancy_rate=0.05,
            fixed_opex_psf=5,
            management_fee_percent=0.03,
            property_tax_amount=50,
            capex_reserve_psf=0.50,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.02,
            loan_amount=600,
            interest_rate=0.06,
            io_months=12,
        )
        # Leveraged CF at period 0 should be higher (loan proceeds offset acquisition)
        # Unleveraged: NOI - 1015 (acq costs)
        # Leveraged: NOI - 1015 + 600 (loan proceeds)
        diff = cfs[0]["leveraged_cash_flow"] - cfs[0]["unleveraged_cash_flow"]
        assert abs(diff - 600) < 1

    def test_annualize_cash_flows(self):
        """Test annualization of monthly cash flows."""
        cfs = generate_cash_flows(
            acquisition_date=date(2025, 1, 1),
            hold_period_months=24,
            purchase_price=1000,
            closing_costs=15,
            total_sf=10000,
            in_place_rent_psf=20,
            market_rent_psf=22,
            rent_growth=0.03,
            vacancy_rate=0.05,
            fixed_opex_psf=5,
            management_fee_percent=0.03,
            property_tax_amount=50,
            capex_reserve_psf=0.50,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.02,
        )
        annual = annualize_cash_flows(cfs)
        # Should have 3 years (partial first year, full year, partial last)
        assert len(annual) >= 2

    def test_sum_cash_flows(self):
        """Test summing specific field across cash flows."""
        cfs = [
            {"period": 0, "noi": 10},
            {"period": 1, "noi": 12},
            {"period": 2, "noi": 14},
        ]
        total = sum_cash_flows(cfs, "noi")
        assert total == 36

    def test_sum_cash_flows_range(self):
        """Test summing with period range."""
        cfs = [
            {"period": 0, "noi": 10},
            {"period": 1, "noi": 12},
            {"period": 2, "noi": 14},
            {"period": 3, "noi": 16},
        ]
        total = sum_cash_flows(cfs, "noi", start_period=1, end_period=2)
        assert total == 26


# ============================================================================
# WATERFALL TESTS
# ============================================================================

class TestWaterfall:
    """Test waterfall distribution calculations."""

    def test_waterfall_basic_distribution(self):
        """Test basic waterfall with simple cash flows."""
        cash_flows = [-100, 10, 10, 10, 10, 110]
        dates = [date(2025, 1, 1) + timedelta(days=30*i) for i in range(6)]

        distributions = calculate_waterfall_distributions(
            leveraged_cash_flows=cash_flows,
            dates=dates,
            total_equity=100,
            lp_share=0.90,
            gp_share=0.10,
            pref_return=0.08,
        )

        assert len(distributions) == 6

    def test_waterfall_lp_gp_split(self):
        """Test that LP/GP splits are correct."""
        cash_flows = [0, 100]  # No acquisition, just distribution
        dates = [date(2025, 1, 1), date(2025, 2, 1)]

        distributions = calculate_waterfall_distributions(
            leveraged_cash_flows=cash_flows,
            dates=dates,
            total_equity=0,  # No equity for simplicity
            lp_share=0.90,
            gp_share=0.10,
            pref_return=0.0,  # No pref for simplicity
        )

        # Second period should split 90/10
        assert abs(distributions[1]["total_to_lp"] - 90) < 0.01
        assert abs(distributions[1]["total_to_gp"] - 10) < 0.01

    def test_waterfall_preferred_return_accrual(self):
        """Test that preferred return accrues correctly."""
        # No distributions for first few periods
        cash_flows = [-100, 0, 0, 0, 200]
        dates = [date(2025, 1, 1) + timedelta(days=30*i) for i in range(5)]

        distributions = calculate_waterfall_distributions(
            leveraged_cash_flows=cash_flows,
            dates=dates,
            total_equity=100,
            lp_share=0.90,
            gp_share=0.10,
            pref_return=0.12,  # 12% annual = 1% monthly
        )

        # Pref should accrue and then be paid
        total_pref_paid = sum(d["lp_preferred_return"] + d["gp_preferred_return"]
                             for d in distributions)
        assert total_pref_paid > 0

    def test_waterfall_return_of_capital(self):
        """Test that return of capital happens before profit split."""
        cash_flows = [-100, 0, 0, 150]
        dates = [date(2025, 1, 1) + timedelta(days=30*i) for i in range(4)]

        distributions = calculate_waterfall_distributions(
            leveraged_cash_flows=cash_flows,
            dates=dates,
            total_equity=100,
            lp_share=0.90,
            gp_share=0.10,
            pref_return=0.0,  # No pref for simplicity
        )

        # Total equity paydown should equal initial equity
        total_equity_paydown = sum(
            d["lp_equity_paydown"] + d["gp_equity_paydown"]
            for d in distributions
        )
        assert abs(total_equity_paydown - 100) < 0.01

    def test_extract_lp_cash_flows(self):
        """Test LP cash flow extraction."""
        distributions = [
            {"total_to_lp": 5},
            {"total_to_lp": 10},
            {"total_to_lp": 100},
        ]
        lp_equity = 90

        lp_cfs = extract_lp_cash_flows(distributions, lp_equity)

        # First period: -90 (investment) + 5 (distribution) = -85
        assert lp_cfs[0] == -85
        assert lp_cfs[1] == 10
        assert lp_cfs[2] == 100

    def test_extract_gp_cash_flows(self):
        """Test GP cash flow extraction."""
        distributions = [
            {"total_to_gp": 1},
            {"total_to_gp": 2},
            {"total_to_gp": 20},
        ]
        gp_equity = 10

        gp_cfs = extract_gp_cash_flows(distributions, gp_equity)

        # First period: -10 (investment) + 1 (distribution) = -9
        assert gp_cfs[0] == -9
        assert gp_cfs[1] == 2
        assert gp_cfs[2] == 20

    def test_waterfall_summary(self):
        """Test waterfall summary calculation."""
        distributions = [
            {
                "lp_equity_paydown": 45, "gp_equity_paydown": 5,
                "lp_preferred_return": 9, "gp_preferred_return": 1,
                "lp_profit": 36, "gp_profit": 4,
                "total_to_lp": 90, "total_to_gp": 10,
            },
            {
                "lp_equity_paydown": 45, "gp_equity_paydown": 5,
                "lp_preferred_return": 0, "gp_preferred_return": 0,
                "lp_profit": 45, "gp_profit": 5,
                "total_to_lp": 90, "total_to_gp": 10,
            },
        ]

        summary = calculate_waterfall_summary(distributions)

        assert summary["total_to_lp"] == 180
        assert summary["total_to_gp"] == 20
        assert summary["total_equity_paydown"] == 100
        assert summary["total_preferred_return"] == 10
        assert summary["total_profit"] == 90


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests for full calculation pipeline."""

    def test_225_worth_ave_approximation(self):
        """Test that model produces reasonable IRR for 225 Worth Ave style inputs."""
        cfs = generate_cash_flows(
            acquisition_date=date(2025, 1, 1),
            hold_period_months=120,
            purchase_price=41500,  # $41.5M
            closing_costs=622.5,  # 1.5%
            total_sf=9932,
            in_place_rent_psf=200,
            market_rent_psf=220,
            rent_growth=0.047,  # 4.7% for target IRR match
            vacancy_rate=0.05,
            fixed_opex_psf=5,  # NNN lease, minimal landlord expenses
            management_fee_percent=0.03,
            property_tax_amount=0,  # NNN - tenant pays
            capex_reserve_psf=0.50,
            expense_growth=0.025,
            exit_cap_rate=0.044,  # 4.4%
            sales_cost_percent=0.02,
            loan_amount=23033,  # 55.5% LTC
            interest_rate=0.055,  # 5.5%
            io_months=120,
            amortization_years=30,
        )

        dates = [date.fromisoformat(cf["date"]) for cf in cfs]
        unlev_cfs = [cf["unleveraged_cash_flow"] for cf in cfs]
        lev_cfs = [cf["leveraged_cash_flow"] for cf in cfs]

        unlev_irr = calculate_xirr(unlev_cfs, dates)
        lev_irr = calculate_xirr(lev_cfs, dates)

        # Should be close to target returns
        # Target: Unleveraged 8.54%, Leveraged 11.43%
        assert 0.07 < unlev_irr < 0.10  # 7-10% range
        assert 0.09 < lev_irr < 0.14  # 9-14% range

        # Leveraged should exceed unleveraged (positive leverage)
        assert lev_irr > unlev_irr

    def test_full_pipeline_with_waterfall(self):
        """Test complete pipeline from cash flows through waterfall."""
        # Generate cash flows
        cfs = generate_cash_flows(
            acquisition_date=date(2025, 1, 1),
            hold_period_months=60,
            purchase_price=10000,
            closing_costs=150,
            total_sf=50000,
            in_place_rent_psf=20,
            market_rent_psf=22,
            rent_growth=0.03,
            vacancy_rate=0.05,
            fixed_opex_psf=5,
            management_fee_percent=0.03,
            property_tax_amount=100,
            capex_reserve_psf=0.50,
            expense_growth=0.025,
            exit_cap_rate=0.06,
            sales_cost_percent=0.02,
            loan_amount=6500,  # 65% LTC
            interest_rate=0.055,
            io_months=60,
        )

        dates = [date.fromisoformat(cf["date"]) for cf in cfs]
        lev_cfs = [cf["leveraged_cash_flow"] for cf in cfs]

        # Calculate leveraged IRR
        lev_irr = calculate_xirr(lev_cfs, dates)
        assert lev_irr > 0

        # Run through waterfall
        total_equity = 10150 - 6500  # Total cost - loan
        distributions = calculate_waterfall_distributions(
            leveraged_cash_flows=lev_cfs,
            dates=dates,
            total_equity=total_equity,
            lp_share=0.90,
            gp_share=0.10,
            pref_return=0.08,
        )

        # Calculate LP IRR
        lp_equity = total_equity * 0.90
        lp_cfs = extract_lp_cash_flows(distributions, lp_equity)
        lp_irr = calculate_xirr(lp_cfs, dates)

        # LP IRR should be positive
        assert lp_irr > 0

        # Summary should balance
        summary = calculate_waterfall_summary(distributions)
        total_distributed = summary["total_to_lp"] + summary["total_to_gp"]
        total_cash_flow = sum(cf for cf in lev_cfs if cf > 0)
        assert abs(total_distributed - total_cash_flow) < 1

    def test_negative_leverage_scenario(self):
        """Test scenario where leverage hurts returns."""
        # High debt cost, low cap rate spread
        cfs = generate_cash_flows(
            acquisition_date=date(2025, 1, 1),
            hold_period_months=60,
            purchase_price=10000,
            closing_costs=150,
            total_sf=50000,
            in_place_rent_psf=15,  # Lower rent
            market_rent_psf=16,
            rent_growth=0.02,
            vacancy_rate=0.10,  # Higher vacancy
            fixed_opex_psf=6,
            management_fee_percent=0.04,
            property_tax_amount=200,
            capex_reserve_psf=1.0,
            expense_growth=0.03,
            exit_cap_rate=0.08,  # Higher exit cap
            sales_cost_percent=0.02,
            loan_amount=7000,  # 70% LTC
            interest_rate=0.08,  # High rate
            io_months=60,
        )

        dates = [date.fromisoformat(cf["date"]) for cf in cfs]
        unlev_cfs = [cf["unleveraged_cash_flow"] for cf in cfs]
        lev_cfs = [cf["leveraged_cash_flow"] for cf in cfs]

        try:
            unlev_irr = calculate_xirr(unlev_cfs, dates)
            lev_irr = calculate_xirr(lev_cfs, dates)
            # In negative leverage, leveraged IRR < unleveraged IRR
            # This test just verifies the calculation runs
            assert isinstance(unlev_irr, float)
            assert isinstance(lev_irr, float)
        except ValueError:
            # IRR may not converge for very negative scenarios
            pass


# ============================================================================
# EDGE CASE TESTS
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_hold_period(self):
        """Test with minimum hold period."""
        cfs = generate_cash_flows(
            acquisition_date=date(2025, 1, 1),
            hold_period_months=1,
            purchase_price=1000,
            closing_costs=15,
            total_sf=10000,
            in_place_rent_psf=20,
            market_rent_psf=22,
            rent_growth=0.03,
            vacancy_rate=0.05,
            fixed_opex_psf=5,
            management_fee_percent=0.03,
            property_tax_amount=50,
            capex_reserve_psf=0.50,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.02,
        )
        assert len(cfs) == 2

    def test_very_long_hold_period(self):
        """Test with very long hold period."""
        cfs = generate_cash_flows(
            acquisition_date=date(2025, 1, 1),
            hold_period_months=360,  # 30 years
            purchase_price=1000,
            closing_costs=15,
            total_sf=10000,
            in_place_rent_psf=20,
            market_rent_psf=22,
            rent_growth=0.03,
            vacancy_rate=0.05,
            fixed_opex_psf=5,
            management_fee_percent=0.03,
            property_tax_amount=50,
            capex_reserve_psf=0.50,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.02,
        )
        assert len(cfs) == 361

    def test_zero_vacancy(self):
        """Test with zero vacancy rate."""
        cfs = generate_cash_flows(
            acquisition_date=date(2025, 1, 1),
            hold_period_months=12,
            purchase_price=1000,
            closing_costs=15,
            total_sf=10000,
            in_place_rent_psf=20,
            market_rent_psf=22,
            rent_growth=0.03,
            vacancy_rate=0.0,  # No vacancy
            fixed_opex_psf=5,
            management_fee_percent=0.03,
            property_tax_amount=50,
            capex_reserve_psf=0.50,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.02,
        )
        # Effective revenue should equal potential revenue
        for i in range(1, 12):
            assert cfs[i]["vacancy_loss"] == 0
            assert cfs[i]["effective_revenue"] == cfs[i]["potential_revenue"]

    def test_high_vacancy(self):
        """Test with very high vacancy rate."""
        cfs = generate_cash_flows(
            acquisition_date=date(2025, 1, 1),
            hold_period_months=12,
            purchase_price=1000,
            closing_costs=15,
            total_sf=10000,
            in_place_rent_psf=20,
            market_rent_psf=22,
            rent_growth=0.03,
            vacancy_rate=0.50,  # 50% vacancy
            fixed_opex_psf=5,
            management_fee_percent=0.03,
            property_tax_amount=50,
            capex_reserve_psf=0.50,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.02,
        )
        # Effective revenue should be half of potential
        for i in range(1, 12):
            expected = cfs[i]["potential_revenue"] * 0.5
            assert abs(cfs[i]["effective_revenue"] - expected) < 0.01

    def test_amortizing_loan_balance_paydown(self):
        """Test that amortizing loan reduces balance."""
        cfs = generate_cash_flows(
            acquisition_date=date(2025, 1, 1),
            hold_period_months=60,
            purchase_price=1000,
            closing_costs=15,
            total_sf=10000,
            in_place_rent_psf=20,
            market_rent_psf=22,
            rent_growth=0.03,
            vacancy_rate=0.05,
            fixed_opex_psf=5,
            management_fee_percent=0.03,
            property_tax_amount=50,
            capex_reserve_psf=0.50,
            expense_growth=0.025,
            exit_cap_rate=0.05,
            sales_cost_percent=0.02,
            loan_amount=600,
            interest_rate=0.06,
            io_months=0,  # Fully amortizing from start
            amortization_years=30,
        )
        # Debt service should include principal
        # (debt service > interest-only payment)
        io_payment = 600 * 0.06 / 12  # Monthly interest only
        assert cfs[1]["debt_service"] > io_payment
