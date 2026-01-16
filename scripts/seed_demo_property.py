"""
Seed the database with the 225 Worth Ave demo property.
Based on the PRD documentation.
"""
import sys
import os
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.db.models import Property, Scenario, User

def main():
    db = SessionLocal()

    try:
        # Get admin user
        admin = db.query(User).filter(User.email == "tooey@hth-corp.com").first()
        if not admin:
            print("Admin user not found! Run create_initial_admin.py first.")
            return

        print(f"Admin user: {admin.email} (ID: {admin.id})")

        # Check if property already exists
        existing = db.query(Property).filter(Property.name == "225 Worth Ave").first()
        if existing:
            print(f"Property '225 Worth Ave' already exists (ID: {existing.id})")
            return

        # Create 225 Worth Ave property
        property = Property(
            name="225 Worth Ave",
            owner_id=admin.id,
            address_street="225 Worth Ave",
            address_city="Palm Beach",
            address_state="FL",
            address_zip="33480",
            property_type="retail",
            building_sf=9932,
            net_rentable_sf=9932,
            purchase_price=41500000,
        )
        db.add(property)
        db.flush()
        print(f"Created property: {property.name} (ID: {property.id})")

        # Create base case scenario with operating assumptions in JSON
        operating_assumptions = {
            # Revenue assumptions
            "total_sf": 9932,
            "in_place_rent_psf": 200.0,  # High-end Palm Beach retail
            "market_rent_psf": 220.0,
            "vacancy_rate": 0.05,
            "rent_growth": 0.025,
            # Expense assumptions
            "fixed_opex_psf": 36.0,
            "management_fee_percent": 0.04,
            "property_tax_amount": 415000,  # ~1% of value
            "capex_reserve_psf": 5.0,
            "expense_growth": 0.025,
            # Financing (optional - for leveraged scenario)
            "loan_amount": 27000000,  # ~65% LTV
            "interest_rate": 0.055,
            "io_months": 36,
            "amortization_years": 30,
        }

        scenario = Scenario(
            property_id=property.id,
            name="Base Case",
            is_base_case=True,
            acquisition_date=date(2025, 1, 1),
            hold_period_months=120,  # 10 years
            purchase_price=41500000,
            closing_costs=622500,  # 1.5% of purchase price
            exit_cap_rate=0.05,
            sales_cost_percent=0.02,
            operating_assumptions=operating_assumptions,
        )
        db.add(scenario)
        db.flush()
        print(f"Created scenario: {scenario.name} (ID: {scenario.id})")

        db.commit()
        print("\nDemo property and scenario created successfully!")
        print(f"\nYou can now access it at:")
        print(f"  https://re-fin-model-225worth-3348ecdc48e8.herokuapp.com/model/{property.id}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
