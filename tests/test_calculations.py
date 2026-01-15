"""
Tests for financial calculation engine.
"""

import pytest
from datetime import date
from app.calculations.irr import calculate_irr, calculate_xirr, calculate_npv
from app.calculations.amortization import calculate_payment, generate_amortization_schedule
from app.calculations.cashflow import generate_cash_flows, calculate_escalation_factor


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

    def test_calculate_npv(self):
        """Test NPV calculation."""
        cash_flows = [-100, 50, 50, 50]
        npv = calculate_npv(cash_flows, 0.10)
        # NPV should be positive since returns exceed cost
        assert npv > 0

    def test_irr_negative_returns(self):
        """Test IRR with negative return scenario."""
        cash_flows = [-100, 40, 40, 10]  # Total return < investment
        irr = calculate_irr(cash_flows)
        assert irr < 0  # Should be negative IRR


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
