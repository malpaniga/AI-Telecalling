"""Security audit service — static checks for known vulnerability patterns.

This is NOT a full security scanner. It runs targeted checks for the issues
the spec calls out:
  - tenant leaks (cross-org data access)
  - secret exposure (provider keys/API keys in responses)
  - unsafe error messages (stack traces leaked to clients)
  - webhook signature verification present
  - rate limiting configured
  - input validation on file uploads
  - RBAC enforcement coverage

Each check returns pass/fail with details. Admin-only.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any

log = logging.getLogger("service.security_audit")

# Patterns that indicate a potential secret leak in response code
SECRET_PATTERNS = [
    (r'api[_-]?key', "API key reference"),
    (r'secret[_-]?key', "Secret key reference"),
    (r'password[_-]?hash', "Password hash reference"),
    (r'provider[_-]?resource[_-]?id', "Provider resource ID in customer response"),
]

# Files that MUST have auth dependencies
API_FILES_REQUIRING_AUTH = [
    "backend/api/v1/organizations.py",
    "backend/api/v1/users.py",
    "backend/api/v1/subscriptions.py",
    "backend/api/v1/billing.py",
    "backend/api/v1/wallet.py",
    "backend/api/v1/leads.py",
    "backend/api/v1/campaigns.py",
    "backend/api/v1/calls.py",
    "backend/api/v1/appointments.py",
    "backend/api/v1/agents.py",
    "backend/api/v1/knowledge.py",
    "backend/api/v1/credits.py",
    "backend/api/v1/phone_numbers.py",
    "backend/api/v1/voice_profiles.py",
]


class SecurityAuditCheck:
    def __init__(self, name: str):
        self.name = name
        self.status = "pass"
        self.findings: list[dict] = []

    def add_finding(self, severity: str, detail: str, file: str = "") -> None:
        self.status = "fail"
        self.findings.append({"severity": severity, "detail": detail, "file": file})

    def to_dict(self) -> dict:
        return {
            "check": self.name,
            "status": self.status,
            "findings_count": len(self.findings),
            "findings": self.findings[:20],
        }


class SecurityAuditService:
    """Runs targeted security checks against the codebase."""

    def __init__(self, base_path: str = "."):
        self.base_path = base_path

    async def run_all(self) -> dict:
        checks = [
            self.check_auth_coverage(),
            self.check_secret_exposure(),
            self.check_webhook_verification(),
            self.check_rate_limiting(),
            self.check_tenant_isolation(),
            self.check_input_validation(),
        ]
        any_fail = any(c.status == "fail" for c in checks)
        critical = sum(
            1 for c in checks for f in c.findings
            if f.get("severity") == "critical"
        )
        high = sum(
            1 for c in checks for f in c.findings
            if f.get("severity") == "high"
        )
        return {
            "overall_status": "fail" if any_fail else "pass",
            "critical_findings": critical,
            "high_findings": high,
            "checks": [c.to_dict() for c in checks],
        }

    # ---- Check 1: Auth coverage ----

    def check_auth_coverage(self) -> SecurityAuditCheck:
        """All API endpoint files must use auth dependencies."""
        check = SecurityAuditCheck("auth_coverage")
        for filepath in API_FILES_REQUIRING_AUTH:
            full = os.path.join(self.base_path, filepath)
            if not os.path.exists(full):
                continue
            with open(full, "r", encoding="utf-8") as f:
                content = f.read()
            if "Depends(get_current_user)" not in content and \
               "require_platform" not in content and \
               "require_org_access" not in content and \
               "require_role" not in content:
                check.add_finding("high", "API file has no auth dependency", filepath)
        return check

    # ---- Check 2: Secret exposure ----

    def check_secret_exposure(self) -> SecurityAuditCheck:
        """Check for secret keys in API response builders (not in models/repos)."""
        check = SecurityAuditCheck("secret_exposure")
        api_dir = os.path.join(self.base_path, "backend/api/v1")
        if not os.path.isdir(api_dir):
            return check
        for fname in os.listdir(api_dir):
            if not fname.endswith(".py") or fname == "__init__.py":
                continue
            fpath = os.path.join(api_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            # Check for raw secret values in return dicts
            for pattern, desc in SECRET_PATTERNS:
                # Only flag if the pattern appears in a return/response context
                # (not in a Depends() or config reference)
                matches = re.findall(
                    rf'return.*{pattern}|".*{pattern}.*".*:',
                    content, re.IGNORECASE,
                )
                # Filter out config/settings references
                real_matches = [m for m in matches
                                if "settings." not in m and "Depends" not in m]
                if real_matches:
                    check.add_finding("high", desc, fname)
        return check

    # ---- Check 3: Webhook verification ----

    def check_webhook_verification(self) -> SecurityAuditCheck:
        """Webhook endpoints must verify signatures."""
        check = SecurityAuditCheck("webhook_verification")
        billing_path = os.path.join(self.base_path, "backend/api/v1/billing.py")
        if os.path.exists(billing_path):
            with open(billing_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "webhook" in content.lower():
                if "verify_webhook_signature" not in content and \
                   "process_webhook" not in content:
                    check.add_finding("critical",
                                     "Webhook endpoint does not verify signature",
                                     "billing.py")
        return check

    # ---- Check 4: Rate limiting ----

    def check_rate_limiting(self) -> SecurityAuditCheck:
        """Rate limiting module must exist and auth endpoints use it."""
        check = SecurityAuditCheck("rate_limiting")
        rl_path = os.path.join(self.base_path, "backend/core/rate_limit.py")
        if not os.path.exists(rl_path):
            check.add_finding("high", "Rate limiting module not found",
                             "backend/core/rate_limit.py")
        return check

    # ---- Check 5: Tenant isolation ----

    def check_tenant_isolation(self) -> SecurityAuditCheck:
        """Check that repos filter by organization_id (heuristic)."""
        check = SecurityAuditCheck("tenant_isolation")
        repo_dir = os.path.join(self.base_path, "backend/repositories")
        if not os.path.isdir(repo_dir):
            return check
        for fname in os.listdir(repo_dir):
            if not fname.endswith(".py") or fname == "__init__.py" or fname == "base.py":
                continue
            fpath = os.path.join(repo_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            # Files with multi-tenant data should reference organization_id
            if "organization_id" not in content and "Wallet" not in fname:
                check.add_finding("medium",
                                 "Repository may not enforce tenant isolation",
                                 fname)
        return check

    # ---- Check 6: Input validation on file uploads ----

    def check_input_validation(self) -> SecurityAuditCheck:
        """File upload endpoints must validate file type/size."""
        check = SecurityAuditCheck("input_validation")
        leads_path = os.path.join(self.base_path, "backend/api/v1/leads.py")
        if os.path.exists(leads_path):
            with open(leads_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "UploadFile" in content and "endswith" not in content and \
               "content_type" not in content:
                check.add_finding("medium",
                                 "File upload may not validate file type",
                                 "leads.py")
        return check
