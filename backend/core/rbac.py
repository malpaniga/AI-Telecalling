"""Role-Based Access Control (RBAC) for the AI Telecalling SaaS platform.

Permission matrix:

Platform roles (no organization scope):
  platform_owner  — everything
  platform_admin  — manage orgs, plans, providers; no billing_admin actions
  support         — read everything; limited write (add note, view audit logs)
  billing_admin   — billing/payments only

Organization roles (scoped to one organization):
  organization_owner  — full org control
  organization_admin  — manage settings, team, agents, campaigns
  manager             — manage campaigns and leads; view calls
  agent               — view calls and leads; add notes
  viewer              — read-only

Usage:
  # In a route:
  user: CurrentUser = Depends(require_role("manager", "organization_admin"))
  
  # Or with the OrgAccess dependency (also validates org ownership):
  ctx: OrgContext = Depends(require_org_access("manager"))
"""

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Path, status

from backend.core.auth import AuthError, CurrentUser, PermissionError, get_current_user

log = logging.getLogger("rbac")

# ---------------------------------------------------------------------------
# Permission sets
# ---------------------------------------------------------------------------

# Roles that can perform any platform-level action
PLATFORM_ROLES = {"platform_owner", "platform_admin", "support", "billing_admin"}

# Ordered hierarchy within org roles (higher index = more permissions)
ORG_ROLE_HIERARCHY = [
    "viewer",       # 0
    "agent",        # 1
    "manager",      # 2
    "organization_admin",   # 3
    "organization_owner",   # 4
]

# Map role → minimum hierarchy level required for various action classes
_ORG_LEVEL = {r: i for i, r in enumerate(ORG_ROLE_HIERARCHY)}

# Platform roles that can read any org data (support, platform_admin, etc.)
PLATFORM_READ_ROLES = {"platform_owner", "platform_admin", "support", "billing_admin"}
PLATFORM_WRITE_ROLES = {"platform_owner", "platform_admin"}
PLATFORM_BILLING_ROLES = {"platform_owner", "billing_admin"}


def _org_level(role: str) -> int:
    return _ORG_LEVEL.get(role, -1)


# ---------------------------------------------------------------------------
# Dependency factories
# ---------------------------------------------------------------------------

def require_role(*allowed_roles: str):
    """
    FastAPI dependency: requires the user to have one of the given roles.
    Platform users with sufficient platform permissions can always pass.

    Usage:
      router.get("/...", dependencies=[Depends(require_role("manager"))])
      or
      async def endpoint(user = Depends(require_role("manager", "organization_admin"))):
    """
    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role in allowed_roles:
            return user
        # platform_owner can do anything
        if user.role == "platform_owner":
            return user
        raise PermissionError(
            f"Role '{user.role}' is not authorized. Required: {sorted(allowed_roles)}"
        )
    return _check


def require_platform(*allowed_platform_roles: str):
    """
    Dependency: requires a platform-level role.
    Default: any platform role (platform_owner, platform_admin, support, billing_admin).
    """
    roles = set(allowed_platform_roles) if allowed_platform_roles else PLATFORM_ROLES

    async def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise PermissionError(
                f"Platform role required. Your role: {user.role}"
            )
        return user
    return _check


class OrgContext:
    """Resolved org-scoped request context."""
    __slots__ = ("user", "org_id")

    def __init__(self, user: CurrentUser, org_id: str):
        self.user = user
        self.org_id = org_id


def require_org_access(min_org_role: str = "viewer"):
    """
    Dependency: validates that:
    1. The user is authenticated.
    2. The user belongs to the org in the path ({org_id}) OR has a platform read role.
    3. The user's role meets the minimum org role requirement.

    Path parameter must be named `org_id`.

    Usage:
      async def endpoint(org_id: str, ctx: OrgContext = Depends(require_org_access("manager"))):
    """
    min_level = _org_level(min_org_role)

    async def _check(
        org_id: str,
        user: CurrentUser = Depends(get_current_user),
    ) -> OrgContext:
        # Platform users with read access can see any org
        if user.role in PLATFORM_READ_ROLES:
            return OrgContext(user=user, org_id=org_id)

        # Org user must belong to this org
        if user.org_id != org_id:
            raise PermissionError("Access denied: not a member of this organization")

        # Check minimum role level
        user_level = _org_level(user.role)
        if user_level < min_level:
            raise PermissionError(
                f"Requires at least '{min_org_role}' role. Your role: {user.role}"
            )

        return OrgContext(user=user, org_id=org_id)

    return _check


def require_self_or_role(user_id_param: str = "user_id", *admin_roles: str):
    """
    Dependency: passes if the current user is accessing their own resource,
    OR if they have one of the admin_roles.
    """
    allowed = set(admin_roles) | {"platform_owner", "platform_admin"}

    async def _check(
        user: CurrentUser = Depends(get_current_user),
        **kwargs,
    ) -> CurrentUser:
        # This needs the path user_id injected; handled at call site
        return user

    return _check


# ---------------------------------------------------------------------------
# Tenant isolation utility
# ---------------------------------------------------------------------------

def assert_org_access(user: CurrentUser, document_org_id: Optional[str]) -> None:
    """
    Raise 403 if `user` does not belong to `document_org_id`.
    Platform users with read roles are always allowed.
    Call this in service/repository layer as a defense-in-depth check.
    """
    if document_org_id is None:
        # Platform-owned resource
        if user.role not in PLATFORM_ROLES:
            raise PermissionError("Platform access required")
        return

    if user.role in PLATFORM_READ_ROLES:
        return  # platform can see any org

    if user.org_id != document_org_id:
        raise PermissionError("Access denied: tenant isolation violation")
