import os
import time
import logging
import requests
from typing import Optional
from pydantic import BaseModel, ConfigDict, ValidationError

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    datefmt='%m/%d/%Y %H:%M:%S',
)
logger = logging.getLogger(__name__)


# 2. Strict API Data Contract (Aligned with API Spec)
class BreweryModel(BaseModel):
    model_config = ConfigDict(extra='ignore')  # ignores the duplicate state/street fields

    id: str
    name: str
    brewery_type: str
    address_1: Optional[str] = None
    address_2: Optional[str] = None
    address_3: Optional[str] = None
    city: str
    state_province: str
    postal_code: str
    country: str
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    phone: Optional[str] = None
    website_url: Optional[str] = None


def run_extract_pipeline(output_dir="data/landing_zone"):
    """
    Extracts brewery data from the Open Brewery DB API with pagination and schema enforcement.
    Streams the raw output directly to an NDJSON file to minimize memory usage.
    """
    base_url = "https://api.openbrewerydb.org/v1/breweries"
    page = 1
    per_page = 200 # Max allowed by the API
    total_valid_records = 0
    total_malformed_records = 0

    # Ensure landing zone path exists
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "raw_breweries.ndjson")

    logger.info(f"Initializing extraction pipeline. Destination: {output_path}")

    with open(output_path, 'w', encoding='utf-8') as f:
        while True:
            params = {
                "page": page,
                "per_page": per_page
            }

            try:
                logger.debug(f"Requesting page {page} with batch size {per_page}...")
                response = requests.get(base_url, params=params, timeout=15)
                response.raise_for_status()

                data = response.json()

                # Terminal condition: API returns an empty list
                if not data:
                    logger.info("API returned empty array. Extraction complete.")
                    break

                # Streaming and continuous data contract validation
                for record in data:
                    try:
                        # Enforce schema and drop deprecated fields seamlessly via Pydantic
                        validated_brewery = BreweryModel(**record)

                        # Serialize object straight to a single line in our NDJSON file
                        f.write(validated_brewery.model_dump_json() + '\n')
                        total_valid_records += 1

                    except ValidationError as ve:
                        total_malformed_records += 1
                        logger.warning(
                            f"Schema Violation dropped record ID: {record.get('id', 'Unknown')}. "
                            f"Reason: {ve.json()}"
                        )

                logger.info(f"Successfully processed page {page}. Cumulative Valid: {total_valid_records}")
                page += 1

                time.sleep(0.2) # Throttle to not overload the server

            except requests.exceptions.RequestException as e:
                logger.critical(f"Pipeline stalled due to unrecoverable network error on page {page}: {e}")
                raise e

    logger.info(
        f"Pipeline Summary -> Valid Records: {total_valid_records} | "
        f"malformed Records: {total_malformed_records}"
    )
    return output_path


if __name__ == "__main__":
    try:
        run_extract_pipeline()
    except Exception as pipeline_err:
        logger.error(f"Execution failed: {pipeline_err}")