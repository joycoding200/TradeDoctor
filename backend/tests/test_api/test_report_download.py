"""Tests for report check-by-analysis + download endpoints.

User path: before generating a report the UI checks whether one already exists;
after generation the user can download it as .markdown. Both endpoints had zero
coverage (generate/get/list were covered, but check and download were not).
"""

from unittest.mock import AsyncMock, patch

import pytest

QMT_CSV = (
    "委托时间,证券代码,证券名称,买卖方向,成交价格,成交数量,手续费\n"
    "2024-01-05 09:30:00,000001,平安银行,买入,10.50,1000,5.00\n"
    "2024-01-10 14:00:00,000001,平安银行,卖出,11.00,1000,5.00\n"
    "2024-02-01 09:30:00,600001,包钢股份,买入,5.00,2000,3.00\n"
    "2024-02-05 14:00:00,600001,包钢股份,卖出,4.50,2000,3.00"
)

MOCK_REPORT = "## 核心结论\n测试报告内容\n\n## 改善建议\n- 严格控制亏损"

TEST_PASSWORD = "secret123"


def _register(client, email):
    resp = client.post(
        "/api/auth/register", json={"email": email, "password": TEST_PASSWORD}
    )
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _setup_analysis(client, headers):
    r = client.post(
        "/api/upload", headers=headers, files={"file": ("t.csv", QMT_CSV, "text/csv")}
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
    aid = client.post(
        "/api/analysis/run",
        headers=headers,
        json={
            "date_start": "2024-01-01",
            "date_end": "2024-12-31",
            "raw_file_id": raw_file_id,
        },
    ).json()["analysis_id"]
    return aid


def _generate(client, headers, analysis_id):
    with patch("app.api.report.get_llm") as mock_get_llm:
        mock_provider = AsyncMock()
        mock_provider.generate = AsyncMock(return_value=MOCK_REPORT)
        mock_get_llm.return_value = mock_provider
        return client.post(
            "/api/report/generate",
            headers=headers,
            json={"analysis_id": analysis_id},
        ).json()["report_id"]


@pytest.fixture
def analysis_with_report(client):
    headers = _register(client, "report_dl@test.com")
    client.cookies.clear()
    aid = _setup_analysis(client, headers)
    rid = _generate(client, headers, aid)
    return headers, aid, rid


# ---------------------------------------------------------------------------
# GET /api/report/by-analysis/{analysis_id}
# ---------------------------------------------------------------------------


class TestCheckReportByAnalysis:
    def test_check_report_exists(self, client, analysis_with_report):
        headers, aid, rid = analysis_with_report
        resp = client.get(
            f"/api/report/by-analysis/{aid}", headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["exists"] is True
        assert body["report_id"] == rid

    def test_check_report_not_exists(self, client):
        headers = _register(client, "report_none@test.com")
        client.cookies.clear()
        aid = _setup_analysis(client, headers)
        resp = client.get(
            f"/api/report/by-analysis/{aid}", headers=headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["exists"] is False
        assert body["report_id"] == ""

    def test_check_report_requires_auth(self, client):
        assert (
            client.get("/api/report/by-analysis/some-id").status_code == 403
        )


# ---------------------------------------------------------------------------
# GET /api/report/{report_id}/download
# ---------------------------------------------------------------------------


class TestDownloadReport:
    def test_download_returns_markdown(self, client, analysis_with_report):
        headers, aid, rid = analysis_with_report
        resp = client.get(f"/api/report/{rid}/download", headers=headers)
        assert resp.status_code == 200
        assert "text/markdown" in resp.headers["content-type"]
        assert MOCK_REPORT in resp.text
        cd = resp.headers["content-disposition"]
        assert "attachment" in cd
        assert rid[:8] in cd
        assert cd.endswith(".md")

    def test_download_404_for_unknown_report(self, client):
        headers = _register(client, "report_404@test.com")
        client.cookies.clear()
        resp = client.get(
            "/api/report/nonexistent-id/download", headers=headers
        )
        assert resp.status_code == 404

    def test_download_cross_user_isolated(self, client, analysis_with_report):
        """User B cannot download User A's report (gets 404)."""
        a_headers, aid, rid = analysis_with_report
        b_headers = _register(client, "report_b@test.com")
        client.cookies.clear()
        resp = client.get(f"/api/report/{rid}/download", headers=b_headers)
        assert resp.status_code == 404

    def test_download_requires_auth(self, client):
        assert (
            client.get("/api/report/some/download").status_code == 403
        )
