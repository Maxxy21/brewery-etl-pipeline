"""
Run the full pipeline: extract -> transform -> load -> analytics -> visualize.
"""

import sys
import logging

from src.extract import run_extract_pipeline
from src.transform import run_transform_pipeline
from src.load import run_load_pipeline
from src.analytics import run_analysis
from src.visualize import run_visualization_pipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    datefmt='%m/%d/%Y %H:%M:%S',
)
logger = logging.getLogger("pipeline")


def main():
    raw_path = run_extract_pipeline(output_dir="data/landing_zone")
    clean_path = run_transform_pipeline(raw_path)
    db_path = run_load_pipeline(clean_path)
    run_analysis(db_path)
    run_visualization_pipeline()
    logger.info("Pipeline finished.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Pipeline failed: {e}")
        sys.exit(1)
