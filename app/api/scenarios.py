"""
Scenario management API endpoints.
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Property, Scenario, Lease, Loan
from app.calculations import irr, cashflow, waterfall

logger = logging.getLogger(__name__)

router = APIRouter()


# ============= Input Schemas =============


class LeaseInput(BaseModel):
    """Lease input schema."""

    tenant_name: str
    space_id: str
    rsf: float
    base_rent_psf: float
    market_rent_psf: Optional[float] = None
    escalation_type: str = "percentage"
    escalation_value: float = 0.025
    escalation_frequency: str = "annual"
    lease_start: date
    lease_end: date
    free_rent_months: int = 0
    ti_allowance_psf: float = 0
    ti_buildout_months: int = 6
    lc_percent_years_1_5: float = 0.06
    lc_percent_years_6_plus: float = 0.03
    reimbursement_type: str = "NNN"
    recovery_percentage: float = 1.0
    is_vacant: bool = False
    options: List[dict] = []


class LoanInput(BaseModel):
    """Loan input schema."""

    name: str
    loan_type: str = "acquisition"
    amount: Optional[float] = None
    ltc_ratio: Optional[float] = None
    ltv_ratio: Optional[float] = None
    interest_type: str = "fixed"
    fixed_rate: float = 0.05
    floating_spread: Optional[float] = None
    index_type: str = "SOFR"
    rate_floor: Optional[float] = None
    rate_cap: Optional[float] = None
    origination_fee_percent: float = 0.01
    closing_costs_percent: float = 0.01
    io_months: int = 120
    amortization_years: int = 30
    maturity_months: int = 120
    start_month: int = 0
    min_dscr: float = 1.25
    debt_yield_test: float = 0.065


class WaterfallHurdleInput(BaseModel):
    """Waterfall hurdle input."""

    name: str = "Hurdle"
    pref_return: float = 0.05
    lp_split: float = 0.90
    gp_split: float = 0.10


class ScenarioCreate(BaseModel):
    """Schema for creating a scenario."""

    property_id: str
    name: str
    description: Optional[str] = None
    is_base_case: bool = False

    # Timing
    acquisition_date: date
    hold_period_months: int = 120
    stabilization_month: int = 77

    # Acquisition
    purchase_price: float
    closing_costs: float

    # Operating Assumptions
    market_rent_psf: float = 300.0
    vacancy_rate: float = 0.0
    collection_loss: float = 0.0
    fixed_opex_psf: float = 36.0
    variable_opex_psf: float = 0.0
    management_fee_percent: float = 0.04
    property_tax_amount: float = 0.0
    property_tax_millage: float = 0.015
    capex_reserve_psf: float = 5.0
    revenue_growth: float = 0.025
    expense_growth: float = 0.025

    # Exit
    exit_cap_rate: float = 0.05
    sales_cost_percent: float = 0.01

    # Waterfall
    lp_share: float = 0.90
    gp_share: float = 0.10
    pref_return: float = 0.05
    compound_monthly: bool = False
    waterfall_hurdles: List[WaterfallHurdleInput] = []

    # Nested data
    leases: List[LeaseInput] = []
    loans: List[LoanInput] = []


class ScenarioUpdate(BaseModel):
    """Schema for updating a scenario."""

    name: Optional[str] = None
    description: Optional[str] = None
    is_base_case: Optional[bool] = None
    acquisition_date: Optional[date] = None
    hold_period_months: Optional[int] = None
    stabilization_month: Optional[int] = None
    purchase_price: Optional[float] = None
    closing_costs: Optional[float] = None
    exit_cap_rate: Optional[float] = None
    sales_cost_percent: Optional[float] = None
    operating_assumptions: Optional[dict] = None
    waterfall_structure: Optional[dict] = None


# ============= Response Schemas =============


class LeaseResponse(BaseModel):
    """Lease response schema."""

    id: str
    tenant_name: str
    space_id: Optional[str]
    rsf: Optional[float]
    base_rent_psf: Optional[float]
    market_rent_psf: Optional[float]
    lease_start: Optional[date]
    lease_end: Optional[date]
    escalation_type: Optional[str]
    escalation_value: Optional[float]
    free_rent_months: Optional[int]
    ti_allowance_psf: Optional[float]
    reimbursement_type: Optional[str]
    is_vacant: bool = False

    class Config:
        from_attributes = True


class LoanResponse(BaseModel):
    """Loan response schema."""

    id: str
    name: Optional[str]
    loan_type: Optional[str]
    amount: Optional[float]
    ltc_ratio: Optional[float]
    interest_type: Optional[str]
    fixed_rate: Optional[float]
    floating_spread: Optional[float]
    io_months: Optional[int]
    amortization_years: Optional[int]

    class Config:
        from_attributes = True


class ReturnMetricsResponse(BaseModel):
    """Return metrics response."""

    unleveraged_irr: Optional[float] = None
    unleveraged_multiple: Optional[float] = None
    unleveraged_profit: Optional[float] = None
    leveraged_irr: Optional[float] = None
    leveraged_multiple: Optional[float] = None
    leveraged_profit: Optional[float] = None
    lp_irr: Optional[float] = None
    gp_irr: Optional[float] = None


class ScenarioResponse(BaseModel):
    """Schema for scenario response."""

    id: str
    property_id: str
    name: str
    description: Optional[str]
    is_base_case: bool
    acquisition_date: Optional[date]
    hold_period_months: Optional[int]
    purchase_price: Optional[float]
    closing_costs: Optional[float]
    exit_cap_rate: Optional[float]
    sales_cost_percent: Optional[float]
    operating_assumptions: Optional[dict]
    waterfall_structure: Optional[dict]
    return_metrics: Optional[dict]
    leases: List[LeaseResponse] = []
    loans: List[LoanResponse] = []

    class Config:
        from_attributes = True


class ScenarioListResponse(BaseModel):
    """Response for listing scenarios."""

    scenarios: List[ScenarioResponse]
    total: int


# ============= Helper Functions =============


def scenario_to_response(scenario: Scenario, include_children: bool = True) -> dict:
    """Convert Scenario model to response dict."""
    response = {
        "id": scenario.id,
        "property_id": scenario.property_id,
        "name": scenario.name,
        "description": scenario.description,
        "is_base_case": scenario.is_base_case,
        "acquisition_date": scenario.acquisition_date,
        "hold_period_months": scenario.hold_period_months,
        "purchase_price": scenario.purchase_price,
        "closing_costs": scenario.closing_costs,
        "exit_cap_rate": scenario.exit_cap_rate,
        "sales_cost_percent": scenario.sales_cost_percent,
        "operating_assumptions": scenario.operating_assumptions,
        "waterfall_structure": scenario.waterfall_structure,
        "return_metrics": scenario.return_metrics,
        "leases": [],
        "loans": [],
    }

    if include_children:
        response["leases"] = [
            {
                "id": l.id,
                "tenant_name": l.tenant_name,
                "space_id": l.space_id,
                "rsf": l.rsf,
                "base_rent_psf": l.base_rent_psf,
                "market_rent_psf": l.market_rent_psf,
                "lease_start": l.lease_start,
                "lease_end": l.lease_end,
                "escalation_type": l.escalation_type,
                "escalation_value": l.escalation_value,
                "free_rent_months": l.free_rent_months,
                "ti_allowance_psf": l.ti_allowance_psf,
                "reimbursement_type": l.reimbursement_type,
                "is_vacant": l.is_vacant or False,
            }
            for l in scenario.leases.filter_by(is_deleted=False).all()
        ]

        response["loans"] = [
            {
                "id": ln.id,
                "name": ln.name,
                "loan_type": ln.loan_type,
                "amount": ln.amount,
                "ltc_ratio": ln.ltc_ratio,
                "interest_type": ln.interest_type,
                "fixed_rate": ln.fixed_rate,
                "floating_spread": ln.floating_spread,
                "io_months": ln.io_months,
                "amortization_years": ln.amortization_years,
            }
            for ln in scenario.loans.filter_by(is_deleted=False).all()
        ]

    return response


def calculate_scenario_returns(scenario: Scenario, db: Session) -> dict:
    """Calculate return metrics for a scenario."""
    # Get operating assumptions
    op_assumptions = scenario.operating_assumptions or {}

    # Get total SF from leases
    leases = scenario.leases.filter_by(is_deleted=False).all()
    total_sf = sum(l.rsf or 0 for l in leases)

    if total_sf == 0:
        total_sf = op_assumptions.get("total_sf", 10000)

    # Get weighted average in-place rent
    in_place_rent = 0
    if leases:
        weighted_rent = sum((l.rsf or 0) * (l.base_rent_psf or 0) for l in leases)
        in_place_rent = weighted_rent / total_sf if total_sf > 0 else 0
    else:
        in_place_rent = op_assumptions.get("in_place_rent_psf", 200)

    # Get loan info
    loans = scenario.loans.filter_by(is_deleted=False).all()
    total_loan_amount = 0
    primary_rate = 0.05
    primary_io_months = 120
    primary_amort_years = 30

    if loans:
        primary_loan = loans[0]
        if primary_loan.amount:
            total_loan_amount = primary_loan.amount
        elif primary_loan.ltc_ratio and scenario.purchase_price:
            total_cost = scenario.purchase_price + (scenario.closing_costs or 0)
            total_loan_amount = total_cost * primary_loan.ltc_ratio

        primary_rate = primary_loan.fixed_rate or 0.05
        primary_io_months = primary_loan.io_months or 120
        primary_amort_years = primary_loan.amortization_years or 30

    # Convert values from full dollars to $000s for the cashflow module
    # The cashflow module expects purchase_price, closing_costs, loan_amount in $000s
    # But property_tax_amount is expected in full dollars (module divides by 1000 internally)
    purchase_price_000s = (scenario.purchase_price or 0) / 1000
    closing_costs_000s = (scenario.closing_costs or 0) / 1000
    loan_amount_000s = total_loan_amount / 1000
    property_tax_full = op_assumptions.get("property_tax_amount", 0)  # Keep in full dollars

    # Log input parameters for debugging
    logger.info(
        f"Calculating returns for scenario {scenario.id}: "
        f"total_sf={total_sf}, in_place_rent={in_place_rent}, "
        f"purchase_price={purchase_price_000s} ($000s), closing_costs={closing_costs_000s} ($000s), "
        f"loan_amount={loan_amount_000s} ($000s), property_tax={property_tax_full} (full $), "
        f"exit_cap={scenario.exit_cap_rate}"
    )

    # Generate dates
    dates = cashflow.generate_monthly_dates(
        scenario.acquisition_date, scenario.hold_period_months or 120
    )

    # Generate cash flows
    # Note: purchase_price, closing_costs, loan_amount in $000s
    # property_tax_amount in full dollars (module converts internally)
    # rent/expense PSF values in $/SF (module converts internally)
    monthly_cfs = cashflow.generate_cash_flows(
        acquisition_date=scenario.acquisition_date,
        hold_period_months=scenario.hold_period_months or 120,
        purchase_price=purchase_price_000s,
        closing_costs=closing_costs_000s,
        total_sf=total_sf,
        in_place_rent_psf=in_place_rent,
        market_rent_psf=op_assumptions.get("market_rent_psf", 300),
        rent_growth=op_assumptions.get("revenue_growth", 0.025),
        vacancy_rate=op_assumptions.get("vacancy_rate", 0),
        fixed_opex_psf=op_assumptions.get("fixed_opex_psf", 36),
        management_fee_percent=op_assumptions.get("management_fee_percent", 0.04),
        property_tax_amount=property_tax_full,
        capex_reserve_psf=op_assumptions.get("capex_reserve_psf", 5),
        expense_growth=op_assumptions.get("expense_growth", 0.025),
        exit_cap_rate=scenario.exit_cap_rate or 0.05,
        sales_cost_percent=scenario.sales_cost_percent or 0.01,
        loan_amount=loan_amount_000s,
        interest_rate=primary_rate,
        io_months=primary_io_months,
        amortization_years=primary_amort_years,
    )

    # Extract cash flow arrays
    unleveraged_cf = [cf["unleveraged_cash_flow"] for cf in monthly_cfs]
    leveraged_cf = [cf["leveraged_cash_flow"] for cf in monthly_cfs]

    # Log cash flow summary for debugging
    logger.info(
        f"Cash flow summary: unlev_cf[0]={unleveraged_cf[0] if unleveraged_cf else 'N/A'}, "
        f"unlev_cf[-1]={unleveraged_cf[-1] if unleveraged_cf else 'N/A'}, "
        f"has_positive={any(cf > 0 for cf in unleveraged_cf)}, "
        f"has_negative={any(cf < 0 for cf in unleveraged_cf)}"
    )

    metrics = {}
    errors = []

    # Calculate unleveraged metrics
    try:
        metrics["unleveraged_irr"] = irr.calculate_xirr(unleveraged_cf, dates)
        metrics["unleveraged_multiple"] = irr.calculate_multiple(unleveraged_cf)
        metrics["unleveraged_profit"] = irr.calculate_profit(unleveraged_cf)
        logger.info(f"Unleveraged metrics: IRR={metrics['unleveraged_irr']:.4f}, Multiple={metrics['unleveraged_multiple']:.2f}")
    except Exception as e:
        error_msg = f"Unleveraged IRR calculation failed: {str(e)}"
        logger.error(error_msg)
        errors.append(error_msg)

    # Calculate leveraged metrics
    if total_loan_amount > 0:
        logger.info(
            f"Leveraged CF summary: lev_cf[0]={leveraged_cf[0] if leveraged_cf else 'N/A'}, "
            f"lev_cf[-1]={leveraged_cf[-1] if leveraged_cf else 'N/A'}"
        )
        try:
            metrics["leveraged_irr"] = irr.calculate_xirr(leveraged_cf, dates)
            metrics["leveraged_multiple"] = irr.calculate_multiple(leveraged_cf)
            metrics["leveraged_profit"] = irr.calculate_profit(leveraged_cf)
            logger.info(f"Leveraged metrics: IRR={metrics['leveraged_irr']:.4f}, Multiple={metrics['leveraged_multiple']:.2f}")
        except Exception as e:
            error_msg = f"Leveraged IRR calculation failed: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        # Calculate waterfall distributions
        wf_structure = scenario.waterfall_structure or {}
        # Total equity in $000s for consistency with cash flows
        total_equity = purchase_price_000s + closing_costs_000s - loan_amount_000s

        logger.info(f"Waterfall: total_equity={total_equity} ($000s), lp_share={wf_structure.get('lp_share', 0.90)}")

        if total_equity > 0:
            try:
                distributions = waterfall.calculate_waterfall_distributions(
                    leveraged_cash_flows=leveraged_cf,
                    dates=dates,
                    total_equity=total_equity,
                    lp_share=wf_structure.get("lp_share", 0.90),
                    gp_share=wf_structure.get("gp_share", 0.10),
                    pref_return=wf_structure.get("pref_return", 0.05),
                    compound_monthly=wf_structure.get("compound_monthly", False),
                )

                lp_equity = total_equity * wf_structure.get("lp_share", 0.90)
                gp_equity = total_equity * wf_structure.get("gp_share", 0.10)

                lp_cfs = waterfall.extract_lp_cash_flows(distributions, lp_equity)
                gp_cfs = waterfall.extract_gp_cash_flows(distributions, gp_equity)

                logger.info(
                    f"LP/GP CF: lp_cf[0]={lp_cfs[0] if lp_cfs else 'N/A'}, "
                    f"lp_cf[-1]={lp_cfs[-1] if lp_cfs else 'N/A'}, "
                    f"gp_cf[0]={gp_cfs[0] if gp_cfs else 'N/A'}, "
                    f"gp_cf[-1]={gp_cfs[-1] if gp_cfs else 'N/A'}"
                )

                try:
                    metrics["lp_irr"] = irr.calculate_xirr(lp_cfs, dates)
                    logger.info(f"LP IRR: {metrics['lp_irr']:.4f}")
                except Exception as e:
                    error_msg = f"LP IRR calculation failed: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

                try:
                    metrics["gp_irr"] = irr.calculate_xirr(gp_cfs, dates)
                    logger.info(f"GP IRR: {metrics['gp_irr']:.4f}")
                except Exception as e:
                    error_msg = f"GP IRR calculation failed: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            except Exception as e:
                error_msg = f"Waterfall calculation failed: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

    # Include errors in metrics for UI display
    if errors:
        metrics["_errors"] = errors

    return metrics


# ============= Endpoints =============


@router.get("/", response_model=ScenarioListResponse)
async def list_scenarios(
    property_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """List all scenarios, optionally filtered by property."""
    query = db.query(Scenario).filter(Scenario.is_deleted == False)

    if property_id:
        query = query.filter(Scenario.property_id == property_id)

    total = query.count()
    scenarios = query.offset(skip).limit(limit).all()

    return ScenarioListResponse(
        scenarios=[scenario_to_response(s, include_children=False) for s in scenarios],
        total=total,
    )


@router.post("/", status_code=201)
async def create_scenario(
    scenario_data: ScenarioCreate,
    db: Session = Depends(get_db),
):
    """Create a new scenario with leases and loans."""
    # Verify property exists
    db_property = (
        db.query(Property)
        .filter(
            Property.id == scenario_data.property_id, Property.is_deleted == False
        )
        .first()
    )

    if not db_property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Build operating assumptions dict
    operating_assumptions = {
        "market_rent_psf": scenario_data.market_rent_psf,
        "vacancy_rate": scenario_data.vacancy_rate,
        "collection_loss": scenario_data.collection_loss,
        "fixed_opex_psf": scenario_data.fixed_opex_psf,
        "variable_opex_psf": scenario_data.variable_opex_psf,
        "management_fee_percent": scenario_data.management_fee_percent,
        "property_tax_amount": scenario_data.property_tax_amount,
        "property_tax_millage": scenario_data.property_tax_millage,
        "capex_reserve_psf": scenario_data.capex_reserve_psf,
        "revenue_growth": scenario_data.revenue_growth,
        "expense_growth": scenario_data.expense_growth,
    }

    # Build waterfall structure dict
    waterfall_structure = {
        "lp_share": scenario_data.lp_share,
        "gp_share": scenario_data.gp_share,
        "pref_return": scenario_data.pref_return,
        "compound_monthly": scenario_data.compound_monthly,
        "hurdles": [h.model_dump() for h in scenario_data.waterfall_hurdles],
    }

    # Create scenario
    db_scenario = Scenario(
        property_id=scenario_data.property_id,
        name=scenario_data.name,
        description=scenario_data.description,
        is_base_case=scenario_data.is_base_case,
        acquisition_date=scenario_data.acquisition_date,
        hold_period_months=scenario_data.hold_period_months,
        stabilization_month=scenario_data.stabilization_month,
        purchase_price=scenario_data.purchase_price,
        closing_costs=scenario_data.closing_costs,
        exit_cap_rate=scenario_data.exit_cap_rate,
        sales_cost_percent=scenario_data.sales_cost_percent,
        operating_assumptions=operating_assumptions,
        waterfall_structure=waterfall_structure,
    )

    db.add(db_scenario)
    db.flush()  # Get the ID

    # Create leases
    for lease_data in scenario_data.leases:
        db_lease = Lease(
            scenario_id=db_scenario.id,
            tenant_name=lease_data.tenant_name,
            space_id=lease_data.space_id,
            rsf=lease_data.rsf,
            base_rent_psf=lease_data.base_rent_psf,
            market_rent_psf=lease_data.market_rent_psf,
            escalation_type=lease_data.escalation_type,
            escalation_value=lease_data.escalation_value,
            escalation_frequency=lease_data.escalation_frequency,
            lease_start=lease_data.lease_start,
            lease_end=lease_data.lease_end,
            free_rent_months=lease_data.free_rent_months,
            ti_allowance_psf=lease_data.ti_allowance_psf,
            ti_buildout_months=lease_data.ti_buildout_months,
            lc_percent_years_1_5=lease_data.lc_percent_years_1_5,
            lc_percent_years_6_plus=lease_data.lc_percent_years_6_plus,
            reimbursement_type=lease_data.reimbursement_type,
            recovery_percentage=lease_data.recovery_percentage,
            is_vacant=lease_data.is_vacant,
            options=lease_data.options,
        )
        db.add(db_lease)

    # Create loans
    for loan_data in scenario_data.loans:
        db_loan = Loan(
            scenario_id=db_scenario.id,
            name=loan_data.name,
            loan_type=loan_data.loan_type,
            amount=loan_data.amount,
            ltc_ratio=loan_data.ltc_ratio,
            ltv_ratio=loan_data.ltv_ratio,
            interest_type=loan_data.interest_type,
            fixed_rate=loan_data.fixed_rate,
            floating_spread=loan_data.floating_spread,
            index_type=loan_data.index_type,
            rate_floor=loan_data.rate_floor,
            rate_cap=loan_data.rate_cap,
            origination_fee_percent=loan_data.origination_fee_percent,
            closing_costs_percent=loan_data.closing_costs_percent,
            io_months=loan_data.io_months,
            amortization_years=loan_data.amortization_years,
            maturity_months=loan_data.maturity_months,
            start_month=loan_data.start_month,
            min_dscr=loan_data.min_dscr,
            debt_yield_test=loan_data.debt_yield_test,
        )
        db.add(db_loan)

    db.commit()
    db.refresh(db_scenario)

    # Calculate return metrics
    metrics = calculate_scenario_returns(db_scenario, db)
    db_scenario.return_metrics = metrics
    db.commit()

    return scenario_to_response(db_scenario)


@router.get("/{scenario_id}")
async def get_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
):
    """Get a scenario by ID with full details."""
    db_scenario = (
        db.query(Scenario)
        .filter(Scenario.id == scenario_id, Scenario.is_deleted == False)
        .first()
    )

    if not db_scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    return scenario_to_response(db_scenario)


@router.put("/{scenario_id}")
async def update_scenario(
    scenario_id: str,
    scenario_data: ScenarioUpdate,
    db: Session = Depends(get_db),
):
    """Update a scenario."""
    db_scenario = (
        db.query(Scenario)
        .filter(Scenario.id == scenario_id, Scenario.is_deleted == False)
        .first()
    )

    if not db_scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Update fields
    update_data = scenario_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_scenario, field, value)

    db.commit()

    # Recalculate returns
    metrics = calculate_scenario_returns(db_scenario, db)
    db_scenario.return_metrics = metrics
    db.commit()

    db.refresh(db_scenario)

    return scenario_to_response(db_scenario)


@router.delete("/{scenario_id}")
async def delete_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
):
    """Soft delete a scenario."""
    db_scenario = (
        db.query(Scenario)
        .filter(Scenario.id == scenario_id, Scenario.is_deleted == False)
        .first()
    )

    if not db_scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    db_scenario.is_deleted = True
    db.commit()

    return {"deleted": True, "id": scenario_id}


@router.post("/{scenario_id}/calculate")
async def calculate_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
):
    """Recalculate return metrics for a scenario."""
    db_scenario = (
        db.query(Scenario)
        .filter(Scenario.id == scenario_id, Scenario.is_deleted == False)
        .first()
    )

    if not db_scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    metrics = calculate_scenario_returns(db_scenario, db)
    db_scenario.return_metrics = metrics
    db.commit()

    return {
        "scenario_id": scenario_id,
        "metrics": metrics,
    }


@router.get("/{scenario_id}/cashflows")
async def get_scenario_cashflows(
    scenario_id: str,
    period_type: str = "monthly",
    db: Session = Depends(get_db),
):
    """Get cash flow projections for a scenario."""
    db_scenario = (
        db.query(Scenario)
        .filter(Scenario.id == scenario_id, Scenario.is_deleted == False)
        .first()
    )

    if not db_scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Get lease and loan data
    op_assumptions = db_scenario.operating_assumptions or {}
    leases = db_scenario.leases.filter_by(is_deleted=False).all()
    loans = db_scenario.loans.filter_by(is_deleted=False).all()

    total_sf = sum(l.rsf or 0 for l in leases) or op_assumptions.get("total_sf", 10000)
    in_place_rent = 0
    if leases:
        weighted_rent = sum((l.rsf or 0) * (l.base_rent_psf or 0) for l in leases)
        in_place_rent = weighted_rent / total_sf if total_sf > 0 else 0
    else:
        in_place_rent = op_assumptions.get("in_place_rent_psf", 200)

    loan_amount = 0
    rate = 0.05
    io_months = 120
    amort_years = 30

    if loans:
        primary_loan = loans[0]
        if primary_loan.amount:
            loan_amount = primary_loan.amount
        elif primary_loan.ltc_ratio and db_scenario.purchase_price:
            total_cost = db_scenario.purchase_price + (db_scenario.closing_costs or 0)
            loan_amount = total_cost * primary_loan.ltc_ratio
        rate = primary_loan.fixed_rate or 0.05
        io_months = primary_loan.io_months or 120
        amort_years = primary_loan.amortization_years or 30

    # Convert values from full dollars to $000s for the cashflow module
    # property_tax_amount stays in full dollars (module converts internally)
    purchase_price_000s = (db_scenario.purchase_price or 0) / 1000
    closing_costs_000s = (db_scenario.closing_costs or 0) / 1000
    loan_amount_000s = loan_amount / 1000
    property_tax_full = op_assumptions.get("property_tax_amount", 0)

    monthly_cfs = cashflow.generate_cash_flows(
        acquisition_date=db_scenario.acquisition_date,
        hold_period_months=db_scenario.hold_period_months or 120,
        purchase_price=purchase_price_000s,
        closing_costs=closing_costs_000s,
        total_sf=total_sf,
        in_place_rent_psf=in_place_rent,
        market_rent_psf=op_assumptions.get("market_rent_psf", 300),
        rent_growth=op_assumptions.get("revenue_growth", 0.025),
        vacancy_rate=op_assumptions.get("vacancy_rate", 0),
        fixed_opex_psf=op_assumptions.get("fixed_opex_psf", 36),
        management_fee_percent=op_assumptions.get("management_fee_percent", 0.04),
        property_tax_amount=property_tax_full,
        capex_reserve_psf=op_assumptions.get("capex_reserve_psf", 5),
        expense_growth=op_assumptions.get("expense_growth", 0.025),
        exit_cap_rate=db_scenario.exit_cap_rate or 0.05,
        sales_cost_percent=db_scenario.sales_cost_percent or 0.01,
        loan_amount=loan_amount_000s,
        interest_rate=rate,
        io_months=io_months,
        amortization_years=amort_years,
    )

    if period_type == "annual":
        return {
            "scenario_id": scenario_id,
            "period_type": "annual",
            "cashflows": cashflow.annualize_cash_flows(monthly_cfs),
        }

    return {
        "scenario_id": scenario_id,
        "period_type": "monthly",
        "cashflows": monthly_cfs,
    }


# ============= Lease Sub-endpoints =============


@router.post("/{scenario_id}/leases")
async def add_lease(
    scenario_id: str,
    lease_data: LeaseInput,
    db: Session = Depends(get_db),
):
    """Add a lease to a scenario."""
    db_scenario = (
        db.query(Scenario)
        .filter(Scenario.id == scenario_id, Scenario.is_deleted == False)
        .first()
    )

    if not db_scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    db_lease = Lease(
        scenario_id=scenario_id,
        tenant_name=lease_data.tenant_name,
        space_id=lease_data.space_id,
        rsf=lease_data.rsf,
        base_rent_psf=lease_data.base_rent_psf,
        market_rent_psf=lease_data.market_rent_psf,
        escalation_type=lease_data.escalation_type,
        escalation_value=lease_data.escalation_value,
        escalation_frequency=lease_data.escalation_frequency,
        lease_start=lease_data.lease_start,
        lease_end=lease_data.lease_end,
        free_rent_months=lease_data.free_rent_months,
        ti_allowance_psf=lease_data.ti_allowance_psf,
        ti_buildout_months=lease_data.ti_buildout_months,
        lc_percent_years_1_5=lease_data.lc_percent_years_1_5,
        lc_percent_years_6_plus=lease_data.lc_percent_years_6_plus,
        reimbursement_type=lease_data.reimbursement_type,
        recovery_percentage=lease_data.recovery_percentage,
        is_vacant=lease_data.is_vacant,
        options=lease_data.options,
    )

    db.add(db_lease)
    db.commit()
    db.refresh(db_lease)

    return {
        "id": db_lease.id,
        "tenant_name": db_lease.tenant_name,
        "space_id": db_lease.space_id,
        "rsf": db_lease.rsf,
        "base_rent_psf": db_lease.base_rent_psf,
    }


@router.delete("/{scenario_id}/leases/{lease_id}")
async def remove_lease(
    scenario_id: str,
    lease_id: str,
    db: Session = Depends(get_db),
):
    """Remove a lease from a scenario."""
    db_lease = (
        db.query(Lease)
        .filter(
            Lease.id == lease_id,
            Lease.scenario_id == scenario_id,
            Lease.is_deleted == False,
        )
        .first()
    )

    if not db_lease:
        raise HTTPException(status_code=404, detail="Lease not found")

    db_lease.is_deleted = True
    db.commit()

    return {"deleted": True, "id": lease_id}


# ============= Loan Sub-endpoints =============


@router.post("/{scenario_id}/loans")
async def add_loan(
    scenario_id: str,
    loan_data: LoanInput,
    db: Session = Depends(get_db),
):
    """Add a loan to a scenario."""
    db_scenario = (
        db.query(Scenario)
        .filter(Scenario.id == scenario_id, Scenario.is_deleted == False)
        .first()
    )

    if not db_scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    db_loan = Loan(
        scenario_id=scenario_id,
        name=loan_data.name,
        loan_type=loan_data.loan_type,
        amount=loan_data.amount,
        ltc_ratio=loan_data.ltc_ratio,
        ltv_ratio=loan_data.ltv_ratio,
        interest_type=loan_data.interest_type,
        fixed_rate=loan_data.fixed_rate,
        floating_spread=loan_data.floating_spread,
        index_type=loan_data.index_type,
        rate_floor=loan_data.rate_floor,
        rate_cap=loan_data.rate_cap,
        origination_fee_percent=loan_data.origination_fee_percent,
        closing_costs_percent=loan_data.closing_costs_percent,
        io_months=loan_data.io_months,
        amortization_years=loan_data.amortization_years,
        maturity_months=loan_data.maturity_months,
        start_month=loan_data.start_month,
        min_dscr=loan_data.min_dscr,
        debt_yield_test=loan_data.debt_yield_test,
    )

    db.add(db_loan)
    db.commit()
    db.refresh(db_loan)

    return {
        "id": db_loan.id,
        "name": db_loan.name,
        "loan_type": db_loan.loan_type,
        "amount": db_loan.amount,
    }


@router.delete("/{scenario_id}/loans/{loan_id}")
async def remove_loan(
    scenario_id: str,
    loan_id: str,
    db: Session = Depends(get_db),
):
    """Remove a loan from a scenario."""
    db_loan = (
        db.query(Loan)
        .filter(
            Loan.id == loan_id,
            Loan.scenario_id == scenario_id,
            Loan.is_deleted == False,
        )
        .first()
    )

    if not db_loan:
        raise HTTPException(status_code=404, detail="Loan not found")

    db_loan.is_deleted = True
    db.commit()

    return {"deleted": True, "id": loan_id}
