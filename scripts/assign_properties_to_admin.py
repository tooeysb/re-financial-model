"""
Assign all existing properties to the admin user.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
from app.db.models import Property, User

def main():
    db = SessionLocal()

    try:
        # Get admin user
        admin = db.query(User).filter(User.email == "tooey@hth-corp.com").first()
        if not admin:
            print("Admin user not found!")
            return

        print(f"Admin user ID: {admin.id}")

        # Get all properties
        properties = db.query(Property).all()
        print(f"Total properties: {len(properties)}")

        if not properties:
            print("No properties found in database.")
            return

        # Update properties without owner or assign all to admin
        updated = 0
        for p in properties:
            print(f"  - {p.name} (ID: {p.id}, current owner_id: {p.owner_id})")
            if p.owner_id != admin.id:
                p.owner_id = admin.id
                updated += 1
                print(f"    -> Assigned to admin")

        if updated > 0:
            db.commit()
            print(f"\nUpdated {updated} properties to admin ownership.")
        else:
            print("\nAll properties already owned by admin.")

    finally:
        db.close()

if __name__ == "__main__":
    main()
