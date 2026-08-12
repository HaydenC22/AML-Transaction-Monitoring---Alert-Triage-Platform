"""Creates raw.paysim_transactions and loads the PaySim-schema CSV into it.

Looks for data/raw/*.csv first (a real PaySim export dropped in by a reviewer who has
a Kaggle account), and falls back to the committed data/sample/paysim_sample.csv
otherwise -- see data/sample/DATA_DICTIONARY.md and docs/adr/0004 for why the sample
exists.
"""

import csv
import glob
import os
from pathlib import Path

import psycopg2

REPO_ROOT = Path(__file__).resolve().parent.parent
DATABASE_URL = os.environ["WAREHOUSE_DATABASE_URL"]

CREATE_SCHEMA_AND_TABLE = """
create schema if not exists raw;

drop table if exists raw.paysim_transactions cascade;

create table raw.paysim_transactions (
    step integer not null,
    type varchar(16) not null,
    amount numeric(18, 2) not null,
    nameorig varchar(32) not null,
    oldbalanceorg numeric(18, 2) not null,
    newbalanceorig numeric(18, 2) not null,
    namedest varchar(32) not null,
    oldbalancedest numeric(18, 2) not null,
    newbalancedest numeric(18, 2) not null,
    isfraud smallint not null,
    isflaggedfraud smallint not null
);
"""

COPY_SQL = """
copy raw.paysim_transactions (
    step, type, amount, nameorig, oldbalanceorg, newbalanceorig,
    namedest, oldbalancedest, newbalancedest, isfraud, isflaggedfraud
)
from stdin with (format csv, header true)
"""


def find_source_csv() -> Path:
    raw_candidates = sorted(glob.glob(str(REPO_ROOT / "data" / "raw" / "*.csv")))
    if raw_candidates:
        return Path(raw_candidates[0])
    sample = REPO_ROOT / "data" / "sample" / "paysim_sample.csv"
    if not sample.exists():
        raise FileNotFoundError(
            "No source CSV found in data/raw/ or data/sample/. "
            "Run scripts/generate_paysim_sample.py first."
        )
    return sample


def main() -> None:
    source_path = find_source_csv()
    print(f"Loading {source_path} into raw.paysim_transactions ...")

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_SCHEMA_AND_TABLE)
            with source_path.open("r", newline="") as f:
                cur.copy_expert(COPY_SQL, f)
            cur.execute("select count(*) from raw.paysim_transactions")
            row_count = cur.fetchone()[0]
        conn.commit()
    finally:
        conn.close()

    print(f"Loaded {row_count:,} rows into raw.paysim_transactions")


if __name__ == "__main__":
    main()
