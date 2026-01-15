"""
Cash Flow Calculations

Generates monthly cash flow projections for real estate investments.
"""

from typing import List, Dict, Optional
from datetime import date
from dateutil.relativedelta import relativedelta

from app.calculations.amortization import calculate_payment


def generate_monthly_dates(start_date: date, num_months: int) -> List[date]:
    """Generate array of monthly dates."""
    return [start_date + relativedelta(months=i) for i in range(num_months + 1)]


def calculate_escalation_factor(
    annual_rate: float, period: int, frequency: str = "monthly"
) -> float:
    """
    Calculate escalation factor for a given period.

    Args:
        annual_rate: Annual escalation rate as decimal
        period: Period number (0-based)
        frequency: How often escalation applies ('monthly' or 'annual')
    """
    if frequency == "monthly":
        # Compound monthly
        return (1 + annual_rate) ** (period / 12)
    else:
        # Step up annually
        years = period // 12
        return (1 + annual_rate) ** years


def generate_cash_flows(
    acquisition_date: date,
    hold_period_months: int,
    purchase_price: float,
    closing_costs: float,
    total_sf: float,
    in_place_rent_psf: float,
    market_rent_psf: float,
    rent_growth: float,
    vacancy_rate: float,
    fixed_opex_psf: float,
    management_fee_percent: float,
    property_tax_amount: float,
    capex_reserve_psf: float,
    expense_growth: float,
    exit_cap_rate: float,
    sales_cost_percent: float,
    loan_amount: Optional[float] = None,
    interest_rate: float = 0.05,
    io_months: int = 120,
    amortization_years: int = 30,
) -> List[Dict]:
    """
    Generate monthly cash flow projections.

    All monetary values in thousands ($000s).
    """
    cash_flows = []

    for period in range(hold_period_months + 1):
        period_date = acquisition_date + relativedelta(months=period)

        # === REVENUE ===
        # Rent with escalation
        rent_escalation = calculate_escalation_factor(rent_growth, period, "monthly")
        monthly_rent = (total_sf * in_place_rent_psf * rent_escalation) / 12 / 1000

        # Potential revenue
        potential_revenue = monthly_rent

        # Vacancy and collection loss
        vacancy_loss = -potential_revenue * vacancy_rate
        effective_revenue = potential_revenue + vacancy_loss

        # === EXPENSES ===
        expense_escalation = calculate_escalation_factor(expense_growth, period, "annual")

        fixed_opex = (total_sf * fixed_opex_psf * expense_escalation) / 12 / 1000
        mgmt_fee = effective_revenue * management_fee_percent
        prop_tax = (property_tax_amount * expense_escalation) / 12 / 1000  # Convert to $000s
        capex = (total_sf * capex_reserve_psf * expense_escalation) / 12 / 1000

        total_expenses = fixed_opex + mgmt_fee + prop_tax + capex

        # === NOI ===
        noi = effective_revenue - total_expenses

        # === CAPITAL EVENTS ===
        acquisition_costs = 0.0
        exit_proceeds = 0.0

        if period == 0:
            acquisition_costs = purchase_price + closing_costs

        if period == hold_period_months:
            # Calculate exit value based on forward NOI
            forward_noi = noi * 12  # Simplified: assume current NOI x 12
            gross_value = forward_noi / exit_cap_rate if exit_cap_rate > 0 else 0
            sales_costs = gross_value * sales_cost_percent
            exit_proceeds = gross_value - sales_costs

        # === DEBT SERVICE ===
        debt_service = 0.0
        interest_expense = 0.0
        principal_payment = 0.0

        if loan_amount and loan_amount > 0 and period > 0:
            monthly_rate = interest_rate / 12

            if period <= io_months:
                # Interest-only (loan_amount already in $000s)
                interest_expense = loan_amount * monthly_rate
                debt_service = interest_expense
            else:
                # Amortizing (loan_amount already in $000s)
                amort_months = amortization_years * 12
                payment = calculate_payment(loan_amount, interest_rate, amort_months)
                interest_expense = loan_amount * monthly_rate
                principal_payment = payment - interest_expense
                debt_service = payment

        # === CASH FLOWS ===
        unleveraged_cf = noi - acquisition_costs + exit_proceeds
        leveraged_cf = unleveraged_cf - debt_service

        # First period: add loan proceeds if applicable (loan_amount already in $000s)
        if period == 0 and loan_amount and loan_amount > 0:
            leveraged_cf += loan_amount  # Loan proceeds offset acquisition

        # Exit period: pay off loan balance (loan_amount already in $000s)
        if period == hold_period_months and loan_amount and loan_amount > 0:
            # Simplified: assume full balance outstanding at exit
            loan_payoff = loan_amount
            leveraged_cf -= loan_payoff

        cash_flows.append(
            {
                "period": period,
                "date": period_date.isoformat(),
                "potential_revenue": round(potential_revenue, 2),
                "vacancy_loss": round(vacancy_loss, 2),
                "effective_revenue": round(effective_revenue, 2),
                "fixed_opex": round(fixed_opex, 2),
                "management_fee": round(mgmt_fee, 2),
                "property_tax": round(prop_tax, 2),
                "capex_reserve": round(capex, 2),
                "total_expenses": round(total_expenses, 2),
                "noi": round(noi, 2),
                "acquisition_costs": round(acquisition_costs, 2),
                "exit_proceeds": round(exit_proceeds, 2),
                "debt_service": round(debt_service, 2),
                "unleveraged_cash_flow": round(unleveraged_cf, 2),
                "leveraged_cash_flow": round(leveraged_cf, 2),
            }
        )

    return cash_flows


def annualize_cash_flows(monthly_cash_flows: List[Dict]) -> List[Dict]:
    """
    Convert monthly cash flows to annual totals.
    """
    annual_data = []
    numeric_fields = [
        "potential_revenue",
        "effective_revenue",
        "total_expenses",
        "noi",
        "debt_service",
        "unleveraged_cash_flow",
        "leveraged_cash_flow",
    ]

    current_year = 1
    year_totals = {"year": current_year}
    for field in numeric_fields:
        year_totals[field] = 0.0

    for cf in monthly_cash_flows:
        cf_year = (cf["period"] // 12) + 1

        if cf_year != current_year:
            annual_data.append(year_totals)
            current_year = cf_year
            year_totals = {"year": current_year}
            for field in numeric_fields:
                year_totals[field] = 0.0

        for field in numeric_fields:
            year_totals[field] += cf.get(field, 0.0)

    # Push final year
    annual_data.append(year_totals)

    # Round all values
    for year in annual_data:
        for key in year:
            if key != "year" and isinstance(year[key], float):
                year[key] = round(year[key], 2)

    return annual_data


def sum_cash_flows(
    cash_flows: List[Dict], field: str, start_period: int = 0, end_period: int = None
) -> float:
    """Sum a specific field across cash flows for a range of periods."""
    if end_period is None:
        end_period = len(cash_flows) - 1

    return sum(
        cf.get(field, 0.0)
        for cf in cash_flows
        if start_period <= cf["period"] <= end_period
    )
