"""
Injected error ranges for demo verification:
- Duplicate contact_id (23 rows): 40-62
- Malformed emails (31 rows): 70-100
- Invalid phones (18 rows): 110-127
- Age out-of-range (12 rows): 130-141
- Age nulls (8 rows): 142-149
- account_type typos (7 rows): 150-156
- annual_revenue negatives (9 rows): 160-168
- annual_revenue text (9 type issues, 3 explicit N/A): 169-177
- Invalid pincodes (11 rows): 180-190
- Wrong date formats (14 rows): 200-213
- Invalid account_manager_id refs (15 rows): 220-234
- Additional required-field null injections to total ~47: distributed rows 300-338
"""

from __future__ import annotations

from pathlib import Path
import random

import numpy as np
import pandas as pd
from faker import Faker


def build_sample_source() -> pd.DataFrame:
    fake = Faker(locale="en_IN")
    rng = random.Random(42)
    np.random.seed(42)
    rows = 500
    first_names = [fake.first_name() for _ in range(rows)]
    last_names = [fake.last_name() for _ in range(rows)]
    data = []
    for i in range(rows):
        data.append(
            {
                "contact_id": 10000 + i,
                "first_name": first_names[i],
                "last_name": last_names[i],
                "email": f"{first_names[i].lower()}.{last_names[i].lower()}{i}@example.in".replace(" ", ""),
                "phone": f"+91-{rng.randint(60000,99999)}-{rng.randint(10000,99999)}",
                "age": int(np.random.randint(18, 66)),
                "account_type": rng.choice(["Individual", "Corporate", "SME"]),
                "annual_revenue": round(float(np.random.uniform(1_00_000, 50_00_000)), 2),
                "city": rng.choice(["Mumbai", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Pune", "Kolkata", "Ahmedabad"]),
                "pincode": f"{rng.randint(100000, 999999)}",
                "created_date": fake.date_between(start_date="-4y", end_date="today").strftime("%d/%m/%Y"),
                "account_manager_id": rng.randint(1001, 1120),
            }
        )
    df = pd.DataFrame(data)
    dup_source = df.loc[39:61, "contact_id"].tolist()
    df.loc[40:62, "contact_id"] = dup_source
    for idx in range(70, 101):
        if idx % 3 == 0:
            df.at[idx, "email"] = f"user{idx}example.com"
        elif idx % 3 == 1:
            df.at[idx, "email"] = f"user..{idx}@example"
        else:
            df.at[idx, "email"] = f"user{idx}@example"
    for idx in range(110, 128):
        df.at[idx, "phone"] = str(rng.randint(10000000, 99999999))
    for idx in range(130, 136):
        df.at[idx, "age"] = 5
    for idx in range(136, 142):
        df.at[idx, "age"] = 150
    for idx in range(142, 150):
        df.at[idx, "age"] = np.nan
    typos = ["Corparate", "SME.", "individuall", "CORP", "Corparate", "SME.", "CORP"]
    for idx, typo in zip(range(150, 157), typos):
        df.at[idx, "account_type"] = typo
    for idx in range(160, 169):
        df.at[idx, "annual_revenue"] = -1 * abs(df.at[idx, "annual_revenue"])
    for idx in range(169, 178):
        df.at[idx, "annual_revenue"] = "N/A" if idx < 172 else "bad_value"
    for idx in range(180, 191):
        df.at[idx, "pincode"] = str(rng.randint(10000, 99999))
    for idx in range(200, 214):
        if idx % 2 == 0:
            df.at[idx, "created_date"] = pd.to_datetime(df.at[idx, "created_date"], dayfirst=True).strftime("%m-%d-%Y")
        else:
            df.at[idx, "created_date"] = pd.to_datetime(df.at[idx, "created_date"], dayfirst=True).strftime("%m/%d/%Y")
    for idx in range(220, 235):
        df.at[idx, "account_manager_id"] = rng.randint(2000, 2200)
    req_cols = ["contact_id", "email", "phone", "account_type", "annual_revenue"]
    null_targets = 47
    injected = 0
    for idx in range(300, rows):
        if injected >= null_targets:
            break
        col = req_cols[idx % len(req_cols)]
        if pd.isna(df.at[idx, col]):
            continue
        df.at[idx, col] = np.nan
        injected += 1
    return df


def build_sample_schema() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ("contact_id", "integer", "Y", r"^\d+$", None, None, ""),
            ("first_name", "string", "N", "", None, None, ""),
            ("last_name", "string", "N", "", None, None, ""),
            ("email", "string", "Y", r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", None, None, ""),
            ("phone", "string", "Y", r"^(\+91-\d{5}-\d{5}|\d{10})$", None, None, ""),
            ("age", "integer", "N", "", 18, 65, ""),
            ("account_type", "string", "Y", r"^(Individual|Corporate|SME)$", None, None, ""),
            ("annual_revenue", "float", "Y", "", 0, None, ""),
            ("city", "string", "N", "", None, None, ""),
            ("pincode", "string", "N", r"^\d{6}$", None, None, ""),
            ("created_date", "date", "N", r"^\d{2}/\d{2}/\d{4}$", None, None, ""),
            ("account_manager_id", "integer", "N", r"^\d+$", None, None, "manager_master"),
        ],
        columns=["field_name", "data_type", "required", "format_regex", "min_val", "max_val", "reference_table"],
    )


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    sample_dir = root / "sample_data"
    sample_dir.mkdir(exist_ok=True)
    source_df = build_sample_source()
    schema_df = build_sample_schema()
    source_df.to_excel(sample_dir / "sample_source.xlsx", index=False)
    schema_df.to_excel(sample_dir / "sample_schema.xlsx", index=False)
    print(f"Generated sample files in {sample_dir}")


if __name__ == "__main__":
    main()
