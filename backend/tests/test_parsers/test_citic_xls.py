"""Tests for the SmartParser handling of broker exports that disguise a
tab/comma text file as .xls.

中信证券 (CITIC) exports a GBK-encoded TSV with a .xls extension where every
cell is wrapped in the Excel text-protection formula ='...' (so codes keep
leading zeros). These tests guard against regressions of:
  1. detecting such files (read_excel fails → must fall back to text)
  2. stripping the ='...' wrapper so value-based classification works
  3. summing commission columns whose values are small integers (手续费 = 5.00)
"""

from app.parsers.registry import ParserRegistry


# Minimal CITIC-style row: header + two trades. GBK-encoded, tab-separated,
# every value wrapped in ="...".
_CITIC_HEADER = (
    "交收日期\t证券代码\t证券名称\t业务名称\t成交价格\t成交数量\t成交金额"
    "\t手续费\t印花税\t过户费\t成交时间\t股东代码"
)
_CITIC_ROWS = [
    "\t".join([
        '="20260331"', '="002471"', '="中超控股"', '="证券卖出"',
        '="9.3100"', '="1000"', '="9310.00"', '="5.00"', '="4.66"',
        '="0.00"', '="09:42:39"', '="0037174116"',
    ]),
    "\t".join([
        '="20260331"', '="002506"', '="协鑫集成"', '="证券买入"',
        '="5.0300"', '="1900"', '="9557.00"', '="5.00"', '="0.00"',
        '="0.00"', '="09:45:17"', '="0037174116"',
    ]),
]


def _citic_bytes() -> bytes:
    text = "\r\n".join([_CITIC_HEADER, *_CITIC_ROWS]) + "\r\n"
    return text.encode("gbk")


def test_detect_citic_xls_disguised_as_text():
    """A .xls that is really a GBK TSV must still be detected."""
    detected = ParserRegistry.detect_format(_citic_bytes(), "交割单.xls")
    assert detected, "CITIC .xls should be detectable"
    assert detected[0][0] == "smart"


def test_parse_citic_strips_formula_wrapper_and_reads_trades():
    trades = ParserRegistry.parse("smart", _citic_bytes(), "交割单.xls")
    assert len(trades) == 2

    sell, buy = trades[0], trades[1]
    # Leading zeros preserved (="002471" → 002471, not 2471)
    assert sell.symbol == "002471"
    assert buy.symbol == "002506"
    assert sell.exchange == "SZ"
    assert buy.exchange == "SZ"

    assert sell.side == "SELL" and buy.side == "BUY"
    assert sell.price == 9.31 and sell.quantity == 1000
    assert buy.price == 5.03 and buy.quantity == 1900

    # Commission sums 手续费 + 印花税 + 过户费:
    #   sell: 5.00 + 4.66 + 0.00 = 9.66
    #   buy:  5.00 + 0.00 + 0.00 = 5.00
    assert round(sell.commission, 2) == 9.66
    assert round(buy.commission, 2) == 5.00


def test_parse_citic_date_parsed_correctly():
    trades = ParserRegistry.parse("smart", _citic_bytes(), "交割单.xls")
    assert all(t.datetime.year == 2026 and t.datetime.month == 3 for t in trades)
    assert trades[0].datetime.day == 31
