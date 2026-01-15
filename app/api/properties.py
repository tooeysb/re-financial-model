"""
Property management API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Property

router = APIRouter()


class PropertyCreate(BaseModel):
    """Schema for creating a property."""

    name: str
    address_street: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_zip: Optional[str] = None
    property_type: str = "retail"
    land_sf: Optional[float] = None
    building_sf: Optional[float] = None
    net_rentable_sf: Optional[float] = None
    year_built: Optional[int] = None
    acquisition_date: Optional[date] = None
    purchase_price: Optional[float] = None
    closing_costs_percent: float = 0.02


class PropertyUpdate(BaseModel):
    """Schema for updating a property."""

    name: Optional[str] = None
    address_street: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_zip: Optional[str] = None
    property_type: Optional[str] = None
    land_sf: Optional[float] = None
    building_sf: Optional[float] = None
    net_rentable_sf: Optional[float] = None
    year_built: Optional[int] = None
    acquisition_date: Optional[date] = None
    purchase_price: Optional[float] = None
    closing_costs_percent: Optional[float] = None


class PropertyResponse(BaseModel):
    """Schema for property response."""

    id: str
    name: str
    address_street: Optional[str]
    address_city: Optional[str]
    address_state: Optional[str]
    address_zip: Optional[str]
    property_type: str
    land_sf: Optional[float]
    building_sf: Optional[float]
    net_rentable_sf: Optional[float]
    year_built: Optional[int]
    acquisition_date: Optional[date]
    purchase_price: Optional[float]
    closing_costs_percent: Optional[float]
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    class Config:
        from_attributes = True


class PropertyListResponse(BaseModel):
    """Response for listing properties."""

    properties: List[PropertyResponse]
    total: int


def property_to_response(prop: Property) -> PropertyResponse:
    """Convert Property model to response schema."""
    return PropertyResponse(
        id=prop.id,
        name=prop.name,
        address_street=prop.address_street,
        address_city=prop.address_city,
        address_state=prop.address_state,
        address_zip=prop.address_zip,
        property_type=prop.property_type or "retail",
        land_sf=prop.land_sf,
        building_sf=prop.building_sf,
        net_rentable_sf=prop.net_rentable_sf,
        year_built=prop.year_built,
        acquisition_date=prop.acquisition_date,
        purchase_price=prop.purchase_price,
        closing_costs_percent=prop.closing_costs_percent,
        created_at=prop.created_at.isoformat() if prop.created_at else None,
        updated_at=prop.updated_at.isoformat() if prop.updated_at else None,
    )


@router.get("/", response_model=PropertyListResponse)
async def list_properties(
    skip: int = 0,
    limit: int = 100,
    property_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all properties with optional filtering."""
    query = db.query(Property).filter(Property.is_deleted == False)

    if property_type:
        query = query.filter(Property.property_type == property_type)

    total = query.count()
    properties = query.offset(skip).limit(limit).all()

    return PropertyListResponse(
        properties=[property_to_response(p) for p in properties],
        total=total,
    )


@router.post("/", response_model=PropertyResponse, status_code=201)
async def create_property(
    property_data: PropertyCreate,
    db: Session = Depends(get_db),
):
    """Create a new property."""
    db_property = Property(
        name=property_data.name,
        address_street=property_data.address_street,
        address_city=property_data.address_city,
        address_state=property_data.address_state,
        address_zip=property_data.address_zip,
        property_type=property_data.property_type,
        land_sf=property_data.land_sf,
        building_sf=property_data.building_sf,
        net_rentable_sf=property_data.net_rentable_sf,
        year_built=property_data.year_built,
        acquisition_date=property_data.acquisition_date,
        purchase_price=property_data.purchase_price,
        closing_costs_percent=property_data.closing_costs_percent,
    )

    db.add(db_property)
    db.commit()
    db.refresh(db_property)

    return property_to_response(db_property)


@router.get("/{property_id}", response_model=PropertyResponse)
async def get_property(
    property_id: str,
    db: Session = Depends(get_db),
):
    """Get a property by ID."""
    db_property = (
        db.query(Property)
        .filter(Property.id == property_id, Property.is_deleted == False)
        .first()
    )

    if not db_property:
        raise HTTPException(status_code=404, detail="Property not found")

    return property_to_response(db_property)


@router.put("/{property_id}", response_model=PropertyResponse)
async def update_property(
    property_id: str,
    property_data: PropertyUpdate,
    db: Session = Depends(get_db),
):
    """Update a property."""
    db_property = (
        db.query(Property)
        .filter(Property.id == property_id, Property.is_deleted == False)
        .first()
    )

    if not db_property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Update only provided fields
    update_data = property_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_property, field, value)

    db.commit()
    db.refresh(db_property)

    return property_to_response(db_property)


@router.delete("/{property_id}")
async def delete_property(
    property_id: str,
    db: Session = Depends(get_db),
):
    """Soft delete a property."""
    db_property = (
        db.query(Property)
        .filter(Property.id == property_id, Property.is_deleted == False)
        .first()
    )

    if not db_property:
        raise HTTPException(status_code=404, detail="Property not found")

    # Soft delete
    db_property.is_deleted = True
    db.commit()

    return {"deleted": True, "id": property_id}


@router.get("/{property_id}/scenarios")
async def list_property_scenarios(
    property_id: str,
    db: Session = Depends(get_db),
):
    """List all scenarios for a property."""
    db_property = (
        db.query(Property)
        .filter(Property.id == property_id, Property.is_deleted == False)
        .first()
    )

    if not db_property:
        raise HTTPException(status_code=404, detail="Property not found")

    scenarios = db_property.scenarios.filter_by(is_deleted=False).all()

    return {
        "property_id": property_id,
        "scenarios": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "is_base_case": s.is_base_case,
                "return_metrics": s.return_metrics,
            }
            for s in scenarios
        ],
        "total": len(scenarios),
    }
