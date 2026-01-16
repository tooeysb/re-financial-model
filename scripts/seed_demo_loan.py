"""
Seed financing/loan for the 225 Worth Ave demo property.
Based on the PRD documentation.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.db.models import Property, Scenario, Loan

def main():
    db = SessionLocal()

    try:
        # Find the 225 Worth Ave property
        property = db.query(Property).filter(Property.name == "225 Worth Ave").first()
        if not property:
            print("Property '225 Worth Ave' not found! Run seed_demo_property.py first.")
            return

        print(f"Found property: {property.name} (ID: {property.id})")

        # Find the Base Case scenario
        scenario = db.query(Scenario).filter(
            Scenario.property_id == property.id,
            Scenario.is_base_case == True
        ).first()
        if not scenario:
            print("Base Case scenario not found!")
            return

        print(f"Found scenario: {scenario.name} (ID: {scenario.id})")

        # Check if loan already exists
        existing_loan = db.query(Loan).filter(Loan.scenario_id == scenario.id).first()
        if existing_loan:
            print(f"Loan already exists: {existing_loan.name}. Skipping.")
            return

        # Create the acquisition loan
        # Purchase price: $41.5M, Loan: $27M (~65% LTV)
        loan = Loan(
            scenario_id=scenario.id,
            name="Senior Acquisition Loan",
            loan_type="acquisition",

            # Amount
            amount=27000000,
            ltv_ratio=0.65,

            # Interest rate
            interest_type="fixed",
            fixed_rate=0.055,  # 5.5%

            # Fees
            origination_fee_percent=0.01,
            closing_costs_percent=0.005,

            # Term structure
            io_months=36,  # 3 years interest-only
            amortization_years=30,
            maturity_months=120,  # 10 year term
            start_month=0,

            # Debt sizing constraints
            min_dscr=1.25,
            max_ltv=0.75,
        )
        db.add(loan)
        db.commit()

        print(f"\nCreated loan: {loan.name}")
        print(f"  Amount: ${loan.amount:,.0f}")
        print(f"  Rate: {loan.fixed_rate:.2%}")
        print(f"  I/O Period: {loan.io_months} months")
        print(f"  Amortization: {loan.amortization_years} years")
        print(f"  Term: {loan.maturity_months} months")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
