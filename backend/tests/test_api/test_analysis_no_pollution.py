"""Regression test: re-uploading an already-imported statement must NOT pollute
a per-file analysis.

Root cause (fixed 2026-06-19): `_load_trades` filtered by user_id + date range
instead of by the analysis's own raw_file_id. So when a user uploaded the same
(or overlapping-date) statement twice, the analysis double-counted trades and
silently returned ~2x PnL / win counts. The fix scopes each analysis to exactly
its raw_file_id.

NOTE on the fixture data: prices are deliberately varied across many distinct
values. SmartParser classifies columns by sampling values, and a price column
with only 1–2 distinct small values (e.g. all 10.00) gets mis-scored as
commission/quantity and the file parses to 0 trades. Real broker exports have
dozens of distinct prices; the fixture mirrors that so the parser stays stable.
"""

# File A: several stocks, varied prices, all within the same date window as B.
FILE_A_CSV = (
    "委托时间,证券代码,证券名称,买卖方向,成交价格,成交数量,手续费\n"
    + "\n".join([
        "2024-01-02 09:30:00,000001,平安银行,买入,10.25,1000,5.13",
        "2024-01-02 10:00:00,000002,万科A,买入,8.40,1500,6.30",
        "2024-01-03 09:35:00,000001,平安银行,卖出,10.80,1000,5.40",
        "2024-01-03 14:00:00,000002,万科A,卖出,8.15,1500,6.11",
        "2024-01-04 09:30:00,600100,同方股份,买入,6.70,2000,6.70",
        "2024-01-05 09:30:00,600100,同方股份,卖出,7.05,2000,7.05",
        "2024-01-08 09:30:00,000001,平安银行,买入,10.60,800,4.24",
        "2024-01-09 09:30:00,000001,平安银行,卖出,11.20,800,4.48",
    ])
    + "\n"
)

# File B: DIFFERENT stocks, SAME date window. Under the buggy user_id+date-range
# logic, an analysis of File A would also pull in these trades.
FILE_B_CSV = (
    "委托时间,证券代码,证券名称,买卖方向,成交价格,成交数量,手续费\n"
    + "\n".join([
        "2024-01-02 09:30:00,600001,包钢股份,买入,1.85,5000,4.63",
        "2024-01-03 09:30:00,600001,包钢股份,卖出,1.92,5000,4.80",
        "2024-01-04 09:30:00,600007,中国国贸,买入,12.30,600,3.69",
        "2024-01-05 09:30:00,600007,中国国贸,卖出,12.05,600,3.62",
        "2024-01-08 09:30:00,600010,包钢股份,买入,2.10,3000,3.15",
        "2024-01-09 09:30:00,600010,包钢股份,卖出,2.25,3000,3.38",
    ])
    + "\n"
)

EMAIL = "dup_upload@test.com"
PASSWORD = "secret123"


def _register(client):
    resp = client.post(
        "/api/auth/register", json={"email": EMAIL, "password": PASSWORD}
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _upload_and_import(client, headers, csv, name):
    r = client.post(
        "/api/upload",
        headers=headers,
        files={"file": (name, csv, "text/csv")},
    )
    raw_file_id = r.json()["raw_file_id"]
    client.post(
        "/api/upload/confirm",
        headers=headers,
        json={"raw_file_id": raw_file_id, "source_type": "smart"},
    )
    client.post(
        "/api/upload/import",
        headers=headers,
        json={"raw_file_id": raw_file_id},
    )
    return raw_file_id


def _run(client, headers, raw_file_id):
    resp = client.post(
        "/api/analysis/run",
        headers=headers,
        json={
            "date_start": "2024-01-01",
            "date_end": "2024-12-31",
            "raw_file_id": raw_file_id,
        },
    )
    return resp.json()["analysis_id"]


def test_analysis_not_polluted_by_other_files_same_user(client):
    """An analysis of File A must reflect ONLY File A, even though the same user
    also imported File B in an overlapping date window."""
    headers = _register(client)

    file_a_id = _upload_and_import(client, headers, FILE_A_CSV, "a.csv")
    _b_id = _upload_and_import(client, headers, FILE_B_CSV, "b.csv")

    analysis_a = _run(client, headers, file_a_id)

    resp = client.get(
        f"/api/analysis/{analysis_a}/stats", headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()

    # File A has 8 trades on {000001, 000002, 600100} only. Under the old bug
    # this would mix in File B's {600001,600007,600010} trades → 14 trades and
    # leaked symbols.
    assert data["total_trades"] == 8
    symbols = {p["symbol"] for p in data["positions"]}
    assert symbols == {"000001", "000002", "600100"}, (
        f"analysis leaked another file's trades: {symbols}"
    )


def test_reimporting_same_statement_does_not_double_count(client):
    """Re-uploading the identical statement and analyzing the second copy must
    show the same single-file numbers, not 2x. This is the exact user scenario:
    accidentally uploading 20260619 交割单.xls twice."""
    headers = _register(client)
    first = _upload_and_import(client, headers, FILE_A_CSV, "a.csv")
    # Same content uploaded again as a new file.
    second = _upload_and_import(client, headers, FILE_A_CSV, "a_dup.csv")

    analysis_second = _run(client, headers, second)
    resp = client.get(
        f"/api/analysis/{analysis_second}/stats", headers=headers
    )
    data = resp.json()
    # Second file's analysis sees only its own 8 trades, not 16.
    assert data["total_trades"] == 8
    symbols = {p["symbol"] for p in data["positions"]}
    assert symbols == {"000001", "000002", "600100"}

    # And the first file's analysis is independently still correct (not 16).
    analysis_first = _run(client, headers, first)
    resp1 = client.get(
        f"/api/analysis/{analysis_first}/stats", headers=headers
    )
    assert resp1.json()["total_trades"] == 8
