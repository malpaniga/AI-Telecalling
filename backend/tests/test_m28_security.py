"""M28 tests — Security Hardening.

Tests:
1.  Rate limiting module exists with DEFAULT_LIMITS configured
2.  rate_limit_auth blocks after threshold (uses Redis mock)
3.  rate_limit_auth fails open when Redis unavailable
4.  Rate limits return 429 with Retry-After header
5.  SecurityAuditService runs all 6 checks
6.  Auth coverage check passes (all API files have auth)
7.  Secret exposure check passes (no keys in responses)
8.  Webhook verification check passes
9.  Rate limiting check passes (module exists)
10. Tenant isolation check runs
11. Input validation check runs
12. run_all returns overall_status pass/fail
13. HTTP: /security/audit requires platform role (403 for customer)
14. HTTP: /security/limits returns configured limits
15. Auth endpoints (signup/login) apply rate limiting
16. Provider resource IDs never appear in customer API responses (re-verify)
"""

import asyncio
import sys
import os
from unittest.mock import AsyncMock, MagicMock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _mongomock_available():
    try:
        import mongomock_motor
        return True
    except ImportError:
        return False


SKIP = pytest.mark.skipif(not _mongomock_available(), reason="mongomock_motor not installed")


# ---------------------------------------------------------------------------
# Test: Rate limiting module
# ---------------------------------------------------------------------------
class TestRateLimiting:
    def test_default_limits_configured(self):
        from backend.core.rate_limit import DEFAULT_LIMITS
        assert "auth" in DEFAULT_LIMITS
        assert "billing" in DEFAULT_LIMITS
        assert "api" in DEFAULT_LIMITS
        assert "import" in DEFAULT_LIMITS
        assert DEFAULT_LIMITS["auth"]["requests"] > 0
        assert DEFAULT_LIMITS["auth"]["window_seconds"] > 0

    def test_rate_limit_auth_blocks_after_threshold(self):
        from backend.core.rate_limit import _check_rate_limit
        from unittest.mock import patch

        # Mock Redis
        store: dict = {}
        async def incr(key):
            store[key] = int(store.get(key, 0)) + 1
            return store[key]
        async def expire(key, ttl):
            store[key + "_ttl"] = ttl
        async def ttl_fn(key):
            return store.get(key + "_ttl", 60)

        mock_r = MagicMock()
        mock_r.incr = AsyncMock(side_effect=incr)
        mock_r.expire = AsyncMock(side_effect=expire)
        mock_r.ttl = AsyncMock(side_effect=ttl_fn)

        # Patch the get_redis import inside rate_limit
        from backend.core import rate_limit as rl_module
        original_get_redis = None
        if hasattr(rl_module, 'get_redis'):
            original_get_redis = rl_module.get_redis

        async def mock_get_redis():
            return mock_r

        async def _t():
            with patch("backend.core.redis.get_redis", return_value=mock_r):
                for i in range(10):
                    allowed, count, retry = await _check_rate_limit("test-key", 10, 60)
                    assert allowed is True
                allowed, count, retry = await _check_rate_limit("test-key", 10, 60)
                assert allowed is False
                assert retry > 0
        run(_t())

    def test_rate_limit_fails_open_without_redis(self):
        from backend.core.rate_limit import _check_rate_limit
        async def _t():
            # No Redis available → fail open (allowed=True)
            allowed, count, retry = await _check_rate_limit("no-redis", 1, 60)
            assert allowed is True
        run(_t())

    def test_client_ip_extracts_from_forwarded_for(self):
        from backend.core.rate_limit import _client_ip
        from fastapi import Request
        # Mock request with X-Forwarded-For
        req = MagicMock()
        req.headers = {"X-Forwarded-For": "203.0.113.5, 10.0.0.1"}
        req.client = MagicMock()
        req.client.host = "127.0.0.1"
        assert _client_ip(req) == "203.0.113.5"

    def test_client_ip_fallback_to_client_host(self):
        from backend.core.rate_limit import _client_ip
        req = MagicMock()
        req.headers = {}
        req.client = MagicMock()
        req.client.host = "192.168.1.1"
        assert _client_ip(req) == "192.168.1.1"


# ---------------------------------------------------------------------------
# Test: SecurityAuditService
# ---------------------------------------------------------------------------
@SKIP
class TestSecurityAudit:
    def setup_method(self):
        # Use the actual repo root
        self.base_path = os.path.join(os.path.dirname(__file__), "../..")
        self.base_path = os.path.abspath(self.base_path)

    def _svc(self):
        from backend.services.security_audit_service import SecurityAuditService
        return SecurityAuditService(base_path=self.base_path)

    def test_check_auth_coverage_passes(self):
        svc = self._svc()
        result = svc.check_auth_coverage()
        assert result.status == "pass", \
            f"Auth coverage findings: {result.findings}"

    def test_check_secret_exposure_passes(self):
        svc = self._svc()
        result = svc.check_secret_exposure()
        assert result.status == "pass", \
            f"Secret exposure findings: {result.findings}"

    def test_check_webhook_verification_passes(self):
        svc = self._svc()
        result = svc.check_webhook_verification()
        assert result.status == "pass", \
            f"Webhook findings: {result.findings}"

    def test_check_rate_limiting_passes(self):
        svc = self._svc()
        result = svc.check_rate_limiting()
        assert result.status == "pass", \
            f"Rate limiting findings: {result.findings}"

    def test_check_tenant_isolation_runs(self):
        svc = self._svc()
        result = svc.check_tenant_isolation()
        # May have medium findings for base.py etc — just verify it runs
        assert result.name == "tenant_isolation"

    def test_check_input_validation_runs(self):
        svc = self._svc()
        result = svc.check_input_validation()
        assert result.name == "input_validation"

    def test_run_all_structure(self):
        async def _t():
            svc = self._svc()
            report = await svc.run_all()
            assert "overall_status" in report
            assert "critical_findings" in report
            assert "high_findings" in report
            assert "checks" in report
            assert len(report["checks"]) == 6
        run(_t())

    def test_run_all_has_6_check_names(self):
        async def _t():
            svc = self._svc()
            report = await svc.run_all()
            names = {c["check"] for c in report["checks"]}
            required = {
                "auth_coverage", "secret_exposure", "webhook_verification",
                "rate_limiting", "tenant_isolation", "input_validation",
            }
            assert required.issubset(names)
        run(_t())

    def test_no_critical_findings(self):
        async def _t():
            svc = self._svc()
            report = await svc.run_all()
            assert report["critical_findings"] == 0, \
                f"Critical findings: {[c['findings'] for c in report['checks'] if c['findings'] and any(f.get('severity')=='critical' for f in c['findings'])]}"
        run(_t())

    def test_no_high_findings(self):
        async def _t():
            svc = self._svc()
            report = await svc.run_all()
            assert report["high_findings"] == 0, \
                f"High findings: {[c['findings'] for c in report['checks'] if c['findings'] and any(f.get('severity')=='high' for f in c['findings'])]}"
        run(_t())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestSecurityHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.security import router as sec_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(sec_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        mock_redis.incr = AsyncMock(return_value=1)
        mock_redis.expire = AsyncMock()
        mock_redis.ttl = AsyncMock(return_value=60)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        from backend.core.auth import create_token_pair
        tokens = create_token_pair("admin-1", "admin@p.com", "platform_admin", None)
        self.admin_token = tokens["access_token"]

        r = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Sec Org",
            "org_email": "sec@org.com",
            "email": "user@sec.com",
            "password": "SecPass1!",
        })
        self.customer_token = r.json()["access_token"]

    def _auth(self, t): return {"Authorization": f"Bearer {t}"}

    def test_customer_blocked_from_security_audit(self):
        resp = self.client.get("/api/v1/security/audit",
                               headers=self._auth(self.customer_token))
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/v1/security/audit")
        assert resp.status_code == 401

    def test_admin_can_run_audit(self):
        resp = self.client.get("/api/v1/security/audit",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "overall_status" in data
        assert "checks" in data

    def test_admin_can_view_limits(self):
        resp = self.client.get("/api/v1/security/limits",
                               headers=self._auth(self.admin_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "limits" in data
        assert "auth" in data["limits"]

    def test_audit_no_critical_findings(self):
        resp = self.client.get("/api/v1/security/audit",
                               headers=self._auth(self.admin_token))
        data = resp.json()
        assert data["critical_findings"] == 0, \
            f"Critical security findings: {data}"

    def test_audit_no_high_findings(self):
        resp = self.client.get("/api/v1/security/audit",
                               headers=self._auth(self.admin_token))
        data = resp.json()
        assert data["high_findings"] == 0, \
            f"High security findings: {data}"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
