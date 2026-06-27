"""Tests for the admin API surface (all 7 endpoints had zero coverage).

User path: an admin logs in (separate admin-scope token), then can search
users, inspect their files/analyses, and download any user's raw files /
analysis snapshots / reports. This is the operator/audit surface.
"""

import json

import pytest

from app.auth.jwt import create_token, hash_password
from app.models.user import User

QMT_CSV = (
    "委托时间,证券代码,证券名称,买卖方向,成交价格,成交数量,手续费\n"
    "2024-01-05 09:30:00,000001,平安银行,买入,10.50,1000,5.00\n"
    "2024-01-10 14:00:00,000001,平安银行,卖出,11.00,1000,5.00"
)
MOCK_REPORT = "## 核心结论\nadmin 测试报告"

ADMIN_EMAIL = "admin@test.com"
ADMIN_PASSWORD = "admin-secret1"
TEST_PASSWORD = "secret123"


def _register(client, email):
    resp = client.post(
        "/api/auth/register", json={"email": email, "password": TEST_PASSWORD}
    )
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _import(client, headers, csv, name="t.csv"):
    r = client.post(
        "/api/upload", headers=headers, files={"file": (name, csv, "text/csv")}
    )
    fid = r.json()["raw_file_id"]
    client.post(
        "/api/upload/confirm",
        headers=headers,
        json={"raw_file_id": fid, "source_type": "smart"},
    )
    client.post(
        "/api/upload/import", headers=headers, json={"raw_file_id": fid}
    )
    return fid


def _run(client, headers, fid):
    return client.post(
        "/api/analysis/run",
        headers=headers,
        json={
            "date_start": "2024-01-01",
            "date_end": "2024-12-31",
            "raw_file_id": fid,
        },
    ).json()["analysis_id"]


def _generate(client, headers, aid):
    from unittest.mock import AsyncMock, patch

    with patch("app.api.report.get_llm") as m:
        p = AsyncMock()
        p.generate = AsyncMock(return_value=MOCK_REPORT)
        m.return_value = p
        return client.post(
            "/api/report/generate", headers=headers, json={"analysis_id": aid}
        ).json()["report_id"]


@pytest.fixture
def admin_token(db_session):
    """Create an admin user directly in the DB and mint an admin-scope token."""
    admin = User(
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        is_admin=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    token = create_token(admin.id, scope="admin")
    db_session.rollback()  # release snapshot so later queries see fresh state
    return {"Authorization": f"Bearer {token}"}, admin.id


@pytest.fixture
def user_with_data(client):
    """A regular user with a file, analysis, and report."""
    headers = _register(client, "u1@test.com")
    client.cookies.clear()
    fid = _import(client, headers, QMT_CSV)
    aid = _run(client, headers, fid)
    rid = _generate(client, headers, aid)
    return headers, fid, aid, rid


# ---------------------------------------------------------------------------
# POST /api/admin/login
# ---------------------------------------------------------------------------


class TestAdminLogin:
    def test_admin_login_success(self, client, admin_token):
        resp = client.post(
            "/api/admin/login",
            json={"username": ADMIN_EMAIL, "password": ADMIN_PASSWORD},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["token_type"] == "bearer"
        assert "access_token" in body

    def test_admin_login_wrong_password(self, client, admin_token):
        resp = client.post(
            "/api/admin/login",
            json={"username": ADMIN_EMAIL, "password": "wrong-pass"},
        )
        assert resp.status_code == 401

    def test_admin_login_rejects_non_admin_user(self, client):
        """A regular user cannot log in via the admin endpoint."""
        _register(client, "nonadmin@test.com")
        resp = client.post(
            "/api/admin/login",
            json={"username": "nonadmin@test.com", "password": TEST_PASSWORD},
        )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Authorization: every admin endpoint requires admin scope
# ---------------------------------------------------------------------------


class TestAdminAuthorization:
    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/admin/users"),
            ("GET", "/api/admin/users/some-id/files"),
            ("GET", "/api/admin/users/some-id/analyses"),
            ("GET", "/api/admin/download/raw/some-id"),
            ("GET", "/api/admin/download/analysis/some-id"),
            ("GET", "/api/admin/download/report/some-id"),
        ],
    )
    def test_admin_endpoints_reject_no_token(self, client, method, path):
        assert client.request(method, path).status_code == 403

    def test_admin_endpoints_reject_regular_user(self, client, user_with_data):
        """A normal (non-admin) user token must be rejected (403)."""
        headers, _, _, _ = user_with_data
        client.cookies.clear()
        for path in (
            "/api/admin/users",
            "/api/admin/users/x/files",
            "/api/admin/users/x/analyses",
            "/api/admin/download/raw/x",
            "/api/admin/download/analysis/x",
            "/api/admin/download/report/x",
        ):
            assert client.get(path, headers=headers).status_code == 403

    def test_admin_token_without_scope_rejected(self, client, db_session, admin_token):
        """An admin user's *normal* token (no admin scope) is still rejected."""
        _, admin_id = admin_token
        normal_token = create_token(admin_id)  # no scope
        headers = {"Authorization": f"Bearer {normal_token}"}
        assert client.get("/api/admin/users", headers=headers).status_code == 403


# ---------------------------------------------------------------------------
# GET /api/admin/users — search with pre-aggregated counts
# ---------------------------------------------------------------------------


class TestAdminSearchUsers:
    def test_search_users_returns_counts(self, client, admin_token, user_with_data):
        headers, _, _, _ = user_with_data
        _, uid = _register(client, "u2@test.com"), None
        admin_headers, _ = admin_token
        client.cookies.clear()
        resp = client.get("/api/admin/users", headers=admin_headers)
        assert resp.status_code == 200
        users = resp.json()
        # At least the regular user + the admin exist
        assert len(users) >= 2
        target = next(u for u in users if u["email"] == "u1@test.com")
        assert target["file_count"] == 1
        assert target["analysis_count"] == 1
        assert target["report_count"] == 1

    def test_search_users_with_query(self, client, admin_token, user_with_data):
        admin_headers, _ = admin_token
        client.cookies.clear()
        resp = client.get("/api/admin/users?q=u1", headers=admin_headers)
        assert resp.status_code == 200
        users = resp.json()
        assert any(u["email"] == "u1@test.com" for u in users)
        # admin email does not match 'u1'
        assert all(u["email"] != ADMIN_EMAIL for u in users)


# ---------------------------------------------------------------------------
# GET /api/admin/users/{id}/files  and  /analyses
# ---------------------------------------------------------------------------


class TestAdminUserFilesAndAnalyses:
    def test_get_user_files(self, client, admin_token, user_with_data):
        _, fid, _, _ = user_with_data
        admin_headers, admin_id = admin_token
        client.cookies.clear()
        resp = client.get(
            f"/api/admin/users/{_user_id(client, user_with_data[0])}/files",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        files = resp.json()
        assert any(f["id"] == fid for f in files)

    def test_get_user_analyses(self, client, admin_token, user_with_data):
        _, _, aid, _ = user_with_data
        admin_headers, _ = admin_token
        client.cookies.clear()
        resp = client.get(
            f"/api/admin/users/{_user_id(client, user_with_data[0])}/analyses",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        analyses = resp.json()
        assert any(a["id"] == aid for a in analyses)
        target = next(a for a in analyses if a["id"] == aid)
        assert target["has_snapshot"] is True
        assert target["has_report"] is True

    def test_get_user_files_empty(self, client, admin_token):
        """A user with no files returns an empty list (not 404)."""
        headers = _register(client, "emptyuser@test.com")
        admin_headers, _ = admin_token
        client.cookies.clear()
        resp = client.get(
            f"/api/admin/users/{_user_id(client, headers)}/files",
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []


def _user_id(client, headers):
    """Resolve the user id behind a bearer token (admin needs it for path)."""
    from jose import jwt

    token = headers["Authorization"].split(" ", 1)[1]
    return jwt.get_unverified_claims(token)["sub"]


# ---------------------------------------------------------------------------
# Admin downloads
# ---------------------------------------------------------------------------


class TestAdminDownloads:
    def test_download_raw_file(self, client, admin_token, user_with_data):
        headers, fid, _, _ = user_with_data
        admin_headers, _ = admin_token
        client.cookies.clear()
        resp = client.get(
            f"/api/admin/download/raw/{fid}", headers=admin_headers
        )
        assert resp.status_code == 200
        assert "attachment" in resp.headers["content-disposition"]
        assert b"000001" in resp.content or "000001" in resp.text

    def test_download_raw_404(self, client, admin_token):
        admin_headers, _ = admin_token
        client.cookies.clear()
        assert (
            client.get(
                "/api/admin/download/raw/nonexistent", headers=admin_headers
            ).status_code
            == 404
        )

    def test_download_analysis_snapshot(self, client, admin_token, user_with_data):
        _, _, aid, _ = user_with_data
        admin_headers, _ = admin_token
        client.cookies.clear()
        resp = client.get(
            f"/api/admin/download/analysis/{aid}", headers=admin_headers
        )
        assert resp.status_code == 200
        data = json.loads(resp.content)
        assert data["id"] == aid
        assert "stats_snapshot" in data
        assert data["stats_snapshot"] is not None

    def test_download_analysis_404(self, client, admin_token):
        admin_headers, _ = admin_token
        client.cookies.clear()
        assert (
            client.get(
                "/api/admin/download/analysis/nonexistent", headers=admin_headers
            ).status_code
            == 404
        )

    def test_download_report(self, client, admin_token, user_with_data):
        _, _, _, rid = user_with_data
        admin_headers, _ = admin_token
        client.cookies.clear()
        resp = client.get(
            f"/api/admin/download/report/{rid}", headers=admin_headers
        )
        assert resp.status_code == 200
        assert MOCK_REPORT in resp.text

    def test_download_report_404(self, client, admin_token):
        admin_headers, _ = admin_token
        client.cookies.clear()
        assert (
            client.get(
                "/api/admin/download/report/nonexistent", headers=admin_headers
            ).status_code
            == 404
        )

    def test_admin_can_download_any_user_data(self, client, admin_token, user_with_data):
        """Admin is not user-scoped: it can download any user's resources.
        This is the intended design (operator audit), not a leak."""
        _, fid, aid, rid = user_with_data
        admin_headers, _ = admin_token
        client.cookies.clear()
        assert client.get(
            f"/api/admin/download/raw/{fid}", headers=admin_headers
        ).status_code == 200
        assert client.get(
            f"/api/admin/download/analysis/{aid}", headers=admin_headers
        ).status_code == 200
        assert client.get(
            f"/api/admin/download/report/{rid}", headers=admin_headers
        ).status_code == 200
