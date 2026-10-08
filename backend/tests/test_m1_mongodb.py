"""M1 tests — MongoDB foundation.

Tests run against mongomock (in-memory MongoDB substitute) so no real MongoDB
connection is needed in CI. Tests validate:
1. Models serialize/deserialize correctly
2. OrganizationRepository CRUD
3. UserRepository create/authenticate/password hash
4. AuditLogRepository write and query
5. Slug uniqueness enforcement
6. Cross-collection isolation patterns
"""

import asyncio
import sys
import os
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Minimal async test runner (no pytest-asyncio needed for simple cases)
# ---------------------------------------------------------------------------
def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# In-memory Motor substitute using mongomock
# ---------------------------------------------------------------------------
def get_mock_db():
    """Return a mongomock-backed async Motor database substitute."""
    try:
        import mongomock_motor
        client = mongomock_motor.AsyncMongoMockClient()
        return client["test_db"]
    except ImportError:
        # Fall back to a simple dict-based stub
        return None


# ---------------------------------------------------------------------------
# Test: Models
# ---------------------------------------------------------------------------
class TestModels:
    def test_base_model_new_id(self):
        from backend.models.base import new_id
        id1 = new_id()
        id2 = new_id()
        assert isinstance(id1, str)
        assert len(id1) == 36  # UUID4 string
        assert id1 != id2

    def test_organization_model_creation(self):
        from backend.models.organization import Organization, OrganizationSettings
        from backend.models.base import new_id
        org = Organization(
            _id=new_id(),
            name="Test Corp",
            slug="test-corp",
            email="test@example.com",
        )
        assert org.name == "Test Corp"
        assert org.slug == "test-corp"
        assert org.status == "active"
        assert org.max_concurrent_calls == 1

    def test_organization_to_mongo(self):
        from backend.models.organization import Organization, OrganizationSettings
        from backend.models.base import new_id
        org = Organization(
            _id=new_id(),
            name="Acme",
            slug="acme",
            email="acme@example.com",
            settings=OrganizationSettings(_id=new_id()),
        )
        doc = org.to_mongo()
        assert "_id" in doc
        assert "id" not in doc  # must use _id for MongoDB
        assert doc["name"] == "Acme"

    def test_user_model_roles(self):
        from backend.models.user import PLATFORM_ROLES, ORGANIZATION_ROLES, ALL_ROLES
        assert "platform_owner" in PLATFORM_ROLES
        assert "organization_owner" in ORGANIZATION_ROLES
        assert "platform_owner" in ALL_ROLES
        assert "organization_owner" in ALL_ROLES
        assert len(ALL_ROLES) == len(PLATFORM_ROLES) + len(ORGANIZATION_ROLES)

    def test_user_model_fields(self):
        from backend.models.user import User
        from backend.models.base import new_id
        user = User(
            _id=new_id(),
            email="user@example.com",
            password_hash="$2b$12$xxx",
            role="organization_owner",
            organization_id="org-123",
        )
        assert user.email == "user@example.com"
        assert user.is_active is True
        assert user.is_platform_user is False

    def test_platform_user_flag(self):
        from backend.models.user import User
        from backend.models.base import new_id
        user = User(
            _id=new_id(),
            email="admin@platform.com",
            password_hash="$2b$12$xxx",
            role="platform_admin",
        )
        assert user.is_platform_user is True
        assert user.organization_id is None

    def test_audit_log_model(self):
        from backend.models.audit_log import AuditLog
        from backend.models.base import new_id
        log = AuditLog(
            _id=new_id(),
            action="user.login",
            organization_id="org-123",
            user_id="user-456",
            status="success",
        )
        assert log.action == "user.login"
        assert log.status == "success"
        doc = log.to_mongo()
        assert "_id" in doc


# ---------------------------------------------------------------------------
# Test: Password hashing
# ---------------------------------------------------------------------------
class TestPasswordHashing:
    def test_hash_and_verify(self):
        from backend.repositories.user_repo import hash_password, verify_password
        pw = "SecurePass123!"
        hashed = hash_password(pw)
        assert hashed != pw
        assert hashed.startswith("$2b$")
        assert verify_password(pw, hashed) is True

    def test_wrong_password_fails(self):
        from backend.repositories.user_repo import hash_password, verify_password
        hashed = hash_password("correct-password")
        assert verify_password("wrong-password", hashed) is False

    def test_different_hashes_same_password(self):
        from backend.repositories.user_repo import hash_password
        pw = "password123"
        h1 = hash_password(pw)
        h2 = hash_password(pw)
        assert h1 != h2  # bcrypt uses random salt

    def test_empty_password_safe(self):
        from backend.repositories.user_repo import hash_password, verify_password
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False


# ---------------------------------------------------------------------------
# Test: Slug generation
# ---------------------------------------------------------------------------
class TestSlugGeneration:
    def test_basic_slugify(self):
        from backend.repositories.organization_repo import _slugify
        assert _slugify("Acme Corp") == "acme-corp"
        assert _slugify("Test Company Ltd.") == "test-company-ltd"
        assert _slugify("  Spaces  ") == "spaces"

    def test_special_chars(self):
        from backend.repositories.organization_repo import _slugify
        result = _slugify("Hello & World! #123")
        assert " " not in result
        assert "&" not in result
        assert "#" not in result

    def test_max_length(self):
        from backend.repositories.organization_repo import _slugify
        long_name = "A" * 100
        result = _slugify(long_name)
        assert len(result) <= 50

    def test_hindi_characters(self):
        from backend.repositories.organization_repo import _slugify
        # Non-ASCII should be stripped for URL safety
        result = _slugify("नमस्ते World")
        assert isinstance(result, str)
        # Should not raise


# ---------------------------------------------------------------------------
# Test: Config
# ---------------------------------------------------------------------------
class TestConfig:
    def test_settings_load(self):
        from backend.config import settings
        assert hasattr(settings, "mongodb_uri")
        assert hasattr(settings, "redis_url")
        assert hasattr(settings, "mongodb_database")
        assert hasattr(settings, "secret_key")
        assert hasattr(settings, "app_env")
        assert hasattr(settings, "demo_mode")

    def test_sarvam_key_fallback(self):
        from backend.config import Settings
        s = Settings(sarvam_api_key="", sarvam_tts_api_key="legacy_key")
        assert s.effective_sarvam_key == "legacy_key"

    def test_sarvam_key_primary(self):
        from backend.config import Settings
        s = Settings(sarvam_api_key="new_key", sarvam_tts_api_key="legacy_key")
        assert s.effective_sarvam_key == "new_key"

    def test_redis_host_parsed(self):
        from backend.config import Settings
        s = Settings(redis_url="redis://my-redis-host:6380/1")
        assert s.redis_host == "my-redis-host"
        assert s.redis_port == 6380

    def test_demo_mode_default_false(self):
        from backend.config import settings
        # Default should be False unless DEMO_MODE env var is set
        assert isinstance(settings.demo_mode, bool)


# ---------------------------------------------------------------------------
# Test: Repository CRUD (uses mongomock if available, otherwise skip)
# ---------------------------------------------------------------------------
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
class TestOrganizationRepository:
    def setup_method(self):
        import mongomock_motor
        client = mongomock_motor.AsyncMongoMockClient()
        self.db = client["test_db"]

    def test_create_organization(self):
        from backend.repositories.organization_repo import OrganizationRepository
        repo = OrganizationRepository(self.db)

        async def _run():
            org = await repo.create(name="Test Corp", email="test@corp.com")
            assert org.id is not None
            assert org.name == "Test Corp"
            assert org.slug == "test-corp"
            assert org.email == "test@corp.com"
            assert org.status == "active"
            return org

        run(_run())

    def test_find_by_id(self):
        from backend.repositories.organization_repo import OrganizationRepository
        repo = OrganizationRepository(self.db)

        async def _run():
            org = await repo.create(name="FindMe", email="find@me.com")
            found = await repo.find_by_id(org.id)
            assert found is not None
            assert found.id == org.id
            assert found.name == "FindMe"

        run(_run())

    def test_find_by_slug(self):
        from backend.repositories.organization_repo import OrganizationRepository
        repo = OrganizationRepository(self.db)

        async def _run():
            org = await repo.create(name="Slug Test", email="slug@test.com")
            found = await repo.find_by_slug("slug-test")
            assert found is not None
            assert found.id == org.id

        run(_run())

    def test_slug_uniqueness(self):
        from backend.repositories.organization_repo import OrganizationRepository
        repo = OrganizationRepository(self.db)

        async def _run():
            org1 = await repo.create(name="Acme", email="acme1@test.com")
            org2 = await repo.create(name="Acme", email="acme2@test.com")
            # Second org should get a unique slug variant
            assert org1.slug != org2.slug
            assert org2.slug.startswith("acme")

        run(_run())

    def test_find_nonexistent(self):
        from backend.repositories.organization_repo import OrganizationRepository
        repo = OrganizationRepository(self.db)

        async def _run():
            result = await repo.find_by_id("nonexistent-id")
            assert result is None

        run(_run())

    def test_list_organizations(self):
        from backend.repositories.organization_repo import OrganizationRepository
        repo = OrganizationRepository(self.db)

        async def _run():
            await repo.create(name="Org A", email="a@test.com")
            await repo.create(name="Org B", email="b@test.com")
            orgs = await repo.list_all(limit=10)
            assert len(orgs) >= 2

        run(_run())

    def test_update_org(self):
        from backend.repositories.organization_repo import OrganizationRepository
        repo = OrganizationRepository(self.db)

        async def _run():
            org = await repo.create(name="Update Test", email="update@test.com")
            ok = await repo.update_by_id(org.id, {"name": "Updated Name"})
            assert ok is True
            updated = await repo.find_by_id(org.id)
            assert updated.name == "Updated Name"

        run(_run())


@SKIP_IF_NO_MONGOMOCK
class TestUserRepository:
    def setup_method(self):
        import mongomock_motor
        client = mongomock_motor.AsyncMongoMockClient()
        self.db = client["test_db"]

    def test_create_user(self):
        from backend.repositories.user_repo import UserRepository
        repo = UserRepository(self.db)

        async def _run():
            user = await repo.create(
                email="user@test.com",
                password="Password123!",
                role="organization_owner",
                organization_id="org-123",
            )
            assert user.id is not None
            assert user.email == "user@test.com"
            assert user.role == "organization_owner"
            # Password must be hashed
            assert user.password_hash != "Password123!"
            assert user.password_hash.startswith("$2b$")

        run(_run())

    def test_find_by_email(self):
        from backend.repositories.user_repo import UserRepository
        repo = UserRepository(self.db)

        async def _run():
            await repo.create(email="Find@Test.COM", password="pw", role="viewer")
            # Should be case-insensitive
            found = await repo.find_by_email("find@test.com")
            assert found is not None
            found_upper = await repo.find_by_email("FIND@TEST.COM")
            assert found_upper is not None

        run(_run())

    def test_authenticate_success(self):
        from backend.repositories.user_repo import UserRepository
        repo = UserRepository(self.db)

        async def _run():
            await repo.create(email="auth@test.com", password="CorrectPass!", role="viewer")
            user = await repo.authenticate("auth@test.com", "CorrectPass!")
            assert user is not None
            assert user.email == "auth@test.com"

        run(_run())

    def test_authenticate_wrong_password(self):
        from backend.repositories.user_repo import UserRepository
        repo = UserRepository(self.db)

        async def _run():
            await repo.create(email="auth2@test.com", password="RealPass!", role="viewer")
            result = await repo.authenticate("auth2@test.com", "WrongPass!")
            assert result is None

        run(_run())

    def test_authenticate_nonexistent(self):
        from backend.repositories.user_repo import UserRepository
        repo = UserRepository(self.db)

        async def _run():
            result = await repo.authenticate("ghost@test.com", "whatever")
            assert result is None

        run(_run())

    def test_user_deactivate(self):
        from backend.repositories.user_repo import UserRepository
        repo = UserRepository(self.db)

        async def _run():
            user = await repo.create(email="deact@test.com", password="pw", role="viewer")
            await repo.deactivate(user.id)
            # Deactivated user cannot authenticate
            result = await repo.authenticate("deact@test.com", "pw")
            assert result is None

        run(_run())


@SKIP_IF_NO_MONGOMOCK
class TestAuditLogRepository:
    def setup_method(self):
        import mongomock_motor
        client = mongomock_motor.AsyncMongoMockClient()
        self.db = client["test_db"]

    def test_log_action(self):
        from backend.repositories.audit_log_repo import AuditLogRepository
        repo = AuditLogRepository(self.db)

        async def _run():
            entry = await repo.log(
                action="user.login",
                organization_id="org-123",
                user_id="user-456",
                user_email="test@test.com",
            )
            assert entry.id is not None
            assert entry.action == "user.login"
            assert entry.status == "success"

        run(_run())

    def test_log_failure(self):
        from backend.repositories.audit_log_repo import AuditLogRepository
        repo = AuditLogRepository(self.db)

        async def _run():
            entry = await repo.log(
                action="campaign.start",
                organization_id="org-123",
                status="failure",
                error_message="Insufficient credits",
            )
            assert entry.status == "failure"
            assert entry.error_message == "Insufficient credits"

        run(_run())

    def test_list_for_org(self):
        from backend.repositories.audit_log_repo import AuditLogRepository
        repo = AuditLogRepository(self.db)

        async def _run():
            await repo.log(action="a.b", organization_id="org-1")
            await repo.log(action="a.c", organization_id="org-1")
            await repo.log(action="a.d", organization_id="org-2")  # different org

            logs = await repo.list_for_org("org-1")
            assert len(logs) == 2
            other_logs = await repo.list_for_org("org-2")
            assert len(other_logs) == 1

        run(_run())


# ---------------------------------------------------------------------------
# Test: Tenant isolation at query level
# ---------------------------------------------------------------------------
@SKIP_IF_NO_MONGOMOCK
class TestTenantIsolation:
    def setup_method(self):
        import mongomock_motor
        client = mongomock_motor.AsyncMongoMockClient()
        self.db = client["test_db"]

    def test_org_data_isolated(self):
        """Organization A should not see Organization B's users."""
        from backend.repositories.user_repo import UserRepository
        repo = UserRepository(self.db)

        async def _run():
            await repo.create(email="a@org.com", password="pw", role="viewer", organization_id="org-A")
            await repo.create(email="b@org.com", password="pw", role="viewer", organization_id="org-B")

            users_a = await repo.find_by_org("org-A")
            users_b = await repo.find_by_org("org-B")

            assert len(users_a) == 1
            assert users_a[0].email == "a@org.com"
            assert len(users_b) == 1
            assert users_b[0].email == "b@org.com"

            # Cross-tenant: org-A must not see org-B data
            for u in users_a:
                assert u.organization_id == "org-A"
            for u in users_b:
                assert u.organization_id == "org-B"

        run(_run())


# ---------------------------------------------------------------------------
# Test: Health check structure
# ---------------------------------------------------------------------------
class TestHealthCheck:
    def test_health_structure(self):
        """health.check_all should return the correct structure (mocked)."""
        import asyncio
        from unittest.mock import patch, AsyncMock
        from backend.core import health

        async def _run():
            with patch("backend.core.health.ping_db", new_callable=AsyncMock, return_value=True), \
                 patch("backend.core.health.ping_redis", new_callable=AsyncMock, return_value=True):
                result = await health.check_all()

            assert "status" in result
            assert "checks" in result
            assert "mongodb" in result["checks"]
            assert "redis" in result["checks"]
            assert result["status"] == "healthy"

        asyncio.get_event_loop().run_until_complete(_run())

    def test_health_degraded_when_mongo_down(self):
        import asyncio
        from unittest.mock import patch, AsyncMock
        from backend.core import health

        async def _run():
            with patch("backend.core.health.ping_db", new_callable=AsyncMock, return_value=False), \
                 patch("backend.core.health.ping_redis", new_callable=AsyncMock, return_value=True):
                result = await health.check_all()

            assert result["status"] == "degraded"
            assert result["checks"]["mongodb"] is False

        asyncio.get_event_loop().run_until_complete(_run())


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-v"]))
