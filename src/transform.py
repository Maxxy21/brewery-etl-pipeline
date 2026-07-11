import os
import logging
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def parse_korean_phone_prefix(phone_val) -> float | str:
    """
    Return the dialing prefix of a South Korean phone number, or NaN if unrecognized.

    Based on the numbering plan (https://en.wikipedia.org/wiki/Telephone_numbers_in_South_Korea):
    Seoul is '02', other trunk numbers give their 3-digit prefix (031, 051, 070, ...),
    and national service numbers (15xx/16xx/18xx) have no trunk zero so we keep 4 digits.
    """
    if pd.isna(phone_val):
        return np.nan

    digits = "".join(c for c in str(phone_val) if c.isdigit())
    if not digits:
        return np.nan

    if digits.startswith("82"):  # +82 international form
        digits = "0" + digits[2:]

    if digits.startswith("02"):
        return "02"
    if digits.startswith("0"):
        return digits[:3]
    if digits.startswith(("15", "16", "18")):
        return digits[:4]
    return np.nan


def classify_korean_phone_type(prefix) -> str:
    """
    Bucket a prefix by type. Specific codes (050 relay, 060 premium) are checked
    before the 03x-06x geographic range so they aren't miscounted as provincial.
    """
    if pd.isna(prefix):
        return "Unknown/Null"

    prefix = str(prefix)

    if prefix == "02":
        return "Seoul (Capital)"
    if prefix in ("010", "011", "016", "017", "018", "019"):
        return "Mobile"
    if prefix == "070":
        return "VoIP/Internet Phone"
    if prefix == "050":  # nationwide "lifetime" relay numbers
        return "Personal/Relay"
    if prefix == "060":
        return "Premium-Rate"
    if prefix == "080":
        return "Toll-Free"
    if len(prefix) == 4 and prefix.startswith(("15", "16", "18")):
        return "National Service"
    if prefix.startswith(("03", "04", "05", "06")):
        return "Provincial/Geographic"
    return "Other/Invalid"


def run_transform_pipeline(input_path: str, output_dir: str = "data/processed_zone") -> str:
    """Clean the raw NDJSON and write a processed NDJSON. Idempotent; drops no rows."""
    logger.info(f"Reading {input_path}")
    df = pd.read_json(input_path, lines=True)
    rows_in = len(df)

    # Strip whitespace. No astype(str) here, so nulls stay null rather than becoming "nan".
    string_cols = df.select_dtypes(include=['object', 'string']).columns
    for col in string_cols:
        df[col] = df[col].str.strip()

    # Treat empty strings as missing so "" and null don't count separately.
    df = df.replace('', np.nan)

    # lowercase brewery_type for safe grouping.
    df['brewery_type'] = df['brewery_type'].str.lower()

    # Title-case the names we display.
    for col in ('state_province', 'city'):
        if col in df.columns:
            mask = df[col].notna()
            df.loc[mask, col] = df.loc[mask, col].str.title()

    # Phone breakdown for the South Korea question. Seed as object dtype so the string
    # prefixes aren't typecast to float.
    is_sk = df['country'] == 'South Korea'
    df['phone_prefix'] = pd.Series(dtype='object')
    df['phone_type'] = pd.Series("Unknown/Null", index=df.index, dtype='object')
    df.loc[is_sk, 'phone_prefix'] = df.loc[is_sk, 'phone'].apply(parse_korean_phone_prefix)
    df.loc[is_sk, 'phone_type'] = df.loc[is_sk, 'phone_prefix'].apply(classify_korean_phone_type)

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "cleaned_breweries.ndjson")

    if rows_in != len(df):
        raise RuntimeError(f"Row count changed ({rows_in} -> {len(df)}); transform should drop nothing.")

    df.to_json(output_path, orient='records', lines=True)
    logger.info(f"Cleaned {rows_in} rows -> {output_path}")
    return output_path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    run_transform_pipeline("data/landing_zone/raw_breweries.ndjson")
