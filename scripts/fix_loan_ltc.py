"""
Fix the loan LTC ratio that wasn't set.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.db.models import Loan

def main():
    db = SessionLocal()

    try:
        # Find and update the loan
        loan = db.query(Loan).filter(Loan.name == "Senior Acquisition Loan").first()
        if not loan:
            print("Loan not found!")
            return

        print(f"Found loan: {loan.name}")
        print(f"  Current ltc_ratio: {loan.ltc_ratio}")
        print(f"  Current ltv_ratio: {loan.ltv_ratio}")

        # Set LTC ratio to 0.65 (65%)
        loan.ltc_ratio = 0.65
        db.commit()

        print(f"\nUpdated ltc_ratio to: {loan.ltc_ratio}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
