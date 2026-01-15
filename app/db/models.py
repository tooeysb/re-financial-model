"""
SQLAlchemy ORM models for the financial model.
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    JSON,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship
import uuid

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


class Property(Base):
    """Property model representing a real estate asset."""

    __tablename__ = "properties"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)

    # Address
    address_street = Column(String(255))
    address_city = Column(String(100))
    address_state = Column(String(50))
    address_zip = Column(String(20))

    # Property details
    property_type = Column(String(50), default="retail")
    land_sf = Column(Float)
    building_sf = Column(Float)
    net_rentable_sf = Column(Float)
    year_built = Column(Integer)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    scenarios = relationship("Scenario", back_populates="property", cascade="all, delete-orphan")


class Scenario(Base):
    """Scenario model for financial analysis scenarios."""

    __tablename__ = "scenarios"

    id = Column(String, primary_key=True, default=generate_uuid)
    property_id = Column(String, ForeignKey("properties.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_base_case = Column(Boolean, default=False)

    # Timing
    acquisition_date = Column(Date)
    hold_period_months = Column(Integer, default=120)
    stabilization_month = Column(Integer, default=77)

    # Acquisition
    purchase_price = Column(Float)
    closing_costs = Column(Float)

    # Operating assumptions (stored as JSON for flexibility)
    operating_assumptions = Column(JSON)

    # Exit assumptions
    exit_cap_rate = Column(Float, default=0.05)
    sales_cost_percent = Column(Float, default=0.01)

    # Waterfall structure (stored as JSON)
    waterfall_structure = Column(JSON)

    # Calculated results (cached)
    return_metrics = Column(JSON)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    property = relationship("Property", back_populates="scenarios")
    leases = relationship("Lease", back_populates="scenario", cascade="all, delete-orphan")
    loans = relationship("Loan", back_populates="scenario", cascade="all, delete-orphan")


class Lease(Base):
    """Lease model for tenant information."""

    __tablename__ = "leases"

    id = Column(String, primary_key=True, default=generate_uuid)
    scenario_id = Column(String, ForeignKey("scenarios.id"), nullable=False)

    # Tenant info
    tenant_name = Column(String(255), nullable=False)
    space_id = Column(String(50))

    # Space details
    rsf = Column(Float)  # Rentable Square Feet

    # Rent structure
    base_rent_psf = Column(Float)
    escalation_type = Column(String(20), default="percentage")
    escalation_value = Column(Float, default=0.025)
    escalation_frequency = Column(String(20), default="annual")

    # Lease term
    lease_start = Column(Date)
    lease_end = Column(Date)

    # Options (stored as JSON)
    options = Column(JSON)

    # Concessions
    free_rent_months = Column(Integer, default=0)
    ti_allowance_psf = Column(Float, default=0)

    # Commissions
    lc_percent_years_1_5 = Column(Float, default=0.06)
    lc_percent_years_6_plus = Column(Float, default=0.03)

    # Reimbursements
    reimbursement_type = Column(String(20), default="NNN")
    recovery_percentage = Column(Float, default=1.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    scenario = relationship("Scenario", back_populates="leases")


class Loan(Base):
    """Loan model for financing structures."""

    __tablename__ = "loans"

    id = Column(String, primary_key=True, default=generate_uuid)
    scenario_id = Column(String, ForeignKey("scenarios.id"), nullable=False)

    name = Column(String(255))
    loan_type = Column(String(50), default="acquisition")

    # Amount
    amount = Column(Float)
    ltc_ratio = Column(Float)
    ltv_ratio = Column(Float)

    # Interest rate
    interest_type = Column(String(20), default="fixed")
    fixed_rate = Column(Float)
    floating_spread = Column(Float)
    index_type = Column(String(20))
    rate_floor = Column(Float)
    rate_cap = Column(Float)

    # Fees
    origination_fee_percent = Column(Float, default=0.01)
    closing_costs_percent = Column(Float, default=0.01)

    # Term structure
    io_months = Column(Integer, default=0)
    amortization_years = Column(Integer, default=30)
    maturity_months = Column(Integer, default=120)
    start_month = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    scenario = relationship("Scenario", back_populates="loans")
