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
    event,
    Enum as SQLEnum,
)
from sqlalchemy.orm import declarative_base, relationship
import uuid
import enum


class UserRole(str, enum.Enum):
    """User role enumeration."""
    admin = "admin"
    user = "user"

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


class AuditMixin:
    """Mixin for audit fields on all models."""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    created_by = Column(String(255), nullable=True)
    updated_by = Column(String(255), nullable=True)
    is_deleted = Column(Boolean, default=False, nullable=False)


class User(AuditMixin, Base):
    """User model for authentication and authorization."""

    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable until invite accepted

    # Profile
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Role and status
    role = Column(SQLEnum(UserRole), default=UserRole.user, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)

    # Timestamps for auth events
    last_login_at = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)

    # Relationships
    properties = relationship(
        "Property",
        back_populates="owner",
        foreign_keys="Property.owner_id",
        lazy="dynamic",
    )
    invite_tokens = relationship(
        "InviteToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )
    refresh_tokens = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )


class Property(AuditMixin, Base):
    """Property model representing a real estate asset."""

    __tablename__ = "properties"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)

    # Owner (for access control)
    owner_id = Column(String, ForeignKey("users.id"), nullable=True)

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
    acquisition_date = Column(Date)

    # Purchase info
    purchase_price = Column(Float)
    closing_costs_percent = Column(Float, default=0.02)

    # Relationships
    owner = relationship("User", back_populates="properties", foreign_keys=[owner_id])
    scenarios = relationship(
        "Scenario",
        back_populates="property",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )


class Scenario(AuditMixin, Base):
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
    operating_assumptions = Column(JSON, default=dict)

    # Exit assumptions
    exit_cap_rate = Column(Float, default=0.05)
    sales_cost_percent = Column(Float, default=0.01)

    # Waterfall structure (stored as JSON)
    waterfall_structure = Column(JSON, default=dict)

    # Calculated results (cached)
    return_metrics = Column(JSON, default=dict)

    # Relationships
    property = relationship("Property", back_populates="scenarios")
    leases = relationship(
        "Lease", back_populates="scenario", cascade="all, delete-orphan", lazy="dynamic"
    )
    loans = relationship(
        "Loan", back_populates="scenario", cascade="all, delete-orphan", lazy="dynamic"
    )


class Lease(AuditMixin, Base):
    """Lease model for tenant information."""

    __tablename__ = "leases"

    id = Column(String, primary_key=True, default=generate_uuid)
    scenario_id = Column(String, ForeignKey("scenarios.id"), nullable=False)

    # Tenant info
    tenant_name = Column(String(255), nullable=False)
    space_id = Column(String(50))

    # Space details
    rsf = Column(Float)  # Rentable Square Feet
    usf = Column(Float)  # Usable Square Feet (if different)

    # Rent structure
    base_rent_psf = Column(Float)
    market_rent_psf = Column(Float)
    escalation_type = Column(String(20), default="percentage")
    escalation_value = Column(Float, default=0.025)
    escalation_frequency = Column(String(20), default="annual")

    # Lease term
    lease_start = Column(Date)
    lease_end = Column(Date)

    # Options (stored as JSON array)
    options = Column(JSON, default=list)

    # Concessions
    free_rent_months = Column(Integer, default=0)
    free_rent_start_month = Column(Integer, default=0)
    ti_allowance_psf = Column(Float, default=0)
    ti_buildout_months = Column(Integer, default=6)

    # Commissions
    lc_percent_years_1_5 = Column(Float, default=0.06)
    lc_percent_years_6_plus = Column(Float, default=0.03)

    # Reimbursements
    reimbursement_type = Column(String(20), default="NNN")
    recovery_percentage = Column(Float, default=1.0)

    # Status
    is_vacant = Column(Boolean, default=False)
    is_month_to_month = Column(Boolean, default=False)

    # Rollover behavior (Excel H-column equivalent)
    # True = apply TI/LC/Free Rent at lease rollover (H=0 in Excel)
    # False = no rollover costs, immediate transition to market (H=1 in Excel)
    apply_rollover_costs = Column(Boolean, default=True)

    # Relationships
    scenario = relationship("Scenario", back_populates="leases")


class Loan(AuditMixin, Base):
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
    index_type = Column(String(20), default="SOFR")
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

    # Debt sizing constraints
    min_dscr = Column(Float, default=1.25)
    max_ltv = Column(Float, default=0.75)
    debt_yield_test = Column(Float, default=0.065)

    # Prepayment
    prepayment_type = Column(String(20), default="open")
    prepayment_penalty_percent = Column(Float, default=0.0)

    # Relationships
    scenario = relationship("Scenario", back_populates="loans")


class SOFRRate(AuditMixin, Base):
    """SOFR forward curve rate data."""

    __tablename__ = "sofr_rates"

    id = Column(String, primary_key=True, default=generate_uuid)
    rate_date = Column(Date, nullable=False, index=True)
    rate_value = Column(Float, nullable=False)
    rate_type = Column(String(20), default="1M")  # 1M, 3M, 6M SOFR


class CashFlowCache(AuditMixin, Base):
    """Cached cash flow calculations for a scenario."""

    __tablename__ = "cashflow_cache"

    id = Column(String, primary_key=True, default=generate_uuid)
    scenario_id = Column(String, ForeignKey("scenarios.id"), nullable=False, index=True)
    period = Column(Integer, nullable=False)
    period_date = Column(Date)

    # Revenue
    potential_revenue = Column(Float, default=0)
    vacancy_loss = Column(Float, default=0)
    effective_revenue = Column(Float, default=0)

    # Expenses
    total_expenses = Column(Float, default=0)

    # NOI
    noi = Column(Float, default=0)

    # Capital events
    acquisition_costs = Column(Float, default=0)
    exit_proceeds = Column(Float, default=0)

    # Debt
    debt_service = Column(Float, default=0)

    # Cash flows
    unleveraged_cf = Column(Float, default=0)
    leveraged_cf = Column(Float, default=0)


class InviteToken(AuditMixin, Base):
    """Invite token for user registration."""

    __tablename__ = "invite_tokens"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="invite_tokens")


class PasswordResetToken(AuditMixin, Base):
    """Password reset token."""

    __tablename__ = "password_reset_tokens"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used_at = Column(DateTime, nullable=True)


class RefreshToken(AuditMixin, Base):
    """Refresh token for JWT authentication."""

    __tablename__ = "refresh_tokens"

    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(255), nullable=False, index=True)  # Store hash, not token
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    device_info = Column(String(255), nullable=True)  # Optional: store device/browser info

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")
