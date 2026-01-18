"""
Cash Flow Calculations

Generates monthly cash flow projections for real estate investments.
"""

from typing import List, Dict, Optional
from datetime import date
from dateutil.relativedelta import relativedelta
from dataclasses import dataclass

from app.calculations.amortization import calculate_payment


@dataclass
class Tenant:
    """Represents a single tenant in the rent roll."""

    name: str
    rsf: float  # Rentable square feet
    in_place_rent_psf: float  # Current rent per SF per year
    market_rent_psf: float  # Market rent per SF per year
    lease_end_month: int  # Month number when lease expires (0-indexed)


def calculate_tenant_rent(
    tenant: Tenant,
    period: int,
    rent_growth: float,
) -> float:
    """
    Calculate monthly rent for a single tenant.

    Uses in-place rent until lease expiration, then rolls to market rent.
    Applies monthly escalation factor.

    Args:
        tenant: Tenant data
        period: Month number (0 = acquisition month)
        rent_growth: Annual rent escalation rate (e.g., 0.025 for 2.5%)

    Returns:
        Monthly rent in $000s
    """
    # Determine which rent rate to use
    if period <= tenant.lease_end_month:
        # Still in lease term - use in-place rent
        rent_psf = tenant.in_place_rent_psf
    else:
        # Lease expired - roll to market rent
        rent_psf = tenant.market_rent_psf

    # Apply escalation factor (monthly compounding)
    escalation_factor = (1 + rent_growth) ** (period / 12)

    # Calculate monthly rent in $000s
    monthly_rent = (tenant.rsf * rent_psf * escalation_factor) / 12 / 1000

    return monthly_rent


def calculate_total_tenant_rent(
    tenants: List[Tenant],
    period: int,
    rent_growth: float,
) -> float:
    """
    Calculate total monthly rent from all tenants.

    Args:
        tenants: List of tenant data
        period: Month number
        rent_growth: Annual rent escalation rate

    Returns:
        Total monthly rent in $000s
    """
    return sum(
        calculate_tenant_rent(tenant, period, rent_growth) for tenant in tenants
    )


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


def calculate_days_in_month(period_date: date) -> int:
    """Calculate the number of days in a given month."""
    next_month = period_date + relativedelta(months=1)
    return (next_month - period_date).days


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
    tenants: Optional[List[Tenant]] = None,
    nnn_lease: bool = True,
    use_actual_365: bool = True,
) -> List[Dict]:
    """
    Generate monthly cash flow projections.

    All monetary values in thousands ($000s).

    If tenants list is provided, uses tenant-by-tenant rent calculation with
    lease expiration logic. Otherwise uses uniform rent calculation with
    weighted average rates.

    Args:
        tenants: Optional list of Tenant objects for per-tenant calculation
        nnn_lease: If True, adds expense reimbursements to revenue (NNN lease structure)
        use_actual_365: If True, uses actual/365 day count for interest calculation
    """
    cash_flows = []

    # First pass: calculate all periods to get forward NOI for exit
    period_data = []

    for period in range(hold_period_months + 1):
        period_date = acquisition_date + relativedelta(months=period)

        # === REVENUE ===
        if tenants and len(tenants) > 0:
            # Tenant-by-tenant calculation with lease expiry logic
            base_rent = calculate_total_tenant_rent(tenants, period, rent_growth)
        else:
            # Fallback: uniform calculation using average rent
            rent_escalation = calculate_escalation_factor(rent_growth, period, "monthly")
            base_rent = (total_sf * in_place_rent_psf * rent_escalation) / 12 / 1000

        # === Month 0 has no operating revenue in Excel model ===
        if period == 0:
            base_rent = 0.0

        # === EXPENSES (calculate first for NNN reimbursements) ===
        expense_escalation = calculate_escalation_factor(expense_growth, period, "annual")

        # Use total RSF from tenants if provided, otherwise use total_sf
        expense_sf = sum(t.rsf for t in tenants) if tenants else total_sf
        fixed_opex = (expense_sf * fixed_opex_psf * expense_escalation) / 12 / 1000
        # property_tax_amount is annual in $000s, just divide by 12 for monthly
        prop_tax = (property_tax_amount * expense_escalation) / 12
        capex = (expense_sf * capex_reserve_psf * expense_escalation) / 12 / 1000

        # Management fee calculated on effective revenue (after reimbursements)
        # For NNN, we need to calculate this iteratively

        # === NNN EXPENSE REIMBURSEMENTS ===
        # In NNN lease, tenants reimburse landlord for operating expenses
        reimbursement_fixed = 0.0
        reimbursement_variable = 0.0

        if nnn_lease and period > 0:
            # Fixed reimbursements: OpEx + Property Taxes (CapEx is NOT reimbursed)
            reimbursement_fixed = fixed_opex + prop_tax
            # Variable reimbursements will include management fee (calculated below)

        # Potential revenue = base rent + reimbursements
        potential_revenue = base_rent + reimbursement_fixed

        # Vacancy and collection loss
        vacancy_loss = -potential_revenue * vacancy_rate
        effective_revenue = potential_revenue + vacancy_loss

        # Management fee on effective revenue
        mgmt_fee = effective_revenue * management_fee_percent

        # Variable reimbursement includes management fee in NNN
        if nnn_lease and period > 0:
            reimbursement_variable = mgmt_fee
            # Add variable reimbursement to revenue
            potential_revenue += reimbursement_variable
            effective_revenue += reimbursement_variable

        total_reimbursement = reimbursement_fixed + reimbursement_variable
        total_expenses = fixed_opex + mgmt_fee + prop_tax + capex

        # === NOI ===
        noi = effective_revenue - total_expenses

        period_data.append({
            "period": period,
            "period_date": period_date,
            "base_rent": base_rent,
            "reimbursement_fixed": reimbursement_fixed,
            "reimbursement_variable": reimbursement_variable,
            "total_reimbursement": total_reimbursement,
            "potential_revenue": potential_revenue,
            "vacancy_loss": vacancy_loss,
            "effective_revenue": effective_revenue,
            "fixed_opex": fixed_opex,
            "mgmt_fee": mgmt_fee,
            "prop_tax": prop_tax,
            "capex": capex,
            "total_expenses": total_expenses,
            "noi": noi,
        })

    # Second pass: calculate exit value with forward NOI and finalize cash flows
    for i, data in enumerate(period_data):
        period = data["period"]
        period_date = data["period_date"]
        noi = data["noi"]

        # === CAPITAL EVENTS ===
        acquisition_costs = 0.0
        exit_proceeds = 0.0

        if period == 0:
            acquisition_costs = purchase_price + closing_costs

        if period == hold_period_months:
            # Calculate forward 12-month NOI for exit valuation
            # Sum NOI from months (exit_month + 1) through (exit_month + 12)
            # Since we only have data through exit_month, we extrapolate using current NOI
            # This matches Excel's approach of using trailing NOI with escalation
            forward_noi = 0.0
            for future_month in range(1, 13):
                future_period = period + future_month
                if future_period <= hold_period_months:
                    # Use actual calculated NOI if available
                    forward_noi += period_data[future_period]["noi"]
                else:
                    # Extrapolate with escalation
                    escalation = (1 + rent_growth) ** (future_month / 12)
                    forward_noi += noi * escalation

            gross_value = forward_noi / exit_cap_rate if exit_cap_rate > 0 else 0
            sales_costs_amount = gross_value * sales_cost_percent
            exit_proceeds = gross_value - sales_costs_amount

        # === DEBT SERVICE with actual/365 calculation ===
        debt_service = 0.0
        interest_expense = 0.0
        principal_payment = 0.0

        if loan_amount and loan_amount > 0 and period > 0:
            if use_actual_365:
                # Actual/365 day count convention
                days_in_month = calculate_days_in_month(period_date)
                daily_rate = interest_rate / 365
                interest_expense = loan_amount * daily_rate * days_in_month
            else:
                # Simple monthly rate
                monthly_rate = interest_rate / 12
                interest_expense = loan_amount * monthly_rate

            if period <= io_months:
                # Interest-only
                debt_service = interest_expense
            else:
                # Amortizing
                amort_months = amortization_years * 12
                payment = calculate_payment(loan_amount, interest_rate, amort_months)
                principal_payment = payment - interest_expense
                debt_service = payment

        # === CASH FLOWS ===
        unleveraged_cf = noi - acquisition_costs + exit_proceeds
        leveraged_cf = unleveraged_cf - debt_service

        # First period: add loan proceeds if applicable
        if period == 0 and loan_amount and loan_amount > 0:
            leveraged_cf += loan_amount

        # Exit period: pay off loan balance
        if period == hold_period_months and loan_amount and loan_amount > 0:
            loan_payoff = loan_amount
            leveraged_cf -= loan_payoff

        cash_flows.append(
            {
                "period": period,
                "date": period_date.isoformat(),
                "base_rent": round(data["base_rent"], 2),
                "reimbursement_revenue": round(data["total_reimbursement"], 2),
                "potential_revenue": round(data["potential_revenue"], 2),
                "vacancy_loss": round(data["vacancy_loss"], 2),
                "effective_revenue": round(data["effective_revenue"], 2),
                "fixed_opex": round(data["fixed_opex"], 2),
                "management_fee": round(data["mgmt_fee"], 2),
                "property_tax": round(data["prop_tax"], 2),
                "capex_reserve": round(data["capex"], 2),
                "total_expenses": round(data["total_expenses"], 2),
                "noi": round(noi, 2),
                "acquisition_costs": round(acquisition_costs, 2),
                "exit_proceeds": round(exit_proceeds, 2),
                "interest_expense": round(interest_expense, 2),
                "principal_payment": round(principal_payment, 2),
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
