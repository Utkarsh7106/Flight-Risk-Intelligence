"""Idempotent seed: the real org structure (business units + departments)
and two test app_user accounts for exercising login/RLS locally.

Run with the migrator role so it can write reference data regardless of
RLS (business_unit/department carry no RLS anyway, app_user carries none
either — see ARCHITECTURE.md). No employee rows are seeded here: the
baseline ~320-row panel is loaded separately once available.

    cd backend && source .venv/bin/activate && python scripts/seed_reference_data.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.app_user import AppUser
from app.models.business_unit import BusinessUnit
from app.models.department import Department
from app.security.password import hash_password

ORG_STRUCTURE = {
    "Business Function and Media": [
        "Bidable Performance",
        "Client Success",
        "Growth and Strategy",
        "Growth",
        "Pragmatic Buying",
        "SEO",
    ],
    "Data Quark": [
        "Data Quark Sales",
        "Digital Analytics",
        "Product and Consulting",
        "Unified Data Solutions",
    ],
    "Enabling Functions": [
        "Finance",
        "Growth",
        "Marketing and PR",
        "People Management",
    ],
    "SP Creative": [
        "Administration",
        "Finance and Accounting",
        "Social",
        "Strategy and Growth",
    ],
    "UI/UX": ["Design"],
}

# Test accounts only — not real LS Digital personnel. Indian names per
# ARCHITECTURE.md's naming rule.
TEST_ACCOUNTS = [
    {
        "email": "priya.sharma@lsdigital-demo.com",
        "password": "ChangeMe123!",
        "full_name": "Priya Sharma",
        "role": "hr",
        "business_unit_name": None,
    },
    {
        "email": "arjun.mehta@lsdigital-demo.com",
        "password": "ChangeMe123!",
        "full_name": "Arjun Mehta",
        "role": "bu_head",
        "business_unit_name": "Data Quark",
    },
]


def seed(db: Session) -> None:
    bu_by_name: dict[str, BusinessUnit] = {}
    for bu_name in ORG_STRUCTURE:
        bu = db.scalar(select(BusinessUnit).where(BusinessUnit.name == bu_name))
        if bu is None:
            bu = BusinessUnit(name=bu_name)
            db.add(bu)
            db.flush()
            print(f"created business_unit: {bu_name}")
        bu_by_name[bu_name] = bu

    for bu_name, dept_names in ORG_STRUCTURE.items():
        bu = bu_by_name[bu_name]
        for dept_name in dept_names:
            dept = db.scalar(
                select(Department).where(
                    Department.business_unit_id == bu.id, Department.name == dept_name
                )
            )
            if dept is None:
                db.add(Department(business_unit_id=bu.id, name=dept_name))
                print(f"created department: {bu_name} / {dept_name}")

    db.flush()

    for account in TEST_ACCOUNTS:
        existing = db.scalar(select(AppUser).where(AppUser.email == account["email"]))
        if existing is not None:
            continue

        business_unit_id = None
        if account["business_unit_name"] is not None:
            business_unit_id = bu_by_name[account["business_unit_name"]].id

        db.add(
            AppUser(
                email=account["email"],
                password_hash=hash_password(account["password"]),
                full_name=account["full_name"],
                role=account["role"],
                business_unit_id=business_unit_id,
            )
        )
        print(f"created app_user: {account['email']} ({account['role']})")

    db.commit()


def main() -> None:
    url = settings.migrations_database_url or settings.database_url
    engine = create_engine(url)
    with Session(engine) as db:
        seed(db)


if __name__ == "__main__":
    main()
