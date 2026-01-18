"""
Financial calculation API endpoints.

These endpoints accept inputs and return calculated results.
Used by HTMX for real-time updates.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional
from datetime import date

from app.calculations import irr, cashflow, waterfall

router = APIRouter()


class TenantInput(BaseModel):
    """Input for a single tenant in the rent roll."""

    name: str
    rsf: float  # Rentable square feet
    in_place_rent_psf: float  # Current rent per SF per year
    market_rent_psf: float  # Market rent per SF per year
    lease_end_month: int  # Month number when lease expires (0-indexed)

    # Rollover behavior (Excel H-column equivalent)
    # True = apply TI/LC/Free Rent at rollover (H=0)
    # False = no costs, immediate market rent (H=1)
    apply_rollover_costs: bool = True

    # Free rent period
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


class WaterfallHurdleInput(BaseModel):
    """Input for a single waterfall hurdle tier."""

    name: str = "Hurdle"
    pref_return: float = 0.05  # Annual preferred return rate
    lp_split: float = 0.90  # LP's share at this tier
    gp_split: float = 0.10  # GP's share at this tier
    gp_promote: float = 0.0  # GP promote percentage


class CashFlowInput(BaseModel):
    """Input for cash flow calculation."""

    # Timing
    acquisition_date: date
    hold_period_months: int = 120
    stabilization_month: int = 77

    # Acquisition
    purchase_price: float
    closing_costs: float

    # Revenue
    total_sf: float
    in_place_rent_psf: float
    market_rent_psf: float
    vacancy_rate: float = 0.0
    collection_loss: float = 0.0

    # Tenant-level rent roll (optional, for per-tenant calculations)
    # If provided, uses tenant-by-tenant rent with lease expiry logic
    tenants: Optional[List[TenantInput]] = None

    # Expenses
    fixed_opex_psf: float = 36.0
    variable_opex_psf: float = 0.0
    management_fee_percent: float = 0.04
    property_tax_amount: float = 0.0
    capex_reserve_psf: float = 5.0

    # Escalation
    rent_growth: float = 0.025
    expense_growth: float = 0.025

    # Exit
    exit_cap_rate: float = 0.05
    sales_cost_percent: float = 0.01

    # Financing (optional)
    loan_amount: Optional[float] = None
    interest_rate: float = 0.05
    io_months: int = 120
    amortization_years: int = 30

    # Lease structure
    nnn_lease: bool = True  # If True, adds expense reimbursements to revenue
    use_actual_365: bool = True  # If True, uses actual/365 day count for interest

    # Waterfall (optional for LP/GP returns)
    lp_share: float = 0.90
    gp_share: float = 0.10
    pref_return: float = 0.05
    compound_monthly: bool = False

    # Multi-hurdle waterfall configuration
    # If use_multi_hurdle is True, uses the 225 Worth Ave default structure
    # Otherwise uses simple single-tier waterfall
    use_multi_hurdle: bool = True
    hurdles: Optional[List[WaterfallHurdleInput]] = None
    final_lp_split: float = 0.75
    final_gp_split: float = 0.0833
    final_gp_promote: float = 0.1667


class ReturnMetrics(BaseModel):
    """Calculated return metrics."""

    # Unleveraged
    unleveraged_irr: float
    unleveraged_multiple: float
    unleveraged_profit: float

    # Leveraged
    leveraged_irr: Optional[float] = None
    leveraged_multiple: Optional[float] = None
    leveraged_profit: Optional[float] = None

    # LP/GP (if waterfall provided)
    lp_irr: Optional[float] = None
    lp_multiple: Optional[float] = None
    gp_irr: Optional[float] = None
    gp_multiple: Optional[float] = None


class CashFlowResponse(BaseModel):
    """Response with cash flows and metrics."""

    metrics: ReturnMetrics
    annual_cashflows: List[dict]
    monthly_cashflows: List[dict]


@router.post("/cashflows", response_model=CashFlowResponse)
async def calculate_cashflows(inputs: CashFlowInput):
    """Calculate full cash flow projections and return metrics."""

    # Generate dates
    dates = cashflow.generate_monthly_dates(
        inputs.acquisition_date, inputs.hold_period_months
    )

    # Convert tenant inputs to Tenant objects if provided
    tenant_list = None
    if inputs.tenants:
        tenant_list = [
            cashflow.Tenant(
                name=t.name,
                rsf=t.rsf,
                in_place_rent_psf=t.in_place_rent_psf,
                market_rent_psf=t.market_rent_psf,
                lease_end_month=t.lease_end_month,
                apply_rollover_costs=t.apply_rollover_costs,
                free_rent_months=t.free_rent_months,
                free_rent_start_month=t.free_rent_start_month,
                ti_buildout_months=t.ti_buildout_months,
                lc_percent_years_1_5=t.lc_percent_years_1_5,
                lc_percent_years_6_plus=t.lc_percent_years_6_plus,
                new_lease_term_years=t.new_lease_term_years,
                ti_allowance_psf=t.ti_allowance_psf,
            )
            for t in inputs.tenants
        ]

    # Calculate monthly cash flows
    monthly_cfs = cashflow.generate_cash_flows(
        acquisition_date=inputs.acquisition_date,
        hold_period_months=inputs.hold_period_months,
        purchase_price=inputs.purchase_price,
        closing_costs=inputs.closing_costs,
        total_sf=inputs.total_sf,
        in_place_rent_psf=inputs.in_place_rent_psf,
        market_rent_psf=inputs.market_rent_psf,
        rent_growth=inputs.rent_growth,
        vacancy_rate=inputs.vacancy_rate,
        fixed_opex_psf=inputs.fixed_opex_psf,
        management_fee_percent=inputs.management_fee_percent,
        property_tax_amount=inputs.property_tax_amount,
        capex_reserve_psf=inputs.capex_reserve_psf,
        expense_growth=inputs.expense_growth,
        exit_cap_rate=inputs.exit_cap_rate,
        sales_cost_percent=inputs.sales_cost_percent,
        loan_amount=inputs.loan_amount,
        interest_rate=inputs.interest_rate,
        io_months=inputs.io_months,
        amortization_years=inputs.amortization_years,
        tenants=tenant_list,
        nnn_lease=inputs.nnn_lease,
        use_actual_365=inputs.use_actual_365,
    )

    # Extract cash flow arrays
    unleveraged_cf = [cf["unleveraged_cash_flow"] for cf in monthly_cfs]
    leveraged_cf = [cf["leveraged_cash_flow"] for cf in monthly_cfs]

    # Calculate metrics
    unleveraged_irr_val = irr.calculate_xirr(unleveraged_cf, dates)
    unleveraged_multiple = irr.calculate_multiple(unleveraged_cf)
    unleveraged_profit = irr.calculate_profit(unleveraged_cf)

    leveraged_irr_val = None
    leveraged_multiple_val = None
    leveraged_profit_val = None

    if inputs.loan_amount and inputs.loan_amount > 0:
        try:
            leveraged_irr_val = irr.calculate_xirr(leveraged_cf, dates)
            leveraged_multiple_val = irr.calculate_multiple(leveraged_cf)
            leveraged_profit_val = irr.calculate_profit(leveraged_cf)
        except Exception:
            pass  # Leveraged IRR may not converge

    # Calculate LP/GP returns using waterfall
    lp_irr_val = None
    lp_multiple_val = None
    gp_irr_val = None
    gp_multiple_val = None

    # Use leveraged cash flows for waterfall if we have debt, otherwise unleveraged
    project_cf = leveraged_cf if (inputs.loan_amount and inputs.loan_amount > 0) else unleveraged_cf
    total_equity = inputs.purchase_price + inputs.closing_costs - (inputs.loan_amount or 0)

    if total_equity > 0:
        try:
            # Build hurdle configuration
            hurdle_list = None
            final_split = None

            if inputs.use_multi_hurdle:
                if inputs.hurdles:
                    # Use custom hurdles if provided
                    hurdle_list = [
                        waterfall.WaterfallHurdle(
                            name=h.name,
                            pref_return=h.pref_return,
                            lp_split=h.lp_split,
                            gp_split=h.gp_split,
                            gp_promote=h.gp_promote,
                        )
                        for h in inputs.hurdles
                    ]
                # If no custom hurdles, will use DEFAULT_HURDLES from waterfall module

                final_split = {
                    "lp_split": inputs.final_lp_split,
                    "gp_split": inputs.final_gp_split,
                    "gp_promote": inputs.final_gp_promote,
                }
            else:
                # Use simple single-tier waterfall
                hurdle_list = [
                    waterfall.WaterfallHurdle(
                        name="Single Hurdle",
                        pref_return=inputs.pref_return,
                        lp_split=inputs.lp_share,
                        gp_split=inputs.gp_share,
                        gp_promote=0.0,
                    )
                ]
                final_split = {
                    "lp_split": inputs.lp_share,
                    "gp_split": inputs.gp_share,
                    "gp_promote": 0.0,
                }

            distributions = waterfall.calculate_waterfall_distributions(
                leveraged_cash_flows=project_cf,
                dates=dates,
                total_equity=total_equity,
                lp_share=inputs.lp_share,
                gp_share=inputs.gp_share,
                pref_return=inputs.pref_return,
                compound_monthly=inputs.compound_monthly,
                hurdles=hurdle_list,
                final_split=final_split,
            )

            lp_equity = total_equity * inputs.lp_share
            gp_equity = total_equity * inputs.gp_share

            lp_cf = waterfall.extract_lp_cash_flows(distributions, lp_equity)
            gp_cf = waterfall.extract_gp_cash_flows(distributions, gp_equity)

            try:
                lp_irr_val = irr.calculate_xirr(lp_cf, dates)
                lp_multiple_val = irr.calculate_multiple(lp_cf)
            except Exception:
                pass

            try:
                gp_irr_val = irr.calculate_xirr(gp_cf, dates)
                gp_multiple_val = irr.calculate_multiple(gp_cf)
            except Exception:
                pass
        except Exception:
            pass  # Waterfall calculation may fail

    # Annualize cash flows
    annual_cfs = cashflow.annualize_cash_flows(monthly_cfs)

    return CashFlowResponse(
        metrics=ReturnMetrics(
            unleveraged_irr=unleveraged_irr_val,
            unleveraged_multiple=unleveraged_multiple,
            unleveraged_profit=unleveraged_profit,
            leveraged_irr=leveraged_irr_val,
            leveraged_multiple=leveraged_multiple_val,
            leveraged_profit=leveraged_profit_val,
            lp_irr=lp_irr_val,
            lp_multiple=lp_multiple_val,
            gp_irr=gp_irr_val,
            gp_multiple=gp_multiple_val,
        ),
        annual_cashflows=annual_cfs,
        monthly_cashflows=monthly_cfs,
    )


class IRRInput(BaseModel):
    """Input for IRR calculation."""

    cash_flows: List[float]
    dates: Optional[List[date]] = None


class IRRResponse(BaseModel):
    """Response with IRR calculation."""

    irr: float
    multiple: float
    profit: float
    npv_at_10_percent: float


@router.post("/irr", response_model=IRRResponse)
async def calculate_irr_endpoint(inputs: IRRInput):
    """Calculate IRR for given cash flows."""
    from fastapi import HTTPException

    try:
        if inputs.dates:
            irr_val = irr.calculate_xirr(inputs.cash_flows, inputs.dates)
        else:
            irr_val = irr.calculate_irr(inputs.cash_flows)

        multiple = irr.calculate_multiple(inputs.cash_flows)
        profit = irr.calculate_profit(inputs.cash_flows)
        npv = irr.calculate_npv(inputs.cash_flows, 0.10)

        return IRRResponse(
            irr=irr_val,
            multiple=multiple,
            profit=profit,
            npv_at_10_percent=npv,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class AmortizationInput(BaseModel):
    """Input for amortization calculation."""

    principal: float
    annual_rate: float
    amortization_years: int
    io_months: int = 0
    total_months: int = 120


@router.post("/amortization")
async def calculate_amortization(inputs: AmortizationInput):
    """Generate loan amortization schedule."""

    from app.calculations.amortization import generate_amortization_schedule

    schedule = generate_amortization_schedule(
        principal=inputs.principal,
        annual_rate=inputs.annual_rate,
        amortization_months=inputs.amortization_years * 12,
        io_months=inputs.io_months,
        total_months=inputs.total_months,
    )

    return {
        "schedule": schedule,
        "total_interest": sum(row["interest"] for row in schedule),
        "total_principal": sum(row["principal"] for row in schedule),
    }
