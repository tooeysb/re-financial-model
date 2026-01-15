"""
Scenario management API endpoints.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import date

router = APIRouter()


class LeaseInput(BaseModel):
    """Lease input schema."""

    tenant_name: str
    space_id: str
    rsf: float
    base_rent_psf: float
    escalation_rate: float = 0.025
    lease_start: date
    lease_end: date
    free_rent_months: int = 0
    ti_allowance_psf: float = 0
    lc_percent: float = 0.06


class LoanInput(BaseModel):
    """Loan input schema."""

    name: str
    loan_type: str = "acquisition"
    amount: Optional[float] = None
    ltc_ratio: Optional[float] = 0.555
    interest_type: str = "fixed"
    fixed_rate: float = 0.05
    floating_spread: Optional[float] = None
    io_months: int = 120
    amortization_years: int = 30
    start_month: int = 0


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

    # Leases
    leases: List[LeaseInput] = []

    # Loans
    loans: List[LoanInput] = []


class ScenarioResponse(BaseModel):
    """Schema for scenario response."""

    id: str
    property_id: str
    name: str
    description: Optional[str]
    is_base_case: bool


@router.get("/")
async def list_scenarios(property_id: Optional[str] = None):
    """List all scenarios, optionally filtered by property."""
    # TODO: Implement database query
    return {"scenarios": [], "total": 0}


@router.post("/", response_model=ScenarioResponse)
async def create_scenario(scenario_data: ScenarioCreate):
    """Create a new scenario."""
    # TODO: Implement database insert
    return {
        "id": "temp-id",
        "property_id": scenario_data.property_id,
        "name": scenario_data.name,
        "description": scenario_data.description,
        "is_base_case": scenario_data.is_base_case,
    }


@router.get("/{scenario_id}")
async def get_scenario(scenario_id: str):
    """Get a scenario by ID with full details."""
    # TODO: Implement database query
    raise HTTPException(status_code=404, detail="Scenario not found")


@router.put("/{scenario_id}")
async def update_scenario(scenario_id: str, scenario_data: ScenarioCreate):
    """Update a scenario."""
    # TODO: Implement database update
    raise HTTPException(status_code=404, detail="Scenario not found")


@router.delete("/{scenario_id}")
async def delete_scenario(scenario_id: str):
    """Delete a scenario."""
    # TODO: Implement database delete
    return {"deleted": True}
