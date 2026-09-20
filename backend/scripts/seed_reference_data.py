"""Idempotent seed: the real org structure (business units + departments),
two test app_user accounts for exercising login/RLS locally, and a small
illustrative batch of ~18 employees spread across all 5 business units so
the directory endpoint has something realistic to look at through /docs.

This is NOT the ~320-row baseline panel referenced in ARCHITECTURE.md —
that dataset is loaded separately once available. These rows exist purely
so HR/BU Head logins have a meaningfully different-looking slice to
eyeball locally.

Run with the migrator role so it can write reference data regardless of
RLS (business_unit/department/app_user carry no RLS at all; employee DOES
carry RLS but fri_migrator bypasses it as table owner — see
ARCHITECTURE.md).

    cd backend && source .venv/bin/activate && python scripts/seed_reference_data.py
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.app_user import AppUser
from app.models.business_unit import BusinessUnit
from app.models.department import Department
from app.models.employee import Employee
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
    {
        "email": "meenakshi.reddy@lsdigital-demo.com",
        "password": "ChangeMe123!",
        "full_name": "Meenakshi Reddy",
        "role": "bu_head",
        "business_unit_name": "Business Function and Media",
    },
    {
        "email": "siddharth.agarwal@lsdigital-demo.com",
        "password": "ChangeMe123!",
        "full_name": "Siddharth Agarwal",
        "role": "bu_head",
        "business_unit_name": "Enabling Functions",
    },
    {
        "email": "pooja.bhattacharya@lsdigital-demo.com",
        "password": "ChangeMe123!",
        "full_name": "Pooja Bhattacharya",
        "role": "bu_head",
        "business_unit_name": "SP Creative",
    },
    {
        "email": "aditya.choudhary@lsdigital-demo.com",
        "password": "ChangeMe123!",
        "full_name": "Aditya Choudhary",
        "role": "bu_head",
        "business_unit_name": "UI/UX",
    },
]


# Illustrative demo employees only — not real LS Digital personnel. Indian
# names per ARCHITECTURE.md's naming rule. `key`/`manager_key` are local
# to this script (not DB ids) and let later rows reference earlier ones
# before either has a real primary key. Data Quark deliberately carries
# both a same-BU manager relationship (Sneha/Meera -> Vikram) and a
# cross-BU one (Rohan -> Ananya, who sits in Business Function and Media)
# — Data Quark is the one BU with a real bu_head login (arjun.mehta), so
# both the visible-manager-name and the manager:null RLS-masking case are
# demoable live through /docs, not only in the pytest suite.
SEED_EMPLOYEES = [
    {
        "key": "ananya_krishnan", "employee_code": "EMP1001", "full_name": "Ananya Krishnan",
        "gender": "Female",
        "business_unit_name": "Business Function and Media", "department_name": "Growth and Strategy",
        "grade": "L6", "designation": "Group Head, Growth", "manager_key": None, "location": "Mumbai",
        "date_of_joining": dt.date(2016, 4, 11), "ctc_annual": 3800000,
        "last_increment_date": dt.date(2025, 4, 1), "last_increment_pct": 6.50,
        "last_promotion_date": dt.date(2023, 4, 1), "performance_rating": 4.30,
        "engagement_score": 88.00, "manager_effectiveness_score": None,
        "email": "ananya.krishnan@lsdigital-demo.com",
    },
    {
        "key": "devika_rao", "employee_code": "EMP1002", "full_name": "Devika Rao",
        "gender": "Female",
        "business_unit_name": "Business Function and Media", "department_name": "Bidable Performance",
        "grade": "L4", "designation": "Manager, Performance Marketing", "manager_key": "ananya_krishnan",
        "location": "Bengaluru", "date_of_joining": dt.date(2019, 7, 22), "ctc_annual": 2150000,
        "last_increment_date": dt.date(2025, 7, 1), "last_increment_pct": 5.00,
        "last_promotion_date": dt.date(2022, 7, 1), "performance_rating": 3.90,
        "engagement_score": 79.00, "manager_effectiveness_score": 90.00,
        "email": "devika.rao@lsdigital-demo.com",
    },
    {
        "key": "ishaan_bhatt", "employee_code": "EMP1003", "full_name": "Ishaan Bhatt",
        "gender": "Male",
        "business_unit_name": "Business Function and Media", "department_name": "SEO",
        "grade": "L2", "designation": "SEO Specialist", "manager_key": "devika_rao",
        "location": "Pune", "date_of_joining": dt.date(2023, 1, 9), "ctc_annual": 950000,
        "last_increment_date": None, "last_increment_pct": None, "last_promotion_date": None,
        "performance_rating": 3.20, "engagement_score": 65.00, "manager_effectiveness_score": 82.00,
        "email": "ishaan.bhatt@lsdigital-demo.com",
    },
    {
        "key": "naveen_subramaniam", "employee_code": "EMP1004", "full_name": "Naveen Subramaniam",
        "gender": "Male",
        "business_unit_name": "Business Function and Media", "department_name": "Client Success",
        "grade": "L3", "designation": "Client Success Lead", "manager_key": "ananya_krishnan",
        "location": "Chennai", "date_of_joining": dt.date(2021, 11, 15), "ctc_annual": 1600000,
        "last_increment_date": dt.date(2025, 11, 1), "last_increment_pct": 4.50,
        "last_promotion_date": None, "performance_rating": 3.70, "engagement_score": 74.00,
        "manager_effectiveness_score": 90.00, "email": "naveen.subramaniam@lsdigital-demo.com",
    },
    {
        "key": "vikram_nair", "employee_code": "EMP1005", "full_name": "Vikram Nair",
        "gender": "Male",
        "business_unit_name": "Data Quark", "department_name": "Data Quark Sales",
        "grade": "L5", "designation": "Senior Manager, Sales", "manager_key": None,
        "location": "Bengaluru", "date_of_joining": dt.date(2017, 2, 1), "ctc_annual": 3200000,
        "last_increment_date": dt.date(2025, 2, 1), "last_increment_pct": 7.00,
        "last_promotion_date": dt.date(2022, 2, 1), "performance_rating": 4.10,
        "engagement_score": 83.00, "manager_effectiveness_score": None,
        "email": "vikram.nair@lsdigital-demo.com",
    },
    {
        "key": "sneha_iyer", "employee_code": "EMP1006", "full_name": "Sneha Iyer",
        "gender": "Female",
        "business_unit_name": "Data Quark", "department_name": "Digital Analytics",
        "grade": "L3", "designation": "Analytics Lead", "manager_key": "vikram_nair",
        "location": "Hyderabad", "date_of_joining": dt.date(2020, 6, 18), "ctc_annual": 1750000,
        "last_increment_date": dt.date(2025, 6, 1), "last_increment_pct": 5.50,
        "last_promotion_date": dt.date(2023, 6, 1), "performance_rating": 3.80,
        "engagement_score": 77.00, "manager_effectiveness_score": 85.00,
        "email": "sneha.iyer@lsdigital-demo.com",
    },
    {
        "key": "rohan_verma", "employee_code": "EMP1007", "full_name": "Rohan Verma",
        "gender": "Male",
        "business_unit_name": "Data Quark", "department_name": "Product and Consulting",
        "grade": "L4", "designation": "Principal Consultant", "manager_key": "ananya_krishnan",
        "location": "Gurugram", "date_of_joining": dt.date(2018, 9, 3), "ctc_annual": 2600000,
        "last_increment_date": dt.date(2025, 9, 1), "last_increment_pct": 6.00,
        "last_promotion_date": dt.date(2021, 9, 1), "performance_rating": 4.00,
        "engagement_score": 80.00, "manager_effectiveness_score": 90.00,
        "email": "rohan.verma@lsdigital-demo.com",
    },
    {
        "key": "meera_pillai", "employee_code": "EMP1008", "full_name": "Meera Pillai",
        "gender": "Female",
        "business_unit_name": "Data Quark", "department_name": "Unified Data Solutions",
        "grade": "L1", "designation": "Associate Consultant", "manager_key": "vikram_nair",
        "location": "Noida", "date_of_joining": dt.date(2024, 3, 11), "ctc_annual": 850000,
        "last_increment_date": None, "last_increment_pct": None, "last_promotion_date": None,
        "performance_rating": 3.40, "engagement_score": 68.00, "manager_effectiveness_score": 85.00,
        "email": "meera.pillai@lsdigital-demo.com",
    },
    {
        "key": "ritika_desai", "employee_code": "EMP1009", "full_name": "Ritika Desai",
        "gender": "Female",
        "business_unit_name": "Enabling Functions", "department_name": "Finance",
        "grade": "L5", "designation": "Finance Controller", "manager_key": None,
        "location": "Mumbai", "date_of_joining": dt.date(2015, 8, 20), "ctc_annual": 3500000,
        "last_increment_date": dt.date(2025, 8, 1), "last_increment_pct": 6.00,
        "last_promotion_date": dt.date(2021, 8, 1), "performance_rating": 4.40,
        "engagement_score": 85.00, "manager_effectiveness_score": None,
        "email": "ritika.desai@lsdigital-demo.com",
    },
    {
        "key": "arnav_chatterjee", "employee_code": "EMP1010", "full_name": "Arnav Chatterjee",
        "gender": "Male",
        "business_unit_name": "Enabling Functions", "department_name": "Growth",
        "grade": "L3", "designation": "Growth Manager", "manager_key": "ritika_desai",
        "location": "Kolkata", "date_of_joining": dt.date(2022, 2, 14), "ctc_annual": 1500000,
        "last_increment_date": None, "last_increment_pct": None, "last_promotion_date": None,
        "performance_rating": 3.60, "engagement_score": 71.00, "manager_effectiveness_score": 88.00,
        "email": "arnav.chatterjee@lsdigital-demo.com",
    },
    {
        "key": "divya_menon", "employee_code": "EMP1011", "full_name": "Divya Menon",
        "gender": "Female",
        "business_unit_name": "Enabling Functions", "department_name": "Marketing and PR",
        "grade": "L3", "designation": "PR Manager", "manager_key": "ritika_desai",
        "location": "Ahmedabad", "date_of_joining": dt.date(2021, 5, 5), "ctc_annual": 1650000,
        "last_increment_date": dt.date(2025, 5, 1), "last_increment_pct": 5.00,
        "last_promotion_date": dt.date(2023, 5, 1), "performance_rating": 3.90,
        "engagement_score": 76.00, "manager_effectiveness_score": 88.00,
        "email": "divya.menon@lsdigital-demo.com",
    },
    {
        "key": "yusuf_sheikh", "employee_code": "EMP1012", "full_name": "Yusuf Sheikh",
        "gender": "Male",
        "business_unit_name": "Enabling Functions", "department_name": "People Management",
        "grade": "L2", "designation": "HR Business Partner", "manager_key": "ritika_desai",
        "location": "Pune", "date_of_joining": dt.date(2023, 8, 1), "ctc_annual": 1100000,
        "last_increment_date": None, "last_increment_pct": None, "last_promotion_date": None,
        "performance_rating": 3.30, "engagement_score": 69.00, "manager_effectiveness_score": 88.00,
        "email": "yusuf.sheikh@lsdigital-demo.com",
    },
    {
        "key": "tanvi_joshi", "employee_code": "EMP1013", "full_name": "Tanvi Joshi",
        "gender": "Female",
        "business_unit_name": "SP Creative", "department_name": "Administration",
        "grade": "L4", "designation": "Admin Head", "manager_key": None,
        "location": "Mumbai", "date_of_joining": dt.date(2014, 1, 10), "ctc_annual": 2400000,
        "last_increment_date": dt.date(2025, 1, 1), "last_increment_pct": 5.50,
        "last_promotion_date": dt.date(2020, 1, 1), "performance_rating": 4.00,
        "engagement_score": 81.00, "manager_effectiveness_score": None,
        "email": "tanvi.joshi@lsdigital-demo.com",
    },
    {
        "key": "kabir_malhotra", "employee_code": "EMP1014", "full_name": "Kabir Malhotra",
        "gender": "Male",
        "business_unit_name": "SP Creative", "department_name": "Finance and Accounting",
        "grade": "L3", "designation": "Accounts Manager", "manager_key": "tanvi_joshi",
        "location": "Bengaluru", "date_of_joining": dt.date(2020, 10, 19), "ctc_annual": 1450000,
        "last_increment_date": dt.date(2025, 10, 1), "last_increment_pct": 4.50,
        "last_promotion_date": None, "performance_rating": 3.50, "engagement_score": 70.00,
        "manager_effectiveness_score": 79.00, "email": "kabir.malhotra@lsdigital-demo.com",
    },
    {
        "key": "zara_ahmed", "employee_code": "EMP1015", "full_name": "Zara Ahmed",
        "gender": "Female",
        "business_unit_name": "SP Creative", "department_name": "Social",
        "grade": "L2", "designation": "Social Media Executive", "manager_key": "tanvi_joshi",
        "location": "Chennai", "date_of_joining": dt.date(2024, 6, 1), "ctc_annual": 900000,
        "last_increment_date": None, "last_increment_pct": None, "last_promotion_date": None,
        "performance_rating": 3.00, "engagement_score": 60.00, "manager_effectiveness_score": 79.00,
        "email": "zara.ahmed@lsdigital-demo.com",
    },
    {
        "key": "farhan_qureshi", "employee_code": "EMP1016", "full_name": "Farhan Qureshi",
        "gender": "Male",
        "business_unit_name": "SP Creative", "department_name": "Strategy and Growth",
        "grade": "L4", "designation": "Strategy Manager", "manager_key": "tanvi_joshi",
        "location": "Hyderabad", "date_of_joining": dt.date(2019, 12, 2), "ctc_annual": 2000000,
        "last_increment_date": dt.date(2025, 12, 1), "last_increment_pct": 5.00,
        "last_promotion_date": dt.date(2022, 12, 1), "performance_rating": 3.80,
        "engagement_score": 75.00, "manager_effectiveness_score": 79.00,
        "email": "farhan.qureshi@lsdigital-demo.com",
    },
    {
        "key": "aarav_kapoor", "employee_code": "EMP1017", "full_name": "Aarav Kapoor",
        "gender": "Male",
        "business_unit_name": "UI/UX", "department_name": "Design",
        "grade": "L5", "designation": "Design Head", "manager_key": None,
        "location": "Bengaluru", "date_of_joining": dt.date(2017, 6, 12), "ctc_annual": 2900000,
        "last_increment_date": dt.date(2025, 6, 1), "last_increment_pct": 6.00,
        "last_promotion_date": dt.date(2022, 6, 1), "performance_rating": 4.20,
        "engagement_score": 84.00, "manager_effectiveness_score": None,
        "email": "aarav.kapoor@lsdigital-demo.com",
    },
    {
        "key": "nisha_bansal", "employee_code": "EMP1018", "full_name": "Nisha Bansal",
        "gender": "Female",
        "business_unit_name": "UI/UX", "department_name": "Design",
        "grade": "L2", "designation": "UI Designer", "manager_key": "aarav_kapoor",
        "location": "Pune", "date_of_joining": dt.date(2023, 4, 25), "ctc_annual": 1050000,
        "last_increment_date": None, "last_increment_pct": None, "last_promotion_date": None,
        "performance_rating": 3.40, "engagement_score": 72.00, "manager_effectiveness_score": 86.00,
        "email": "nisha.bansal@lsdigital-demo.com",
    },
]


def seed_employees(db: Session, bu_by_name: dict[str, BusinessUnit]) -> None:
    created: dict[str, Employee] = {}

    for spec in SEED_EMPLOYEES:
        existing = db.scalar(select(Employee).where(Employee.employee_code == spec["employee_code"]))
        if existing is not None:
            created[spec["key"]] = existing
            continue

        department = db.scalar(
            select(Department).where(
                Department.business_unit_id == bu_by_name[spec["business_unit_name"]].id,
                Department.name == spec["department_name"],
            )
        )
        manager = created[spec["manager_key"]] if spec["manager_key"] else None

        # business_unit_id is left unset: the sync_employee_business_unit
        # BEFORE INSERT trigger (migration 5c6bf1a73a67) derives it from
        # department_id.
        employee = Employee(
            employee_code=spec["employee_code"],
            full_name=spec["full_name"],
            gender=spec["gender"],
            date_of_joining=spec["date_of_joining"],
            department_id=department.id,
            designation=spec["designation"],
            grade=spec["grade"],
            manager_id=manager.id if manager else None,
            location=spec["location"],
            email=spec["email"],
            ctc_annual=spec["ctc_annual"],
            last_increment_date=spec["last_increment_date"],
            last_increment_pct=spec["last_increment_pct"],
            last_promotion_date=spec["last_promotion_date"],
            performance_rating=spec["performance_rating"],
            engagement_score=spec["engagement_score"],
            manager_effectiveness_score=spec["manager_effectiveness_score"],
        )
        db.add(employee)
        db.flush()
        print(f"created employee: {spec['full_name']} ({spec['business_unit_name']} / {spec['department_name']})")
        created[spec["key"]] = employee


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

    seed_employees(db, bu_by_name)

    db.commit()


def main() -> None:
    url = settings.migrations_database_url or settings.database_url
    engine = create_engine(url)
    with Session(engine) as db:
        seed(db)


if __name__ == "__main__":
    main()
