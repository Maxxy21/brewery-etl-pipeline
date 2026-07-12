import numpy as np
import pandas as pd
import pytest

from src.transform import parse_korean_phone_prefix, classify_korean_phone_type


@pytest.mark.parametrize("raw, expected", [
    # Seoul keeps its two-digit code, everything else on a trunk zero gives three.
    ("02-6205-1785", "02"),
    ("02-743-1212", "02"),
    ("051-791-1002", "051"),
    ("031-827-1635", "031"),
    ("033-818-1663", "033"),
    ("064-721-0227", "064"),
    ("010-3022-4997", "010"),
    ("070-7722-0705", "070"),
    # Relay numbers show up with both 3 and 4-digit groupings in the source.
    ("050-71342-6297", "050"),
    ("0507-1446-2345", "050"),
    # National service numbers have no trunk zero, so we keep four digits.
    ("1661-5869", "1661"),
    # +82 international form should normalize back to the domestic trunk.
    ("+82 2 6205 1785", "02"),
    ("+82 51 791 1002", "051"),
])
def test_parse_prefix(raw, expected):
    assert parse_korean_phone_prefix(raw) == expected


@pytest.mark.parametrize("raw", [None, np.nan, "", "   ", "not a phone number"])
def test_parse_prefix_returns_nan_for_unusable_input(raw):
    assert pd.isna(parse_korean_phone_prefix(raw))


@pytest.mark.parametrize("prefix, expected", [
    ("02", "Seoul (Capital)"),
    ("051", "Provincial/Geographic"),
    ("031", "Provincial/Geographic"),
    ("064", "Provincial/Geographic"),
    ("010", "Mobile"),
    ("019", "Mobile"),
    ("070", "VoIP/Internet Phone"),
    ("050", "Personal/Relay"),
    ("060", "Premium-Rate"),
    ("080", "Toll-Free"),
    ("1661", "National Service"),
    ("1588", "National Service"),
    ("099", "Other/Invalid"),
])
def test_classify(prefix, expected):
    assert classify_korean_phone_type(prefix) == expected


def test_classify_missing_prefix():
    assert classify_korean_phone_type(np.nan) == "Unknown/Null"


# The three below are regressions. Each one was wrong at some point, and the geographic
# bucket is the backbone of the by-province analysis, so a leak into it matters.

def test_relay_numbers_are_not_geographic():
    # 050 sits inside the 03x-06x range but is a nationwide relay number, not a province.
    assert classify_korean_phone_type("050") != "Provincial/Geographic"


def test_premium_rate_is_not_geographic():
    # Same trap as 050: 060 starts with 06 but is not a provincial code.
    assert classify_korean_phone_type("060") != "Provincial/Geographic"


def test_national_service_is_not_treated_as_missing():
    # 1661-5869 has no trunk zero. It should be its own category, not lumped in with
    # the breweries that simply have no phone number at all.
    prefix = parse_korean_phone_prefix("1661-5869")
    assert classify_korean_phone_type(prefix) == "National Service"


def test_end_to_end_on_real_examples():
    """A handful of real rows from the dataset, parsed and classified together."""
    cases = {
        "02-6205-1785": "Seoul (Capital)",     # Gangnam-gu, Seoul
        "051-791-1002": "Provincial/Geographic",  # Busanjin-gu, Busan
        "070-4837-6258": "VoIP/Internet Phone",   # Suyeong-gu, Busan
        "010-3022-4997": "Mobile",                # Seosan-si
        "0507-1446-2345": "Personal/Relay",       # Jung-gu, Daegu
        "1661-5869": "National Service",          # Gongju-si
    }
    for raw, expected in cases.items():
        assert classify_korean_phone_type(parse_korean_phone_prefix(raw)) == expected
