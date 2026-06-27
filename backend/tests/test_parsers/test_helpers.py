"""Tests for parser helper functions."""

from app.parsers import _get_exchange


def test_get_exchange():
    assert _get_exchange("600519") == "SH"
    assert _get_exchange("500000") == "SH"
    assert _get_exchange("900901") == "SH"
    assert _get_exchange("000001") == "SZ"
    assert _get_exchange("300001") == "SZ"
    assert _get_exchange("200001") == "SZ"
    assert _get_exchange("IF2406") == "CFFEX"
    assert _get_exchange("RB2405") == "SHFE"
