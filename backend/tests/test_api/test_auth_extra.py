"""Tests for the remaining auth endpoints: logout, update profile, password strength.

These cover the user-auth path that test_auth.py leaves out: after register/login/me,
the user can log out, edit their nickname, and check password strength before signing up.
"""

TEST_EMAIL = "auth_extra@test.com"
TEST_PASSWORD = "secret123"


def _register(client, email=TEST_EMAIL):
    resp = client.post(
        "/api/auth/register",
        json={"email": email, "password": TEST_PASSWORD},
    )
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------


class TestLogout:
    def test_logout_invalidates_token(self, client):
        """After logout, the same JWT must no longer authenticate."""
        headers = _register(client)

        # Token works before logout
        assert client.get("/api/auth/me", headers=headers).status_code == 200

        resp = client.post("/api/auth/logout", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["detail"] == "已登出"

        # Token is now blacklisted → 401 (invalid credentials, not 403)
        assert client.get("/api/auth/me", headers=headers).status_code == 401

    def test_logout_requires_auth(self, client):
        assert client.post("/api/auth/logout").status_code == 403

    def test_logout_idempotent(self, client):
        """Calling logout twice with the same token does not 500.

        The first logout blacklists the jti; the second call's auth dependency
        rejects the now-blacklisted token (401) before reaching the handler —
        which is the expected, safe behavior (no duplicate insert, no error).
        """
        headers = _register(client, "logout_idem@test.com")
        assert client.post("/api/auth/logout", headers=headers).status_code == 200
        assert client.post("/api/auth/logout", headers=headers).status_code == 401


# ---------------------------------------------------------------------------
# PUT /api/auth/me — update profile
# ---------------------------------------------------------------------------


class TestUpdateProfile:
    def test_update_profile_changes_nickname(self, client):
        headers = _register(client, "profile1@test.com")
        resp = client.put(
            "/api/auth/me", headers=headers, json={"nickname": "稳健投资者"}
        )
        assert resp.status_code == 200
        assert resp.json()["nickname"] == "稳健投资者"

        # Persisted: GET /me reflects the new nickname
        me = client.get("/api/auth/me", headers=headers).json()
        assert me["nickname"] == "稳健投资者"

    def test_update_profile_rejects_short_nickname(self, client):
        headers = _register(client, "profile2@test.com")
        resp = client.put(
            "/api/auth/me", headers=headers, json={"nickname": "短"}
        )
        assert resp.status_code == 400

    def test_update_profile_rejects_long_nickname(self, client):
        headers = _register(client, "profile3@test.com")
        resp = client.put(
            "/api/auth/me",
            headers=headers,
            json={"nickname": "超" * 21},
        )
        assert resp.status_code == 400

    def test_update_profile_requires_auth(self, client):
        assert (
            client.put("/api/auth/me", json={"nickname": "x"}).status_code == 403
        )


# ---------------------------------------------------------------------------
# POST /api/auth/password-strength
# ---------------------------------------------------------------------------


class TestPasswordStrength:
    def test_weak_password(self, client):
        """Too short → err set, score 0, label 弱."""
        resp = client.post(
            "/api/auth/password-strength", json={"password": "abc"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["score"] == 0
        assert body["label"] == "弱"
        assert body["hint"]  # non-empty error message

    def test_common_password_rejected(self, client):
        """A common weak password is rejected even if it meets length rules."""
        resp = client.post(
            "/api/auth/password-strength", json={"password": "12345678"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["hint"]  # rejected → hint non-empty
        assert body["score"] == 0

    def test_strong_password(self, client):
        """Length>=12 + upper + lower + digit + symbol → score 4."""
        resp = client.post(
            "/api/auth/password-strength", json={"password": "Abcd1234!@#$"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["score"] == 4
        assert body["label"] == "很强"
        assert body["hint"] == ""

    def test_medium_password(self, client):
        """Letters + digits but no symbol, short → score 2 (digit + mix-case)."""
        resp = client.post(
            "/api/auth/password-strength", json={"password": "Secret123"}
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["score"] == 2
        assert body["hint"] == ""

    def test_password_strength_no_auth_required(self, client):
        """Pre-registration check: must work without a token."""
        resp = client.post(
            "/api/auth/password-strength", json={"password": "Anypass1!"}
        )
        assert resp.status_code == 200
