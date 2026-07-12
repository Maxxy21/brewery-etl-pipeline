import os
import sqlite3
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def run_analysis(db_path: str, output_dir: str = "data/analytics_zone/analytics"):
    """Answer the four questions with SQL and save the aggregates as CSVs."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}. Run load.py first.")

    os.makedirs(output_dir, exist_ok=True)
    conn = sqlite3.connect(db_path)

    try:
        # Q1 & Q2: US states by microbrewery count.
        us_micro = pd.read_sql_query(
            "SELECT state_province, COUNT(*) AS microbrewery_count "
            "FROM breweries WHERE country = 'United States' AND brewery_type = 'micro' "
            "GROUP BY state_province ORDER BY microbrewery_count DESC",
            conn,
        )
        if not us_micro.empty:
            top = us_micro.iloc[0]
            logger.info(f"Q1: {top['state_province']} has the most microbreweries ({top['microbrewery_count']}).")
            logger.info(f"Q2 top 5:\n{us_micro.head(5).to_string(index=False)}")
            us_micro.head(5).to_csv(os.path.join(output_dir, "top_us_micro_states.csv"),
                                    index=False, encoding='utf-8')

        # Q3: brewpubs in Incheon.
        incheon = conn.execute(
            "SELECT COUNT(*) FROM breweries WHERE country = 'South Korea' "
            "AND brewery_type = 'brewpub' AND state_province = 'Incheon'"
        ).fetchone()[0]
        logger.info(f"Q3: {incheon} brewpub(s) in Incheon, South Korea.")

        # Q4: South Korea phone-type distribution by province.
        sk_phones = pd.read_sql_query(
            "SELECT state_province, phone_type, COUNT(*) AS frequency "
            "FROM breweries WHERE country = 'South Korea' AND phone_prefix IS NOT NULL "
            "GROUP BY state_province, phone_type ORDER BY state_province ASC, frequency DESC",
            conn,
        )
        sk_phones.to_csv(os.path.join(output_dir, "korea_phone_by_province.csv"),
                         index=False, encoding='utf-8')

        # Type split for South Korea, to be used for visualization.
        sk_types = pd.read_sql_query(
            "SELECT brewery_type, COUNT(*) AS count FROM breweries "
            "WHERE country = 'South Korea' GROUP BY brewery_type ORDER BY count DESC",
            conn,
        )
        sk_types.to_csv(os.path.join(output_dir, "korea_brewery_types.csv"),
                        index=False, encoding='utf-8')

        logger.info(f"Results written to {output_dir}")
    finally:
        conn.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
    run_analysis("data/database/breweries.db")
