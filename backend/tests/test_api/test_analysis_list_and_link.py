"""Tests for analysis list + link-files endpoints.

User path: after running an analysis on one statement, the user may want to see
all their analyses (list) and add more statements to an existing analysis
(link-files) — the multi-file analysis flow. Both endpoints had zero coverage.
"""

import pytest

from app.models.analysis import Analysis

# Two disjoint statements so linking the second widens the date range.
CSV_A = (
    "委托时间,证券代码,证券名称,买卖方向,成交价格,成交数量,手续费\n"
    "2024-01-05 09:30:00,000001,平安银行,买入,10.50,1000,5.00\n"
    "2024-01-10 14:00:00,000001,平安银行,卖出,11.00,1000,5.00"
)
CSV_B = (
    "委托时间,证券代码,证券名称,买卖方向,成交价格,成交数量,手续费\n"
    "2024-03-05 09:30:00,600001,包钢股份,买入,5.00,2000,3.00\n"
    "2024-03-10 14:00:00,600001,包钢股份,卖出,4.50,2000,3.00"
)

TEST_PASSWORD = "secret123"


def _register(client, email):
    resp = client.post(
        "/api/auth/register", json={"email": email, "password": TEST_PASSWORD}
    )
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _import_csv(client, headers, csv, name="t.csv"):
    r = client.post(
        "/api/upload", headers=headers, files={"file": (name, csv, "text/csv")}
    )
    raw_file_id = r.json()["raw_file_id"]
    client.post(
        "/api/upload/confirm",
        headers=headers,
        json={"raw_file_id": raw_file_id, "source_type": "smart"},
    )
    client.post(
        "/api/upload/import", headers=headers, json={"raw_file_id": raw_file_id}
    )
    return raw_file_id


def _run(client, headers, raw_file_id):
    return client.post(
        "/api/analysis/run",
        headers=headers,
        json={
            "date_start": "2024-01-01",
            "date_end": "2024-12-31",
            "raw_file_id": raw_file_id,
        },
    ).json()["analysis_id"]


# ---------------------------------------------------------------------------
# GET /api/analysis (list)
# ---------------------------------------------------------------------------


class TestListAnalyses:
    def test_list_analyses_returns_user_analyses(self, client):
        headers = _register(client, "list1@test.com")
        raw_id = _import_csv(client, headers, CSV_A)
        aid = _run(client, headers, raw_id)

        resp = client.get("/api/analysis", headers=headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        item = body["analyses"][0]
        assert item["id"] == aid
        assert raw_id in item["raw_file_ids"]
        assert item["has_snapshot"] is True  # run_analysis precomputed it
        assert item["has_report"] is False
        assert item["report_id"] == ""

    def test_list_analyses_requires_auth(self, client):
        assert client.get("/api/analysis").status_code == 403

    def test_list_analyses_isolated_by_user(self, client):
        a_headers = _register(client, "listA@test.com")
        _run(client, a_headers, _import_csv(client, a_headers, CSV_A))

        b_headers = _register(client, "listB@test.com")
        _run(client, b_headers, _import_csv(client, b_headers, CSV_B))

        # register() sets an auth cookie; clear it so requests authenticate
        # strictly via the Authorization header (otherwise the most recent
        # cookie wins and the two users bleed into each other).
        client.cookies.clear()
        resp_a = client.get("/api/analysis", headers=a_headers).json()
        resp_b = client.get("/api/analysis", headers=b_headers).json()
        assert resp_a["total"] == 1
        assert resp_b["total"] == 1
        assert resp_a["analyses"][0]["id"] != resp_b["analyses"][0]["id"]


# ---------------------------------------------------------------------------
# POST /api/analysis/{id}/link-files
# ---------------------------------------------------------------------------


class TestLinkFiles:
    def test_link_files_adds_files_and_invalidates_snapshot(self, client, db_session):
        headers = _register(client, "link1@test.com")
        raw_a = _import_csv(client, headers, CSV_A)
        aid = _run(client, headers, raw_a)

        raw_b = _import_csv(client, headers, CSV_B, "b.csv")
        resp = client.post(
            f"/api/analysis/{aid}/link-files",
            headers=headers,
            json={"raw_file_ids": [raw_b]},
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "已添加 1 个文件到分析"

        # Snapshot invalidated → must recompute on next GET; date range widened.
        # Roll back this session's transaction so it sees the API's commits.
        db_session.rollback()
        analysis = db_session.query(Analysis).filter_by(id=aid).first()
        assert analysis is not None
        assert analysis.stats_snapshot is None
        assert analysis.date_end.month >= 3  # CSV_B trades are in March

    def test_link_files_idempotent(self, client):
        headers = _register(client, "link2@test.com")
        raw_a = _import_csv(client, headers, CSV_A)
        aid = _run(client, headers, raw_a)
        raw_b = _import_csv(client, headers, CSV_B, "b.csv")

        client.post(
            f"/api/analysis/{aid}/link-files",
            headers=headers,
            json={"raw_file_ids": [raw_b]},
        )
        # Linking the same file again adds nothing
        resp = client.post(
            f"/api/analysis/{aid}/link-files",
            headers=headers,
            json={"raw_file_ids": [raw_b]},
        )
        assert resp.status_code == 200
        assert resp.json()["detail"] == "已添加 0 个文件到分析"

    def test_link_files_rejects_unimported_file(self, client):
        """A file that was uploaded but not confirmed/imported (no source_type)."""
        headers = _register(client, "link3@test.com")
        raw_a = _import_csv(client, headers, CSV_A)
        aid = _run(client, headers, raw_a)
        # Upload a second file but do NOT confirm/import it
        r = client.post(
            "/api/upload",
            headers=headers,
            files={"file": ("unconfirmed.csv", CSV_B, "text/csv")},
        )
        unconfirmed_id = r.json()["raw_file_id"]

        resp = client.post(
            f"/api/analysis/{aid}/link-files",
            headers=headers,
            json={"raw_file_ids": [unconfirmed_id]},
        )
        assert resp.status_code == 400
        assert "尚未导入" in resp.json()["detail"]

    def test_link_files_rejects_other_users_file(self, client):
        """Cannot link a raw_file owned by another user."""
        a_headers = _register(client, "linkA@test.com")
        raw_a = _import_csv(client, a_headers, CSV_A)
        aid = _run(client, a_headers, raw_a)

        b_headers = _register(client, "linkB@test.com")
        b_raw = _import_csv(client, b_headers, CSV_B, "b.csv")

        resp = client.post(
            f"/api/analysis/{aid}/link-files",
            headers=a_headers,
            json={"raw_file_ids": [b_raw]},
        )
        assert resp.status_code == 404

    def test_link_files_requires_auth(self, client):
        resp = client.post(
            "/api/analysis/some-id/link-files",
            json={"raw_file_ids": ["x"]},
        )
        assert resp.status_code == 403
