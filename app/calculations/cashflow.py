"""
Cash Flow Calculations

Generates monthly cash flow projections for real estate investments.
"""

from typing import List, Dict, Optional, Tuple
from datetime import date
from dateutil.relativedelta import relativedelta
from dataclasses import dataclass

from app.calculations.amortization import calculate_payment


@dataclass
class Tenant:
    """Represents a single tenant in the rent roll.

    Excel Reference: Model sheet rows 46-51 (revenue), rows 33-38 (TI/LC)

    The H-column flag in Excel determines whether TI/LC/Free Rent apply at rollover:
    - H=1: No free rent, no TI/LC at rollover (e.g., Peter Millar)
    - H=0: Has free rent, has TI/LC at rollover (e.g., J McLaughlin, Gucci)
    """

    name: str
    rsf: float  # Rentable square feet
    in_place_rent_psf: float  # Current rent per SF per year
    market_rent_psf: float  # Market rent per SF per year
    lease_end_month: int  # Month number when lease expires (0-indexed)

    # Flag: Whether to apply TI/LC/Free Rent at lease rollover (Excel H-column)
    # True = H=0 (apply costs), False = H=1 (no costs)
    apply_rollover_costs: bool = True

    # Free rent period (for new leases or lease rollovers)
    free_rent_months: int = 0
    free_rent_start_month: int = 0  # 0 = starts at acquisition

    # TI buildout period (no rent during construction after rollover)
    ti_buildout_months: int = 0

    # Lease commission rates
    lc_percent_years_1_5: float = 0.06  # 6% for years 1-5
    lc_percent_years_6_plus: float = 0.03  # 3% for years 6+
    new_lease_term_years: int = 10  # New lease term at rollover

    # TI allowance for rollover
    ti_allowance_psf: float = 0.0


@dataclass
class RateCurve:
    """SOFR forward rate curve for floating rate calculations."""

    rates: Dict[date, float]  # Date -> rate mapping

    def get_rate(self, period_date: date) -> float:
        """
        Get the SOFR rate for a given date.

        Uses the most recent rate on or before the period date.
        Falls back to 0.0 if no rates are available.
        """
        if not self.rates:
            return 0.0

        # Find the most recent rate on or before the period date
        applicable_dates = [d for d in self.rates.keys() if d <= period_date]
        if not applicable_dates:
            # Use earliest rate if all rates are in the future
            earliest = min(self.rates.keys())
            return self.rates[earliest]

        latest_applicable = max(applicable_dates)
        return self.rates[latest_applicable]


def calculate_tenant_rent(
    tenant: Tenant,
    period: int,
    rent_growth: float,
) -> float:
    """
    Calculate monthly rent for a single tenant.

    Uses in-place rent until lease expiration, then rolls to market rent.
    Applies monthly compounding escalation factor per Excel formula.
    Returns NET rent (after free rent deduction).

    For detailed breakdown including free rent deduction, use
    calculate_tenant_rent_detailed().

    Args:
        tenant: Tenant data
        period: Month number (0 = acquisition month)
        rent_growth: Annual rent escalation rate (e.g., 0.025 for 2.5%)

    Returns:
        Monthly NET rent in $000s (gross rent minus free rent deduction)
    """
    gross_rent, free_rent_deduction = calculate_tenant_rent_detailed(
        tenant, period, rent_growth
    )
    return gross_rent + free_rent_deduction  # deduction is negative


def calculate_tenant_rent_detailed(
    tenant: Tenant,
    period: int,
    rent_growth: float,
) -> Tuple[float, float]:
    """
    Calculate monthly rent with detailed breakdown for a single tenant.

    Excel Reference: Model sheet rows 46-51

    The Excel model calculates:
    1. Gross rent (even during free rent periods at market rate)
    2. Free rent deduction as a SEPARATE negative line item

    Timeline at lease rollover (e.g., J McLaughlin at month 50):
    - Month 50: Last in-place rent
    - Months 51-56: TI buildout (gross_rent = $0, deduction = $0)
    - Months 57-66: Free rent period (gross_rent = market, deduction = -market)
    - Month 67+: Paying rent (gross_rent = market, deduction = $0)

    Escalation: Uses MONTHLY COMPOUNDING per Excel Row 2 formula:
    (1 + rate/12)^period

    Args:
        tenant: Tenant data
        period: Month number (0 = acquisition month)
        rent_growth: Annual rent escalation rate (e.g., 0.025 for 2.5%)

    Returns:
        Tuple of (gross_rent, free_rent_deduction) in $000s
        - gross_rent: Always positive or zero
        - free_rent_deduction: Always negative or zero
    """
    # Apply RENT escalation (monthly compounding)
    escalation_factor = calculate_rent_escalation(rent_growth, period)

    # Initialize
    gross_rent = 0.0
    free_rent_deduction = 0.0

    if period <= tenant.lease_end_month:
        # === DURING ORIGINAL LEASE TERM ===

        # Check for in-place lease free rent period
        if tenant.free_rent_start_month > 0:
            # Free rent during in-place lease
            free_rent_end = tenant.free_rent_start_month + tenant.free_rent_months
            if tenant.free_rent_start_month <= period < free_rent_end:
                # Calculate gross rent at in-place rate
                gross_rent = (tenant.rsf * tenant.in_place_rent_psf * escalation_factor) / 12 / 1000
                # Deduction negates it
                free_rent_deduction = -gross_rent
                return (gross_rent, free_rent_deduction)

        # Normal in-place rent
        gross_rent = (tenant.rsf * tenant.in_place_rent_psf * escalation_factor) / 12 / 1000

    else:
        # === AFTER LEASE EXPIRATION (Rollover) ===
        rollover_month = tenant.lease_end_month + 1

        # Check if apply_rollover_costs flag is set (Excel H-column)
        if tenant.apply_rollover_costs:
            # H=0: Apply TI buildout gap and free rent

            # TI buildout period comes first (no rent during construction)
            ti_end = rollover_month + tenant.ti_buildout_months
            if rollover_month <= period < ti_end:
                # During TI buildout: zero revenue, zero deduction
                return (0.0, 0.0)

            # Calculate market rent
            gross_rent = (tenant.rsf * tenant.market_rent_psf * escalation_factor) / 12 / 1000

            # Free rent period comes after TI buildout
            free_rent_start = ti_end
            free_rent_end = free_rent_start + tenant.free_rent_months
            if free_rent_start <= period < free_rent_end:
                # During free rent: show market rent with negative deduction
                free_rent_deduction = -gross_rent

        else:
            # H=1: No TI gap, no free rent - immediate transition to market rent
            gross_rent = (tenant.rsf * tenant.market_rent_psf * escalation_factor) / 12 / 1000

    return (gross_rent, free_rent_deduction)


def calculate_lease_commission(
    tenant: Tenant,
    rent_growth: float,
    rollover_month: int,
) -> float:
    """
    Calculate lease commission at lease rollover using Excel LCs sheet methodology.

    Excel Reference: LCs sheet rows 16-25

    The Excel model calculates LC year-by-year with:
    1. Annual rent escalating each year: rent_year_n = rent_year_1 * (1 + growth)^(n-1)
    2. Year 1 rent reduced by free rent months: net_rent_y1 = annual_rent * (12 - free_months) / 12
    3. Different LC rates for years 1-5 (6%) vs years 6+ (3%)

    Example (LCs sheet for 2,300 SF @ $25/mo = $690K annual):
    | Year | Annual Rent | Net Rent | LC% | LC $ |
    |------|-------------|----------|-----|------|
    | 1 | $690,000 | $115,000 | 6% | $6,900 |
    | 2 | $707,250 | $707,250 | 6% | $42,435 |
    | ... | ... | ... | ... | ... |
    | 10 | $861,715 | $861,715 | 3% | $25,851 |
    | TOTAL | | | | $306,216 |

    Args:
        tenant: Tenant data with LC rates, new lease term, and free rent months
        rent_growth: Annual rent escalation rate
        rollover_month: Month when rollover occurs (used for base rent escalation)

    Returns:
        Lease commission in $000s (one-time cost at rollover)
    """
    # Skip if tenant doesn't apply rollover costs (H=1 in Excel)
    if not tenant.apply_rollover_costs:
        return 0.0

    # Calculate base annual rent at rollover time
    # Use RENT escalation (monthly compounding) to get the market rent level
    escalation_factor = calculate_rent_escalation(rent_growth, rollover_month)
    annual_rent_year_1 = tenant.rsf * tenant.market_rent_psf * escalation_factor

    total_lc = 0.0

    for year in range(1, tenant.new_lease_term_years + 1):
        # Year-by-year escalated rent (each year compounds from year 1)
        if year == 1:
            annual_rent = annual_rent_year_1
        else:
            annual_rent = annual_rent_year_1 * (1 + rent_growth) ** (year - 1)

        # Year 1: Deduct free rent months from net rent calculation
        if year == 1 and tenant.free_rent_months > 0:
            net_rent = annual_rent * (12 - tenant.free_rent_months) / 12
        else:
            net_rent = annual_rent

        # LC rate based on year
        lc_rate = tenant.lc_percent_years_1_5 if year <= 5 else tenant.lc_percent_years_6_plus
        total_lc += net_rent * lc_rate

    return total_lc / 1000  # Convert to $000s


def calculate_ti_cost(tenant: Tenant, rent_growth: float, rollover_month: int) -> float:
    """
    Calculate TI allowance cost at lease rollover.

    Excel Reference: Model sheet rows 33-35

    TI costs apply ONLY if:
    1. Global TI toggle is ON (Assumptions D38 = 1)
    2. Tenant's apply_rollover_costs flag is True (H column = 0)

    Excel formula: TI = $PSF × RSF × escalation_factor / 1000

    Args:
        tenant: Tenant data with TI allowance PSF
        rent_growth: Annual rent escalation rate (used for escalation at rollover)
        rollover_month: Month when rollover occurs

    Returns:
        TI cost in $000s (one-time cost)
    """
    # Skip if tenant doesn't apply rollover costs (H=1 in Excel)
    if not tenant.apply_rollover_costs:
        return 0.0

    # Apply rent escalation factor at rollover time (per Excel formula)
    escalation_factor = calculate_rent_escalation(rent_growth, rollover_month)

    return (tenant.rsf * tenant.ti_allowance_psf * escalation_factor) / 1000


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


def calculate_rent_escalation(annual_rate: float, period: int) -> float:
    """
    Calculate RENT escalation factor using MONTHLY COMPOUNDING.

    Excel Formula (Row 2): L2 = K2 * (1 + $D$2/12)
    This compounds monthly: (1 + rate/12)^period

    Result after 12 months: 1.0252884570 (≈2.53% growth due to compounding)

    Args:
        annual_rate: Annual escalation rate as decimal (e.g., 0.025 for 2.5%)
        period: Period number (0-based months)

    Returns:
        Escalation factor for the given period
    """
    return (1 + annual_rate / 12) ** period


def calculate_expense_escalation(annual_rate: float, period: int) -> float:
    """
    Calculate EXPENSE escalation factor using ANNUAL RATE applied monthly.

    Excel Formula (Row 3): L3 = K3 * (1 + $D3)^(1/12)
    This applies annual rate spread across months: (1 + rate)^(period/12)

    Result after 12 months: 1.0250000000 (EXACTLY 2.5% growth by design)

    Args:
        annual_rate: Annual escalation rate as decimal (e.g., 0.025 for 2.5%)
        period: Period number (0-based months)

    Returns:
        Escalation factor for the given period
    """
    return (1 + annual_rate) ** (period / 12)


def calculate_escalation_factor(
    annual_rate: float, period: int, frequency: str = "monthly"
) -> float:
    """
    DEPRECATED: Use calculate_rent_escalation or calculate_expense_escalation instead.

    Calculate escalation factor for a given period.
    Kept for backward compatibility.

    Args:
        annual_rate: Annual escalation rate as decimal
        period: Period number (0-based)
        frequency: How often escalation applies ('monthly' or 'annual')
    """
    if frequency == "monthly":
        # Use rent escalation (monthly compounding) for backward compatibility
        return calculate_rent_escalation(annual_rate, period)
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
    interest_rate: float = 0.0525,  # PRD Section 7.1: 5.25%
    io_months: int = 120,
    amortization_years: int = 30,
    tenants: Optional[List[Tenant]] = None,
    nnn_lease: bool = True,
    use_actual_365: bool = True,
    # === NEW: Variable OpEx ===
    variable_opex_psf: float = 0.0,
    # === NEW: Parking/Storage Income ===
    parking_stalls: int = 0,
    parking_rate_per_stall: float = 0.0,  # Monthly rate per stall
    storage_units: int = 0,
    storage_rate_per_unit: float = 0.0,  # Monthly rate per unit
    # === NEW: Loan Closing Costs ===
    loan_origination_fee: float = 0.0,  # In $000s
    loan_closing_costs: float = 0.0,  # In $000s
    # === NEW: SOFR Integration ===
    interest_type: str = "fixed",  # "fixed" or "floating"
    floating_spread: float = 0.0,  # Spread over SOFR for floating rate
    rate_curve: Optional[RateCurve] = None,  # SOFR curve for floating rate
    # === NEW: Capitalized Interest ===
    capitalize_interest: bool = False,  # Whether to capitalize unpaid interest
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
        variable_opex_psf: Variable operating expenses per SF (escalates with rent)
        parking_stalls: Number of parking stalls
        parking_rate_per_stall: Monthly rate per parking stall
        storage_units: Number of storage units
        storage_rate_per_unit: Monthly rate per storage unit
        loan_origination_fee: Upfront loan fee in $000s
        loan_closing_costs: Loan closing costs in $000s
        interest_type: "fixed" or "floating"
        floating_spread: Spread over SOFR for floating rate loans
        rate_curve: RateCurve object with SOFR rates
        capitalize_interest: Whether to add unpaid interest to loan balance
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
            # Use RENT escalation (monthly compounding) per Excel Row 2
            rent_escalation = calculate_rent_escalation(rent_growth, period)
            base_rent = (total_sf * in_place_rent_psf * rent_escalation) / 12 / 1000

        # === Month 0 has no operating revenue in Excel model ===
        if period == 0:
            base_rent = 0.0

        # === PARKING/STORAGE INCOME ===
        # Parking and storage income escalates with RENT (monthly compounding)
        rent_escalation = calculate_rent_escalation(rent_growth, period)
        parking_income = 0.0
        storage_income = 0.0
        if period > 0:  # No other income in Month 0
            parking_income = (parking_stalls * parking_rate_per_stall * rent_escalation) / 1000
            storage_income = (storage_units * storage_rate_per_unit * rent_escalation) / 1000
        other_income = parking_income + storage_income

        # === EXPENSES (calculate first for NNN reimbursements) ===
        # Use EXPENSE escalation formula: (1 + rate)^(period/12) per Excel Row 3
        expense_escalation = calculate_expense_escalation(expense_growth, period)

        # Use total RSF from tenants if provided, otherwise use total_sf
        expense_sf = sum(t.rsf for t in tenants) if tenants else total_sf
        fixed_opex = (expense_sf * fixed_opex_psf * expense_escalation) / 12 / 1000

        # Variable OpEx (escalates with expenses)
        var_opex = (expense_sf * variable_opex_psf * expense_escalation) / 12 / 1000

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
            # Note: Variable OpEx is also reimbursed in NNN
            reimbursement_fixed = fixed_opex + var_opex + prop_tax
            # Variable reimbursements will include management fee (calculated below)

        # Potential revenue = base rent + other income + reimbursements
        potential_revenue = base_rent + other_income + reimbursement_fixed

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
        total_expenses = fixed_opex + var_opex + mgmt_fee + prop_tax + capex

        # === NOI ===
        noi = effective_revenue - total_expenses

        period_data.append({
            "period": period,
            "period_date": period_date,
            "base_rent": base_rent,
            "parking_income": parking_income,
            "storage_income": storage_income,
            "other_income": other_income,
            "reimbursement_fixed": reimbursement_fixed,
            "reimbursement_variable": reimbursement_variable,
            "total_reimbursement": total_reimbursement,
            "potential_revenue": potential_revenue,
            "vacancy_loss": vacancy_loss,
            "effective_revenue": effective_revenue,
            "fixed_opex": fixed_opex,
            "variable_opex": var_opex,
            "mgmt_fee": mgmt_fee,
            "prop_tax": prop_tax,
            "capex": capex,
            "total_expenses": total_expenses,
            "noi": noi,
        })

    # === PRE-CALCULATE LEASE ROLLOVER EVENTS ===
    # Build a dict of period -> (lease_commissions, ti_costs) for one-time capital costs
    rollover_costs: Dict[int, Tuple[float, float]] = {}
    if tenants:
        for tenant in tenants:
            rollover_month = tenant.lease_end_month + 1
            if 0 < rollover_month <= hold_period_months:
                lc_cost = calculate_lease_commission(tenant, rent_growth, rollover_month)
                ti_cost = calculate_ti_cost(tenant, rent_growth, rollover_month)
                if rollover_month in rollover_costs:
                    existing_lc, existing_ti = rollover_costs[rollover_month]
                    rollover_costs[rollover_month] = (existing_lc + lc_cost, existing_ti + ti_cost)
                else:
                    rollover_costs[rollover_month] = (lc_cost, ti_cost)

    # === INITIALIZE LOAN BALANCE TRACKING FOR CAPITALIZED INTEREST ===
    current_loan_balance = loan_amount if loan_amount else 0.0
    total_capitalized_interest = 0.0

    # Second pass: calculate exit value with forward NOI and finalize cash flows
    for i, data in enumerate(period_data):
        period = data["period"]
        period_date = data["period_date"]
        noi = data["noi"]

        # === CAPITAL EVENTS ===
        acquisition_costs = 0.0
        exit_proceeds = 0.0
        lease_commission_cost = 0.0
        ti_cost = 0.0

        if period == 0:
            acquisition_costs = purchase_price + closing_costs

        # Lease rollover costs (LC + TI) at the month after lease expiry
        if period in rollover_costs:
            lease_commission_cost, ti_cost = rollover_costs[period]

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

        # === DEBT SERVICE with actual/365 calculation and SOFR support ===
        # Excel Formula (Row 122): AVERAGE(L119, L119+L120) * L116 * (L12-K12) / 365
        # Where: L119=Beginning balance, L120=Draws, L116=Rate
        debt_service = 0.0
        interest_expense = 0.0
        principal_payment = 0.0
        capitalized_interest = 0.0
        period_draws = 0.0  # For construction loans, this would be non-zero
        effective_rate = interest_rate  # Default to fixed rate

        if current_loan_balance > 0 and period > 0:
            # Determine effective interest rate
            if interest_type == "floating" and rate_curve is not None:
                # Floating rate: SOFR + spread
                sofr_rate = rate_curve.get_rate(period_date)
                effective_rate = sofr_rate + floating_spread
            else:
                # Fixed rate
                effective_rate = interest_rate

            # Calculate AVERAGE balance per Excel formula
            # AVERAGE(beginning_balance, beginning_balance + draws)
            # = (beginning + beginning + draws) / 2
            # = beginning + draws/2
            avg_balance = current_loan_balance + period_draws / 2

            if use_actual_365:
                # Actual/365 day count convention
                days_in_month = calculate_days_in_month(period_date)
                daily_rate = effective_rate / 365
                interest_expense = avg_balance * daily_rate * days_in_month
            else:
                # Simple monthly rate
                monthly_rate = effective_rate / 12
                interest_expense = avg_balance * monthly_rate

            if period <= io_months:
                # Interest-only period
                debt_service = interest_expense
            else:
                # Amortizing period
                amort_months = amortization_years * 12
                payment = calculate_payment(current_loan_balance, effective_rate, amort_months)
                principal_payment = payment - interest_expense
                debt_service = payment
                # Reduce loan balance by principal payment
                current_loan_balance -= principal_payment

        # === CASH FLOWS ===
        # Unleveraged includes lease costs as capital outflows
        total_capital_costs = lease_commission_cost + ti_cost
        unleveraged_cf = noi - acquisition_costs - total_capital_costs + exit_proceeds
        leveraged_cf = unleveraged_cf - debt_service

        # First period: add loan proceeds minus closing costs if applicable
        if period == 0 and loan_amount and loan_amount > 0:
            # Net loan proceeds = loan amount - origination fee - closing costs
            net_loan_proceeds = loan_amount - loan_origination_fee - loan_closing_costs
            leveraged_cf += net_loan_proceeds

        # === CAPITALIZED INTEREST ===
        # During I/O period, if cash flow is negative, capitalize the shortfall
        if capitalize_interest and period > 0 and period <= io_months:
            if leveraged_cf < 0:
                # Capitalize the shortfall (add to loan balance)
                capitalized_interest = min(interest_expense, abs(leveraged_cf))
                current_loan_balance += capitalized_interest
                total_capitalized_interest += capitalized_interest
                # Adjust leveraged CF (interest was capitalized, not paid)
                leveraged_cf += capitalized_interest

        # Exit period: pay off loan balance (including any capitalized interest)
        loan_payoff = 0.0
        if period == hold_period_months and loan_amount and loan_amount > 0:
            loan_payoff = current_loan_balance
            leveraged_cf -= loan_payoff

        cash_flows.append(
            {
                "period": period,
                "date": period_date.isoformat(),
                "base_rent": round(data["base_rent"], 2),
                "parking_income": round(data["parking_income"], 2),
                "storage_income": round(data["storage_income"], 2),
                "other_income": round(data["other_income"], 2),
                "reimbursement_revenue": round(data["total_reimbursement"], 2),
                "potential_revenue": round(data["potential_revenue"], 2),
                "vacancy_loss": round(data["vacancy_loss"], 2),
                "effective_revenue": round(data["effective_revenue"], 2),
                "fixed_opex": round(data["fixed_opex"], 2),
                "variable_opex": round(data["variable_opex"], 2),
                "management_fee": round(data["mgmt_fee"], 2),
                "property_tax": round(data["prop_tax"], 2),
                "capex_reserve": round(data["capex"], 2),
                "total_expenses": round(data["total_expenses"], 2),
                "noi": round(noi, 2),
                "acquisition_costs": round(acquisition_costs, 2),
                "lease_commission": round(lease_commission_cost, 2),
                "ti_cost": round(ti_cost, 2),
                "exit_proceeds": round(exit_proceeds, 2),
                "effective_interest_rate": round(effective_rate, 6),
                "interest_expense": round(interest_expense, 2),
                "principal_payment": round(principal_payment, 2),
                "debt_service": round(debt_service, 2),
                "capitalized_interest": round(capitalized_interest, 2),
                "loan_balance": round(current_loan_balance, 2),
                "loan_payoff": round(loan_payoff, 2),
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
