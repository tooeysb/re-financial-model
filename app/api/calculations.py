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
