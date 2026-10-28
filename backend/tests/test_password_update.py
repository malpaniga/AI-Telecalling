"""Tests for password update endpoints:
1. Self change password: POST /api/v1/auth/change-password
2. Super Admin org password reset: POST /api/v1/admin/organizations/{org_id}/password
"""

import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from fastapi import HTTPException

from backend.api.v1.auth import change_password, ChangePasswordRequest
from backend.api.v1.admin import update_org_password, AdminUpdateOrgPasswordRequest
from backend.core.auth import CurrentUser
from backend.repositories.user_repo import hash_password, verify_password
from backend.models.user import User
from backend.models.organization import Organization


def run(coro):
    return asyncio.run(coro)


class MockRequest:
    client = MagicMock(host="127.0.0.1")


class TestChangePasswordEndpoint:
    def test_change_password_validation_length(self):
        """Passwords under 8 chars should raise ValueError."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            ChangePasswordRequest(
                current_password="oldpassword123",
                new_password="short",
            )

    def test_change_password_wrong_current(self):
        """Should raise 400 if current password is wrong."""
        mock_user = User(
            id="u-123",
            email="admin@nivcall.com",
            password_hash=hash_password("correct_old_pass"),
            role="platform_owner",
        )
        current_user = CurrentUser(
            user_id="u-123",
            email="admin@nivcall.com",
            role="platform_owner",
            org_id=None,
        )

        with patch("backend.api.v1.auth.get_db") as mock_db, \
             patch("backend.api.v1.auth.UserRepository") as mock_user_repo_cls, \
             patch("backend.api.v1.auth.AuditLogRepository") as mock_audit_cls:
            
            repo = MagicMock()
            repo.find_by_id = AsyncMock(return_value=mock_user)
            mock_user_repo_cls.return_value = repo

            req = MockRequest()
            body = ChangePasswordRequest(
                current_password="wrong_password",
                new_password="new_strong_password_123",
            )

            with pytest.raises(HTTPException) as exc_info:
                run(change_password(body, req, current_user))
            assert exc_info.value.status_code == 400
            assert "Incorrect current password" in exc_info.value.detail

    def test_change_password_same_as_old(self):
        """Should raise 400 if new password is identical to current password."""
        mock_user = User(
            id="u-123",
            email="admin@nivcall.com",
            password_hash=hash_password("same_password_123"),
            role="platform_owner",
        )
        current_user = CurrentUser(
            user_id="u-123",
            email="admin@nivcall.com",
            role="platform_owner",
            org_id=None,
        )

        with patch("backend.api.v1.auth.get_db") as mock_db, \
             patch("backend.api.v1.auth.UserRepository") as mock_user_repo_cls, \
             patch("backend.api.v1.auth.AuditLogRepository") as mock_audit_cls:
            
            repo = MagicMock()
            repo.find_by_id = AsyncMock(return_value=mock_user)
            mock_user_repo_cls.return_value = repo

            req = MockRequest()
            body = ChangePasswordRequest(
                current_password="same_password_123",
                new_password="same_password_123",
            )

            with pytest.raises(HTTPException) as exc_info:
                run(change_password(body, req, current_user))
            assert exc_info.value.status_code == 400
            assert "must be different" in exc_info.value.detail

    def test_change_password_success(self):
        """Should update password and audit log on success."""
        mock_user = User(
            id="u-123",
            email="admin@nivcall.com",
            password_hash=hash_password("old_password_123"),
            role="platform_owner",
        )
        current_user = CurrentUser(
            user_id="u-123",
            email="admin@nivcall.com",
            role="platform_owner",
            org_id=None,
        )

        with patch("backend.api.v1.auth.get_db") as mock_db, \
             patch("backend.api.v1.auth.UserRepository") as mock_user_repo_cls, \
             patch("backend.api.v1.auth.AuditLogRepository") as mock_audit_cls:
            
            repo = MagicMock()
            repo.find_by_id = AsyncMock(return_value=mock_user)
            repo.update_password = AsyncMock(return_value=True)
            mock_user_repo_cls.return_value = repo

            audit = MagicMock()
            audit.log = AsyncMock()
            mock_audit_cls.return_value = audit

            req = MockRequest()
            body = ChangePasswordRequest(
                current_password="old_password_123",
                new_password="brand_new_secure_password_999",
            )

            res = run(change_password(body, req, current_user))
            assert res["status"] == "success"
            repo.update_password.assert_awaited_once_with(
                "u-123", "brand_new_secure_password_999"
            )
            audit.log.assert_awaited_once()


class TestAdminOrgPasswordUpdateEndpoint:
    def test_admin_org_password_validation_length(self):
        """Passwords under 8 chars should raise ValueError."""
        with pytest.raises(ValueError, match="at least 8 characters"):
            AdminUpdateOrgPasswordRequest(new_password="short")

    def test_admin_org_password_org_not_found(self):
        """Should raise 404 if organization does not exist."""
        admin_user = CurrentUser(
            user_id="admin-1",
            email="admin@nivcall.com",
            role="platform_owner",
            org_id=None,
        )

        with patch("backend.api.v1.admin.get_db"), \
             patch("backend.repositories.organization_repo.OrganizationRepository.find_by_id", new_callable=AsyncMock) as mock_find_org:
            
            mock_find_org.return_value = None
            req = MockRequest()
            body = AdminUpdateOrgPasswordRequest(new_password="new_strong_pass_123")

            with pytest.raises(HTTPException) as exc_info:
                run(update_org_password("non-existent-org", body, req, admin_user))
            assert exc_info.value.status_code == 404
            assert "Organization not found" in exc_info.value.detail

    def test_admin_org_password_success_via_email_match(self):
        """Should update password of user matching org.email."""
        admin_user = CurrentUser(
            user_id="admin-1",
            email="admin@nivcall.com",
            role="platform_owner",
            org_id=None,
        )
        mock_org = Organization(
            id="org-789",
            name="Test Org",
            slug="test-org",
            email="owner@testorg.com",
        )
        mock_target_user = User(
            id="user-456",
            email="owner@testorg.com",
            organization_id="org-789",
            password_hash=hash_password("old_pass_123"),
            role="organization_owner",
        )

        with patch("backend.api.v1.admin.get_db"), \
             patch("backend.repositories.organization_repo.OrganizationRepository.find_by_id", new_callable=AsyncMock) as mock_find_org, \
             patch("backend.repositories.user_repo.UserRepository.find_by_email", new_callable=AsyncMock) as mock_find_user, \
             patch("backend.repositories.user_repo.UserRepository.update_password", new_callable=AsyncMock) as mock_update_pw, \
             patch("backend.repositories.audit_log_repo.AuditLogRepository.log", new_callable=AsyncMock) as mock_audit:
            
            mock_find_org.return_value = mock_org
            mock_find_user.return_value = mock_target_user
            mock_update_pw.return_value = True

            req = MockRequest()
            body = AdminUpdateOrgPasswordRequest(new_password="fresh_admin_assigned_pass_456")

            res = run(update_org_password("org-789", body, req, admin_user))
            assert res["status"] == "success"
            assert res["user_email"] == "owner@testorg.com"
            mock_update_pw.assert_awaited_once_with(
                "user-456", "fresh_admin_assigned_pass_456"
            )
            mock_audit.assert_awaited_once()

    def test_admin_org_password_fallback_to_org_users(self):
        """When email doesn't match directly, falls back to organization users search."""
        admin_user = CurrentUser(
            user_id="admin-1",
            email="admin@nivcall.com",
            role="platform_owner",
            org_id=None,
        )
        mock_org = Organization(
            id="org-789",
            name="Test Org",
            slug="test-org",
            email="company@testorg.com",
        )
        mock_owner_user = User(
            id="user-999",
            email="real_owner@testorg.com",
            organization_id="org-789",
            password_hash=hash_password("old_pass_123"),
            role="organization_owner",
        )

        with patch("backend.api.v1.admin.get_db"), \
             patch("backend.repositories.organization_repo.OrganizationRepository.find_by_id", new_callable=AsyncMock) as mock_find_org, \
             patch("backend.repositories.user_repo.UserRepository.find_by_email", new_callable=AsyncMock) as mock_find_user, \
             patch("backend.repositories.user_repo.UserRepository.find_by_org", new_callable=AsyncMock) as mock_find_by_org, \
             patch("backend.repositories.user_repo.UserRepository.update_password", new_callable=AsyncMock) as mock_update_pw, \
             patch("backend.repositories.audit_log_repo.AuditLogRepository.log", new_callable=AsyncMock) as mock_audit:
            
            mock_find_org.return_value = mock_org
            mock_find_user.return_value = None  # No user with company@testorg.com
            mock_find_by_org.return_value = [mock_owner_user]
            mock_update_pw.return_value = True

            req = MockRequest()
            body = AdminUpdateOrgPasswordRequest(new_password="fresh_admin_assigned_pass_456")

            res = run(update_org_password("org-789", body, req, admin_user))
            assert res["status"] == "success"
            assert res["user_email"] == "real_owner@testorg.com"
            mock_update_pw.assert_awaited_once_with(
                "user-999", "fresh_admin_assigned_pass_456"
            )
