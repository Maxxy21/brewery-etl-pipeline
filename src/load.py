import os
import sqlite3
import logging
import pandas as pd

logger = logging.getLogger(__name__)

CREATE_TABLE = """
CREATE TABLE breweries (
    id             TEXT PRIMARY KEY,
    name           TEXT,
    brewery_type   TEXT,
    address_1      TEXT,
    address_2      TEXT,
    address_3      TEXT,
    city           TEXT,
    state_province TEXT,
    postal_code    TEXT,
    country        TEXT,
    longitude      REAL,
    latitude       REAL,
    phone          TEXT,
    website_url    TEXT,
    phone_prefix   TEXT,
    phone_type     TEXT
);
"""


def run_load_pipeline(input_path: str, db_dir: str = "data/database") -> str:
    """Full-refresh the cleaned records into SQLite inside a single transaction."""
    # Pin the identifier-like columns to str so leading zeros survive the read
    df = pd.read_json(
        input_path,
        lines=True,
        dtype={'id': str, 'postal_code': str, 'phone': str, 'phone_prefix': str, 'phone_type': str},
    )
    expected_rows = len(df)

    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "breweries.db")
    conn = sqlite3.connect(db_path)

    try:
        cursor = conn.cursor()
        # One transaction: if the insert fails, the DROP rolls back and the old table stays.
        cursor.execute("BEGIN TRANSACTION;")
        cursor.execute("DROP TABLE IF EXISTS breweries;")
        cursor.execute(CREATE_TABLE)
        # append keeps the explicit schema above instead of letting pandas infer one.
        df.to_sql('breweries', conn, if_exists='append', index=False)
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Load failed, transaction rolled back.")
        raise

    try:
        landed_rows = conn.execute("SELECT COUNT(*) FROM breweries;").fetchone()[0]
        if landed_rows != expected_rows:
            raise RuntimeError(f"Expected {expected_rows} rows, found {landed_rows}.")
        logger.info(f"Loaded {landed_rows} rows into {db_path}")

        # Quick check against the /meta figures.
        for btype, count in conn.execute(
            "SELECT brewery_type, COUNT(*) FROM breweries "
            "WHERE brewery_type IN ('micro', 'brewpub') GROUP BY brewery_type;"
        ):
            logger.info(f"  {btype}: {count}")
    finally:
        conn.close()

    return db_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    run_load_pipeline("data/processed_zone/cleaned_breweries.ndjson")
