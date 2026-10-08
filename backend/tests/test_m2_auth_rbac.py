"""M2 tests — Auth + Multi-Tenancy + RBAC.

Tests:
1. JWT token creation / decoding
2. Token expiry and type validation
3. Signup flow
4. Login success / failure
5. Logout / refresh token revocation
6. /me endpoint
7. RBAC: role permission checks
8. Tenant isolation: Org A cannot access Org B data
9. Platform roles bypass org checks
10. Refresh token flow
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# Test: JWT tokens
# ---------------------------------------------------------------------------
class TestJWTTokens:
    def test_create_access_token(self):
        from backend.core.auth import create_access_token, decode_access_token
        token = create_access_token("user-1", "a@b.com", "organization_owner", "org-1")
        assert isinstance(token, str)
        payload = decode_access_token(token)
        assert payload["sub"] == "user-1"
        assert payload["email"] == "a@b.com"
        assert payload["role"] == "organization_owner"
        assert payload["org"] == "org-1"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        from backend.core.auth import create_refresh_token, decode_refresh_token
        token, jti = create_refresh_token("user-1", "a@b.com", "viewer", "org-1")
        assert isinstance(token, str)
        assert isinstance(jti, str)
        payload = decode_refresh_token(token)
        assert payload["sub"] == "user-1"
        assert payload["type"] == "refresh"
        assert payload["jti"] == jti

    def test_access_token_wrong_type_rejected(self):
        from backend.core.auth import create_refresh_token, decode_access_token, AuthError
        token, _ = create_refresh_token("u", "a@b.com", "viewer", None)
        with pytest.raises(AuthError):
            decode_access_token(token)

    def test_refresh_token_wrong_type_rejected(self):
        from backend.core.auth import create_access_token, decode_refresh_token, AuthError
        token = create_access_token("u", "a@b.com", "viewer", None)
        with pytest.raises(AuthError):
            decode_refresh_token(token)

    def test_invalid_token_rejected(self):
        from backend.core.auth import decode_access_token, AuthError
        with pytest.raises(AuthError):
            decode_access_token("not.a.valid.jwt")

    def test_tampered_token_rejected(self):
        from backend.core.auth import create_access_token, decode_access_token, AuthError
        token = create_access_token("u", "a@b.com", "viewer", None)
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(AuthError):
            decode_access_token(tampered)

    def test_platform_user_token(self):
        from backend.core.auth import create_access_token, decode_access_token
        token = create_access_token("admin-1", "admin@platform.com", "platform_admin", None)
        payload = decode_access_token(token)
        assert payload["org"] is None
        assert payload["role"] == "platform_admin"

    def test_token_pair_structure(self):
        from backend.core.auth import create_token_pair
        pair = create_token_pair("u", "a@b.com", "viewer", "org-1")
        assert "access_token" in pair
        assert "refresh_token" in pair
        assert "jti" in pair
        assert pair["token_type"] == "bearer"
        assert pair["expires_in"] > 0


# ---------------------------------------------------------------------------
# Test: CurrentUser model
# ---------------------------------------------------------------------------
class TestCurrentUser:
    def test_is_platform_false_for_org_user(self):
        from backend.core.auth import CurrentUser
        u = CurrentUser("id", "a@b.com", "organization_owner", "org-1")
        assert u.is_platform is False

    def test_is_platform_true_for_platform_roles(self):
        from backend.core.auth import CurrentUser
        for role in ["platform_owner", "platform_admin", "support", "billing_admin"]:
            u = CurrentUser("id", "a@b.com", role, None)
            assert u.is_platform is True, f"Expected is_platform for {role}"

    def test_org_user_has_org_id(self):
        from backend.core.auth import CurrentUser
        u = CurrentUser("id", "a@b.com", "manager", "org-abc")
        assert u.org_id == "org-abc"


# ---------------------------------------------------------------------------
# Test: RBAC permission matrix
# ---------------------------------------------------------------------------
class TestRBACPermissions:
    def test_org_role_hierarchy(self):
        from backend.core.rbac import _org_level
        assert _org_level("viewer") < _org_level("agent")
        assert _org_level("agent") < _org_level("manager")
        assert _org_level("manager") < _org_level("organization_admin")
        assert _org_level("organization_admin") < _org_level("organization_owner")

    def test_unknown_role_has_negative_level(self):
        from backend.core.rbac import _org_level
        assert _org_level("unknown_role") < 0

    def test_assert_org_access_passes_for_same_org(self):
        from backend.core.auth import CurrentUser
        from backend.core.rbac import assert_org_access
        user = CurrentUser("id", "a@b.com", "manager", "org-A")
        # Should not raise
        assert_org_access(user, "org-A")

    def test_assert_org_access_blocks_different_org(self):
        from backend.core.auth import CurrentUser, PermissionError
        from backend.core.rbac import assert_org_access
        user = CurrentUser("id", "a@b.com", "manager", "org-A")
        with pytest.raises(PermissionError):
            assert_org_access(user, "org-B")

    def test_platform_user_passes_org_access(self):
        from backend.core.auth import CurrentUser
        from backend.core.rbac import assert_org_access
        for role in ["platform_owner", "platform_admin", "support", "billing_admin"]:
            user = CurrentUser("id", "a@b.com", role, None)
            # Should not raise for any org
            assert_org_access(user, "org-any")

    def test_platform_resource_requires_platform_role(self):
        from backend.core.auth import CurrentUser, PermissionError
        from backend.core.rbac import assert_org_access
        user = CurrentUser("id", "a@b.com", "organization_owner", "org-1")
        with pytest.raises(PermissionError):
            assert_org_access(user, None)  # None = platform-owned resource

    def test_platform_user_can_access_platform_resource(self):
        from backend.core.auth import CurrentUser
        from backend.core.rbac import assert_org_access
        user = CurrentUser("id", "a@b.com", "platform_admin", None)
        # Should not raise
        assert_org_access(user, None)


# ---------------------------------------------------------------------------
# Test: FastAPI auth endpoints (using TestClient with mocked DB)
# ---------------------------------------------------------------------------
def _get_test_app():
    """Build a test FastAPI app with in-memory MongoDB."""
    import mongomock_motor
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.core import db as db_module, redis as redis_module

    return app


def _mongomock_available():
    try:
        import mongomock_motor
        return True
    except ImportError:
        return False


SKIP_IF_NO_MONGOMOCK = pytest.mark.skipif(
    not _mongomock_available(),
    reason="mongomock_motor not installed"
)


@SKIP_IF_NO_MONGOMOCK
class TestAuthEndpoints:
    """Test auth endpoints using TestClient + mongomock."""

    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.core import db as db_module

        # Minimal test app
        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")

        # Inject mock db
        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        self.client = TestClient(self.test_app)

    def test_signup_creates_org_and_user(self):
        resp = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Test Org",
            "org_email": "org@test.com",
            "email": "owner@test.com",
            "password": "SecurePass1!",
            "first_name": "Test",
            "last_name": "Owner",
        })
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["organization_id"] is not None

    def test_signup_duplicate_email_rejected(self):
        self.client.post("/api/v1/auth/signup", json={
            "org_name": "Org A",
            "org_email": "org-a@test.com",
            "email": "dup@test.com",
            "password": "SecurePass1!",
        })
        resp = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Org B",
            "org_email": "org-b@test.com",
            "email": "dup@test.com",  # same user email
            "password": "SecurePass1!",
        })
        assert resp.status_code == 409

    def test_signup_short_password_rejected(self):
        resp = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Org",
            "org_email": "x@test.com",
            "email": "user@test.com",
            "password": "short",
        })
        assert resp.status_code == 422

    def test_login_success(self):
        self.client.post("/api/v1/auth/signup", json={
            "org_name": "Login Org",
            "org_email": "login-org@test.com",
            "email": "login@test.com",
            "password": "LoginPass1!",
        })
        resp = self.client.post("/api/v1/auth/login", json={
            "email": "login@test.com",
            "password": "LoginPass1!",
        })
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "access_token" in data
        assert data["user"]["email"] == "login@test.com"

    def test_login_wrong_password(self):
        self.client.post("/api/v1/auth/signup", json={
            "org_name": "WP Org",
            "org_email": "wp-org@test.com",
            "email": "wp@test.com",
            "password": "CorrectPass1!",
        })
        resp = self.client.post("/api/v1/auth/login", json={
            "email": "wp@test.com",
            "password": "WrongPass",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self):
        resp = self.client.post("/api/v1/auth/login", json={
            "email": "ghost@nowhere.com",
            "password": "anything",
        })
        assert resp.status_code == 401

    def test_me_with_valid_token(self):
        signup_resp = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Me Org",
            "org_email": "me-org@test.com",
            "email": "me@test.com",
            "password": "MePass1234!",
        })
        token = signup_resp.json()["access_token"]
        resp = self.client.get("/api/v1/auth/me",
                               headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["email"] == "me@test.com"
        assert data["role"] == "organization_owner"

    def test_me_without_token_returns_401(self):
        resp = self.client.get("/api/v1/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token_returns_401(self):
        resp = self.client.get("/api/v1/auth/me",
                               headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Test: Multi-tenancy isolation (cross-org data access denial)
# ---------------------------------------------------------------------------
@SKIP_IF_NO_MONGOMOCK
class TestMultiTenancyIsolation:
    """Critical: Org A must NOT be able to access Org B data."""

    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.organizations import router as org_router
        from backend.api.v1.users import router as user_router
        from backend.core import db as db_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(org_router, prefix="/api/v1")
        self.test_app.include_router(user_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        self.client = TestClient(self.test_app)

        # Sign up two orgs
        r1 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Org Alpha",
            "org_email": "alpha@corp.com",
            "email": "alpha-owner@corp.com",
            "password": "AlphaPass1!",
        })
        self.token_a = r1.json()["access_token"]
        self.org_id_a = r1.json()["organization_id"]

        r2 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Org Beta",
            "org_email": "beta@corp.com",
            "email": "beta-owner@corp.com",
            "password": "BetaPass1!",
        })
        self.token_b = r2.json()["access_token"]
        self.org_id_b = r2.json()["organization_id"]

    def _headers(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def test_org_a_can_read_own_org(self):
        resp = self.client.get(
            f"/api/v1/organizations/{self.org_id_a}",
            headers=self._headers(self.token_a),
        )
        assert resp.status_code == 200
        assert resp.json()["id"] == self.org_id_a

    def test_org_a_cannot_read_org_b(self):
        """CRITICAL: Org A must receive 403 when accessing Org B."""
        resp = self.client.get(
            f"/api/v1/organizations/{self.org_id_b}",
            headers=self._headers(self.token_a),
        )
        assert resp.status_code == 403, (
            f"TENANT ISOLATION FAILURE: Org A accessed Org B data! "
            f"Status: {resp.status_code}, Body: {resp.text}"
        )

    def test_org_b_cannot_read_org_a(self):
        """CRITICAL: Org B must receive 403 when accessing Org A."""
        resp = self.client.get(
            f"/api/v1/organizations/{self.org_id_a}",
            headers=self._headers(self.token_b),
        )
        assert resp.status_code == 403, (
            f"TENANT ISOLATION FAILURE: Org B accessed Org A data! "
            f"Status: {resp.status_code}, Body: {resp.text}"
        )

    def test_org_a_cannot_list_org_b_users(self):
        """Org A cannot list users of Org B."""
        resp = self.client.get(
            f"/api/v1/users/org/{self.org_id_b}",
            headers=self._headers(self.token_a),
        )
        assert resp.status_code == 403

    def test_unauthenticated_request_denied(self):
        resp = self.client.get(f"/api/v1/organizations/{self.org_id_a}")
        assert resp.status_code == 401

    def test_org_b_cannot_update_org_a(self):
        resp = self.client.patch(
            f"/api/v1/organizations/{self.org_id_a}",
            json={"name": "HACKED"},
            headers=self._headers(self.token_b),
        )
        assert resp.status_code == 403

    def test_org_a_can_list_own_users(self):
        resp = self.client.get(
            f"/api/v1/users/org/{self.org_id_a}",
            headers=self._headers(self.token_a),
        )
        assert resp.status_code == 200
        users = resp.json()
        # Only org A users should be visible
        for u in users:
            assert u["organization_id"] == self.org_id_a


# ---------------------------------------------------------------------------
# Test: RBAC via HTTP
# ---------------------------------------------------------------------------
@SKIP_IF_NO_MONGOMOCK
class TestRBACHTTP:
    """Role-based access control enforced at the HTTP layer."""

    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.organizations import router as org_router
        from backend.api.v1.users import router as user_router
        from backend.core import db as db_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(org_router, prefix="/api/v1")
        self.test_app.include_router(user_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        db_module._db = client["test"]

        self.client = TestClient(self.test_app)

        # Create owner and invite a viewer
        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "RBAC Org",
            "org_email": "rbac@org.com",
            "email": "owner@rbac.com",
            "password": "OwnerPass1!",
        })
        self.owner_token = r.json()["access_token"]
        self.org_id = r.json()["organization_id"]

        # Invite a viewer
        invite_resp = self.client.post(
            f"/api/v1/users/org/{self.org_id}/invite",
            json={
                "email": "viewer@rbac.com",
                "password": "ViewerPass1!",
                "role": "viewer",
            },
            headers={"Authorization": f"Bearer {self.owner_token}"},
        )
        assert invite_resp.status_code == 201
        # Login as viewer
        login_resp = self.client.post("/api/v1/auth/login", json={
            "email": "viewer@rbac.com",
            "password": "ViewerPass1!",
        })
        self.viewer_token = login_resp.json()["access_token"]

    def _auth(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}"}

    def test_owner_can_update_org(self):
        resp = self.client.patch(
            f"/api/v1/organizations/{self.org_id}",
            json={"name": "Updated Name"},
            headers=self._auth(self.owner_token),
        )
        assert resp.status_code == 200

    def test_viewer_cannot_update_org(self):
        """Viewer does not have organization_admin role."""
        resp = self.client.patch(
            f"/api/v1/organizations/{self.org_id}",
            json={"name": "Hacked"},
            headers=self._auth(self.viewer_token),
        )
        assert resp.status_code == 403

    def test_viewer_can_read_org(self):
        resp = self.client.get(
            f"/api/v1/organizations/{self.org_id}",
            headers=self._auth(self.viewer_token),
        )
        assert resp.status_code == 200

    def test_viewer_cannot_invite_users(self):
        resp = self.client.post(
            f"/api/v1/users/org/{self.org_id}/invite",
            json={"email": "new@rbac.com", "password": "NewPass1!", "role": "agent"},
            headers=self._auth(self.viewer_token),
        )
        assert resp.status_code == 403

    def test_owner_can_invite_users(self):
        resp = self.client.post(
            f"/api/v1/users/org/{self.org_id}/invite",
            json={"email": "agent@rbac.com", "password": "AgentPass1!", "role": "agent"},
            headers=self._auth(self.owner_token),
        )
        assert resp.status_code == 201

    def test_cannot_assign_platform_role_via_invite(self):
        resp = self.client.post(
            f"/api/v1/users/org/{self.org_id}/invite",
            json={"email": "fake-admin@rbac.com", "password": "Pass1!", "role": "platform_owner"},
            headers=self._auth(self.owner_token),
        )
        assert resp.status_code == 400

    def test_viewer_can_read_own_profile(self):
        # Decode viewer user_id from token
        from backend.core.auth import decode_access_token
        payload = decode_access_token(self.viewer_token)
        user_id = payload["sub"]
        resp = self.client.get(
            f"/api/v1/users/{user_id}",
            headers=self._auth(self.viewer_token),
        )
        assert resp.status_code == 200

    def test_viewer_cannot_deactivate_other_users(self):
        # Invite another user
        invite = self.client.post(
            f"/api/v1/users/org/{self.org_id}/invite",
            json={"email": "target@rbac.com", "password": "TargetPass1!", "role": "agent"},
            headers=self._auth(self.owner_token),
        )
        target_id = invite.json()["id"]
        resp = self.client.delete(
            f"/api/v1/users/{target_id}",
            headers=self._auth(self.viewer_token),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Test: Token refresh
# ---------------------------------------------------------------------------
@SKIP_IF_NO_MONGOMOCK
class TestTokenRefresh:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        db_module._db = client["test"]

        # Mock Redis for refresh token revocation
        self._redis_store = {}

        async def fake_set(key, val, ex=None):
            self._redis_store[key] = val

        async def fake_exists(key):
            return 1 if key in self._redis_store else 0

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock(side_effect=fake_set)
        mock_redis.exists = AsyncMock(side_effect=fake_exists)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

    def test_refresh_returns_new_access_token(self):
        # Signup
        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Refresh Org",
            "org_email": "ref-org@t.com",
            "email": "ref@t.com",
            "password": "RefreshPass1!",
        })
        refresh_token = r.json()["refresh_token"]

        resp = self.client.post("/api/v1/auth/refresh",
                                json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        # New access token should be different from original
        assert data["access_token"] != r.json()["access_token"]

    def test_logout_revokes_refresh_token(self):
        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Logout Org",
            "org_email": "logout-org@t.com",
            "email": "logout@t.com",
            "password": "LogoutPass1!",
        })
        access_token = r.json()["access_token"]
        refresh_token = r.json()["refresh_token"]

        # Logout
        self.client.post("/api/v1/auth/logout",
                         json={"refresh_token": refresh_token},
                         headers={"Authorization": f"Bearer {access_token}"})

        # Refresh should now fail (token revoked)
        resp = self.client.post("/api/v1/auth/refresh",
                                json={"refresh_token": refresh_token})
        assert resp.status_code == 401

    def test_invalid_refresh_token_rejected(self):
        resp = self.client.post("/api/v1/auth/refresh",
                                json={"refresh_token": "invalid.token.here"})
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
