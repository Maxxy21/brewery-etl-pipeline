import os
import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from pydantic import BaseModel, ConfigDict, ValidationError

logger = logging.getLogger(__name__)

BASE_URL = "https://api.openbrewerydb.org/v1/breweries"
PER_PAGE = 200 # max allowed by the API
MAX_PAGES = 100
REQUEST_TIMEOUT = 15
MAX_ATTEMPTS = 3
RECONCILE_TOLERANCE = 5  # /meta can drift by a record or two between calls


# Only `id` is required. Keeping the rest optional to let the landing zone hold every
# record the API returns, including malformed ones; data cleaning would happen in the transform layer.
class BreweryModel(BaseModel):
    model_config = ConfigDict(extra='ignore')  # ignores the duplicate state/street fields

    id: str
    name: Optional[str] = None
    brewery_type: Optional[str] = None
    address_1: Optional[str] = None
    address_2: Optional[str] = None
    address_3: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    phone: Optional[str] = None
    website_url: Optional[str] = None


def fetch_with_retry(url, params=None):
    """GET with retries and exponential backoff, raising only once attempts run out."""
    backoff = 1
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt == MAX_ATTEMPTS:
                logger.critical(f"Giving up on {url} params={params} after {MAX_ATTEMPTS} attempts: {e}")
                raise
            logger.warning(f"Attempt {attempt}/{MAX_ATTEMPTS} failed for {url}: {e}. Retrying in {backoff}s...")
            time.sleep(backoff)
            backoff *= 2
    return None


def fetch_meta_total():
    meta = fetch_with_retry(f"{BASE_URL}/meta")
    return int(meta["total"])


def run_extract_pipeline(output_dir="data/landing_zone"):
    """Page through the API into an NDJSON file, then compare the count against /meta."""

    logger.info(f"Starting extract pipeline to {output_dir}.")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "raw_breweries.ndjson")
    metadata_path = os.path.join(output_dir, "raw_breweries.meta.json")

    meta_total = fetch_meta_total()
    logger.info(f"/meta expects {meta_total} breweries. Writing to {output_path}")

    page = 1
    records_seen = 0     # everything the API returned
    records_written = 0  # records that had an id
    records_dropped = 0  # records with no id

    with open(output_path, 'w', encoding='utf-8') as f:
        while True:
            if page > MAX_PAGES:
                raise RuntimeError(f"Passed MAX_PAGES={MAX_PAGES} without an empty page; aborting.")

            data = fetch_with_retry(BASE_URL, params={"page": page, "per_page": PER_PAGE})
            if not data:
                break

            for record in data:
                records_seen += 1
                try:
                    validated = BreweryModel(**record)
                    f.write(validated.model_dump_json() + '\n')
                    records_written += 1
                except ValidationError as ve:
                    records_dropped += 1
                    logger.warning(f"Dropped record with no usable id. Reason: {ve.errors()}")

            logger.info(f"Page {page} done, {records_written} written so far.")
            page += 1
            time.sleep(0.2)

    pages_fetched = page - 1

    # Compare against records_seen and not records_written: /meta counts dropped rows too.
    drift = abs(records_seen - meta_total)
    if drift > RECONCILE_TOLERANCE:
        raise RuntimeError(
            f"Reconciliation failed: saw {records_seen}, /meta expected {meta_total} "
            f"(drift {drift} > tolerance {RECONCILE_TOLERANCE})."
        )
    logger.info(f"Reconciled: saw {records_seen} vs /meta {meta_total} (drift {drift}).")

    metadata = {
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "source_url": BASE_URL,
        "meta_total": meta_total,
        "records_seen": records_seen,
        "records_written": records_written,
        "records_dropped_no_id": records_dropped,
        "pages_fetched": pages_fetched,
    }
    with open(metadata_path, 'w', encoding='utf-8') as m:
        json.dump(metadata, m, indent=2)

    logger.info(f"Done: {records_written} written, {records_dropped} dropped, {pages_fetched} pages.")
    return output_path


if __name__ == "__main__":
    try:
        run_extract_pipeline()
    except Exception as pipeline_err:
        logger.error(f"Execution failed: {pipeline_err}")
        raise
