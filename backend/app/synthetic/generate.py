"""Module 3 dataset generator. Produces a large (~3000-row), entirely
synthetic workforce with an honestly, non-circularly generated departure
label — see MODULE3_REFERENCE.md and app/synthetic/label.py for the full
reasoning. This script only builds the raw dataset and the label; model
training and SHAP happen separately in app/synthetic/train.py, which
must be run afterward.

Idempotent in the sense that matters here: unlike scripts/seed_reference_
data.py (which preserves hand-authored rows), this dataset has no
real-world source to protect across runs, so re-running this script
truncates and regenerates the whole synthetic_employee table from
scratch, deterministically (fixed RNG seed below) — same output every
time until the generation logic itself changes.

Run with the migrator role so it can write regardless of RLS
(synthetic_employee carries RLS just like employee — see the migration —
and fri_migrator bypasses it as table owner):

    cd backend && source .venv/bin/activate && python -m app.synthetic.generate
"""

from __future__ import annotations

import datetime as dt
import random
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from sqlalchemy import create_engine, delete, func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.business_unit import BusinessUnit
from app.models.department import Department
from app.models.synthetic_employee import SyntheticEmployee
from app.synthetic.features import RawSignals, compute_features, grade_medians
from app.synthetic.label import BASE_RATE, NOISE_STD_DEV, departure_log_odds_terms, sigmoid

# Fixed seed: this dataset is fully synthetic with no source of truth to
# preserve, so determinism (same output every run) is more useful than
# fresh randomness each time.
RNG_SEED = 20260921
TOTAL_EMPLOYEES = 3000
AS_OF = dt.date.today()

FIRST_NAMES_MALE = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan",
    "Krishna", "Ishaan", "Rohan", "Karthik", "Aryan", "Dhruv", "Kabir", "Rudra",
    "Advait", "Yash", "Pranav", "Nikhil", "Siddharth", "Varun", "Abhishek",
    "Harsh", "Vikram", "Rajat", "Ankit", "Manish", "Gaurav", "Tarun", "Amit",
    "Sameer", "Naveen", "Deepak", "Rahul", "Suresh", "Ramesh", "Kunal",
    "Akash", "Vishal", "Sanjay", "Ajay", "Anirudh", "Farhan", "Zaid", "Imran",
    "Yusuf", "Arnav", "Kartik", "Nikunj",
]
FIRST_NAMES_FEMALE = [
    "Saanvi", "Ananya", "Aadhya", "Diya", "Ishita", "Myra", "Anika", "Riya",
    "Priya", "Meera", "Kavya", "Aditi", "Sneha", "Pooja", "Neha", "Divya",
    "Shreya", "Nisha", "Tanvi", "Ritika", "Aisha", "Zara", "Sanya", "Kritika",
    "Bhavya", "Charu", "Deepika", "Gauri", "Isha", "Jyoti", "Kiran", "Lavanya",
    "Manisha", "Nandini", "Pallavi", "Radhika", "Sakshi", "Simran", "Swati",
    "Trisha", "Vidya", "Yamini", "Anjali", "Bhavna", "Chitra", "Devika",
    "Esha", "Farah", "Geeta", "Harini",
]
LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Mehta", "Shah", "Patel", "Reddy", "Rao",
    "Nair", "Iyer", "Menon", "Pillai", "Krishnan", "Subramaniam", "Desai",
    "Joshi", "Malhotra", "Kapoor", "Chatterjee", "Banerjee", "Mukherjee",
    "Bhattacharya", "Chowdhury", "Bose", "Ghosh", "Agarwal", "Bansal",
    "Choudhary", "Singh", "Kumar", "Yadav", "Pandey", "Mishra", "Tiwari",
    "Trivedi", "Bhatt", "Thakur", "Rathore", "Chauhan", "Sinha", "Saxena",
    "Kulkarni", "Deshmukh", "Naidu", "Pillay", "Qureshi", "Sheikh", "Ahmed",
    "Khan", "Ansari",
]

LOCATIONS = ["Mumbai", "Bengaluru", "Pune", "Chennai", "Hyderabad", "Gurugram", "Noida", "Kolkata"]

# (min, max) annual CTC in INR per grade — overlapping ranges, same rough
# ballpark as the hand-authored Module 1/2 seed data.
CTC_RANGE_BY_GRADE = {
    "L1": (500_000, 950_000),
    "L2": (850_000, 1_500_000),
    "L3": (1_400_000, 2_300_000),
    "L4": (2_100_000, 3_600_000),
    "L5": (3_300_000, 5_800_000),
    "L6": (5_500_000, 9_500_000),
}
# Roughly pyramid-shaped org: most headcount junior, fewer senior.
GRADE_WEIGHTS = [("L1", 0.20), ("L2", 0.25), ("L3", 0.25), ("L4", 0.15), ("L5", 0.10), ("L6", 0.05)]

DESIGNATION_BY_GRADE = {
    "L1": ["Associate", "Executive"],
    "L2": ["Senior Executive", "Specialist"],
    "L3": ["Lead", "Manager"],
    "L4": ["Senior Manager", "Principal Consultant"],
    "L5": ["Associate Director", "Senior Manager"],
    "L6": ["Director", "Group Head"],
}


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _weighted_grade(rng: random.Random) -> str:
    return rng.choices([g for g, _ in GRADE_WEIGHTS], weights=[w for _, w in GRADE_WEIGHTS], k=1)[0]


def _random_name(rng: random.Random, used: set[str]) -> tuple[str, str]:
    """Returns (full_name, gender). Retries on collision — pool size (50 *
    50 * 2 genders combined against 50 surnames) comfortably covers 3000
    unique names.
    """
    while True:
        gender = rng.choice(["Male", "Female"])
        first = rng.choice(FIRST_NAMES_MALE if gender == "Male" else FIRST_NAMES_FEMALE)
        last = rng.choice(LAST_NAMES)
        full_name = f"{first} {last}"
        if full_name not in used:
            used.add(full_name)
            return full_name, gender


def _random_date_of_joining(rng: random.Random, as_of: dt.date) -> dt.date:
    days_back = rng.randint(30, 10 * 365)
    return as_of - dt.timedelta(days=days_back)


def _maybe_promotion_date(rng: random.Random, joined: dt.date, as_of: dt.date) -> dt.date | None:
    if rng.random() > 0.55:
        return None
    earliest = joined + dt.timedelta(days=180)
    if earliest >= as_of:
        return None
    days_span = (as_of - earliest).days
    return earliest + dt.timedelta(days=rng.randint(0, days_span))


def _maybe_increment_date(rng: random.Random, joined: dt.date, as_of: dt.date) -> dt.date | None:
    if rng.random() > 0.80:
        return None
    earliest = joined + dt.timedelta(days=90)
    if earliest >= as_of:
        return None
    days_span = (as_of - earliest).days
    return earliest + dt.timedelta(days=rng.randint(0, days_span))


def generate_rows(departments: list[Department], rng: random.Random) -> list[dict]:
    used_names: set[str] = set()
    used_codes: set[str] = set()
    raw_rows: list[dict] = []

    for i in range(TOTAL_EMPLOYEES):
        department = departments[i % len(departments)]
        full_name, gender = _random_name(rng, used_names)
        grade = _weighted_grade(rng)
        joined = _random_date_of_joining(rng, AS_OF)
        low, high = CTC_RANGE_BY_GRADE[grade]
        ctc_annual = round(rng.uniform(low, high), -3)

        code = f"SYN-{i + 1:05d}"
        used_codes.add(code)

        raw_rows.append(
            {
                "employee_code": code,
                "full_name": full_name,
                "gender": gender,
                "department_id": department.id,
                "business_unit_id": department.business_unit_id,
                "designation": rng.choice(DESIGNATION_BY_GRADE[grade]),
                "grade": grade,
                "location": rng.choice(LOCATIONS),
                "date_of_joining": joined,
                "ctc_annual": ctc_annual,
                "last_increment_date": _maybe_increment_date(rng, joined, AS_OF),
                "last_promotion_date": _maybe_promotion_date(rng, joined, AS_OF),
                "performance_rating": round(_clip(rng.gauss(3.2, 0.5), 2.0, 4.7), 2),
                "engagement_score": round(_clip(rng.gauss(65, 15), 0, 100), 2),
                "manager_effectiveness_score": round(_clip(rng.gauss(65, 15), 0, 100), 2),
                "overtime": rng.random() < 0.28,
                "job_satisfaction_score": round(_clip(rng.gauss(65, 15), 0, 100), 2),
                "distance_from_home_km": round(_clip(abs(rng.gauss(12, 10)), 1, 60), 1),
            }
        )

    return raw_rows


def calibrate_intercept(
    terms: list[float], noises: list[float], draws: list[float], target_rate: float
) -> float:
    """Finds, by bisection, the intercept that makes the realized
    departure rate over this exact dataset (same terms/noise/uniform-draw
    triples throughout) land on target_rate. Necessary because every term
    in departure_log_odds_terms is one-directional (risk-only — there are
    no protective terms pulling log-odds down), so the average employee's
    raw term sum is well above zero; naively setting the intercept to
    logit(target_rate) (as if terms averaged to zero) systematically
    overshoots the realized rate. Bisecting on the actual generated
    sample, holding noise/draws fixed, finds the true answer rather than
    a guess — and keeps the whole thing deterministic under the fixed
    RNG seed.
    """
    lo, hi = -6.0, 4.0
    mid = 0.0
    for _ in range(50):
        mid = (lo + hi) / 2
        left_count = sum(
            1 for term, noise, draw in zip(terms, noises, draws) if draw < sigmoid(mid + term + noise)
        )
        rate = left_count / len(terms)
        if abs(rate - target_rate) < 0.001:
            break
        if rate < target_rate:
            lo = mid
        else:
            hi = mid
    return mid


def label_rows(raw_rows: list[dict], rng: random.Random) -> None:
    """Mutates raw_rows in place, adding 'employment_status' per
    app/synthetic/label.py's independently-derived probabilistic label.
    Grade-median CTC is computed once, across the whole generated
    dataset, mirroring the aggregate-only peer comparison already used
    in Module 2 (see features.py's grade_medians docstring).
    """
    signals = [
        RawSignals(
            date_of_joining=r["date_of_joining"],
            grade=r["grade"],
            last_promotion_date=r["last_promotion_date"],
            last_increment_date=r["last_increment_date"],
            ctc_annual=r["ctc_annual"],
            performance_rating=r["performance_rating"],
            engagement_score=r["engagement_score"],
            manager_effectiveness_score=r["manager_effectiveness_score"],
            overtime=r["overtime"],
            job_satisfaction_score=r["job_satisfaction_score"],
            distance_from_home_km=r["distance_from_home_km"],
        )
        for r in raw_rows
    ]
    medians = grade_medians(signals)
    features_list = [compute_features(s, AS_OF, medians[s.grade]) for s in signals]

    terms = [departure_log_odds_terms(f) for f in features_list]
    noises = [rng.gauss(0.0, NOISE_STD_DEV) for _ in features_list]
    draws = [rng.random() for _ in features_list]

    intercept = calibrate_intercept(terms, noises, draws, BASE_RATE)

    left_count = 0
    for row, term, noise, draw in zip(raw_rows, terms, noises, draws):
        left = draw < sigmoid(intercept + term + noise)
        row["employment_status"] = "separated" if left else "active"
        if left:
            left_count += 1

    rate = left_count / len(raw_rows)
    print(f"Calibrated intercept={intercept:.3f} for target base rate {BASE_RATE:.0%} -> realized {rate:.1%}")


def main() -> None:
    url = settings.migrations_database_url or settings.database_url
    engine = create_engine(url)
    rng = random.Random(RNG_SEED)

    with Session(engine) as db:
        departments = list(db.scalars(select(Department)))
        if not departments:
            raise RuntimeError("No departments found — run scripts/seed_reference_data.py first.")

        raw_rows = generate_rows(departments, rng)
        label_rows(raw_rows, rng)

        db.execute(delete(SyntheticEmployee))
        db.add_all(SyntheticEmployee(**row) for row in raw_rows)
        db.commit()

        active_count = db.scalar(
            select(func.count()).select_from(SyntheticEmployee).where(SyntheticEmployee.employment_status == "active")
        )
        print(f"Wrote {len(raw_rows)} synthetic_employee rows ({active_count} active).")
        print("Next: python -m app.synthetic.train")


if __name__ == "__main__":
    main()
