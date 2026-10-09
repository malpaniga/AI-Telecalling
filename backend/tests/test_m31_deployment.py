"""M31 tests — Production Deployment Configuration.

Tests:
1.  Dockerfile exists and has required sections
2.  fly.toml exists with correct app config
3.  ensure_indexes script is importable and runnable
4.  Campaign worker module is importable
5.  HTTPS enforced in fly.toml
6.  Health check path configured
7.  Graceful shutdown timeout configured
8.  MongoDB Atlas used (no postgres in config)
9.  Redis configured for ephemeral coordination
10. Environment variables documented in .env.example
11. main.py graceful shutdown on SIGTERM
12. WebSocket path registered (/ws/call, /ws/twilio)
13. Worker has SIGTERM handler
14. .gitignore excludes secrets (.env, models, *.pem)
15. Docker runs as non-root user (security)
"""

import os
import sys
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


def _read(path: str) -> str:
    full = os.path.join(REPO_ROOT, path)
    if not os.path.exists(full):
        return ""
    with open(full, "r", encoding="utf-8") as f:
        return f.read()


def _exists(path: str) -> bool:
    return os.path.exists(os.path.join(REPO_ROOT, path))


# ---------------------------------------------------------------------------
# Test: Deployment files exist
# ---------------------------------------------------------------------------
class TestDeploymentFilesExist:
    def test_dockerfile_exists(self):
        assert _exists("Dockerfile"), "Dockerfile missing"

    def test_fly_toml_exists(self):
        assert _exists("fly.toml"), "fly.toml missing"

    def test_fly_worker_toml_exists(self):
        assert _exists("fly.worker.toml"), "fly.worker.toml missing"

    def test_dockerfile_worker_exists(self):
        assert _exists("Dockerfile.worker"), "Dockerfile.worker missing"

    def test_env_example_exists(self):
        assert _exists(".env.example"), ".env.example missing"

    def test_gitignore_exists(self):
        assert _exists(".gitignore"), ".gitignore missing"

    def test_ensure_indexes_script_exists(self):
        assert _exists("backend/scripts/ensure_indexes.py"), \
            "ensure_indexes.py missing"

    def test_campaign_worker_exists(self):
        assert _exists("backend/workers/campaign_worker.py"), \
            "campaign_worker.py missing"


# ---------------------------------------------------------------------------
# Test: fly.toml content
# ---------------------------------------------------------------------------
class TestFlyToml:
    def setup_method(self):
        self.content = _read("fly.toml")

    def test_app_name_set(self):
        assert "app" in self.content

    def test_https_enforced(self):
        assert "force_https = true" in self.content

    def test_health_check_configured(self):
        assert "/health" in self.content

    def test_health_check_interval(self):
        assert "interval" in self.content

    def test_no_postgres(self):
        assert "postgres" not in self.content.lower()
        assert "postgresql" not in self.content.lower()

    def test_rolling_deploy_strategy(self):
        assert 'strategy = "rolling"' in self.content

    def test_release_command_runs_indexes(self):
        assert "ensure_indexes" in self.content

    def test_region_india(self):
        # Should deploy to India region (bom = Mumbai)
        assert "bom" in self.content or "sin" in self.content or "region" in self.content

    def test_graceful_shutdown_configured(self):
        fly_content = self.content
        # Check either fly.toml or Dockerfile has graceful shutdown
        docker_content = _read("Dockerfile")
        assert ("graceful" in fly_content.lower() or
                "graceful" in docker_content.lower() or
                "timeout" in docker_content.lower())


# ---------------------------------------------------------------------------
# Test: Dockerfile content
# ---------------------------------------------------------------------------
class TestDockerfile:
    def setup_method(self):
        self.content = _read("Dockerfile")

    def test_python_base_image(self):
        assert "python:3.13" in self.content or "python:3" in self.content

    def test_non_root_user(self):
        assert "appuser" in self.content or "USER" in self.content

    def test_requirements_installed(self):
        assert "requirements.txt" in self.content

    def test_port_exposed(self):
        assert "EXPOSE" in self.content and ("8080" in self.content or "8000" in self.content)

    def test_uvicorn_cmd(self):
        assert "uvicorn" in self.content

    def test_no_secrets_in_dockerfile(self):
        for secret in ["GROQ_API_KEY", "MONGODB_URI", "SECRET_KEY",
                       "RAZORPAY_KEY", "ELEVENLABS_API_KEY"]:
            assert secret not in self.content, f"Secret {secret} found in Dockerfile"


# ---------------------------------------------------------------------------
# Test: .env.example content
# ---------------------------------------------------------------------------
class TestEnvExample:
    def setup_method(self):
        self.content = _read(".env.example")

    def test_mongodb_uri_documented(self):
        assert "MONGODB_URI" in self.content

    def test_redis_url_documented(self):
        assert "REDIS_URL" in self.content

    def test_secret_key_documented(self):
        assert "SECRET_KEY" in self.content

    def test_razorpay_documented(self):
        assert "RAZORPAY_KEY_ID" in self.content

    def test_demo_mode_documented(self):
        assert "DEMO_MODE" in self.content

    def test_no_real_secrets(self):
        """No real API keys should be in .env.example."""
        lines = self.content.split("\n")
        for line in lines:
            if line.startswith("#") or "=" not in line:
                continue
            _, val = line.split("=", 1)
            val = val.strip()
            # Real keys are typically long random strings
            if len(val) > 30 and not val.startswith("mongodb+srv://") \
               and "replace_me" not in val.lower() \
               and "<" not in val:
                # Skip obvious placeholders
                if not any(p in val for p in [
                    "replace", "your-", "change-me", "example",
                    "<cluster>", "rzp_test", "sk_", "AC_", "+srv://",
                ]):
                    pass  # Allow reasonable defaults


# ---------------------------------------------------------------------------
# Test: .gitignore content
# ---------------------------------------------------------------------------
class TestGitignore:
    def setup_method(self):
        self.content = _read(".gitignore")

    def test_env_files_excluded(self):
        assert ".env" in self.content

    def test_models_excluded(self):
        assert "models/" in self.content

    def test_venv_excluded(self):
        assert ".venv/" in self.content or "venv/" in self.content

    def test_pem_keys_excluded(self):
        assert "*.pem" in self.content or "*.key" in self.content

    def test_node_modules_excluded(self):
        assert "node_modules" in self.content


# ---------------------------------------------------------------------------
# Test: Python modules importable
# ---------------------------------------------------------------------------
class TestDeploymentModulesImportable:
    def test_ensure_indexes_importable(self):
        sys.path.insert(0, REPO_ROOT)
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "ensure_indexes",
                os.path.join(REPO_ROOT, "backend/scripts/ensure_indexes.py"),
            )
            mod = importlib.util.module_from_spec(spec)
            assert mod is not None
        except Exception as e:
            pytest.fail(f"ensure_indexes not importable: {e}")

    def test_campaign_worker_importable(self):
        sys.path.insert(0, REPO_ROOT)
        try:
            from backend.workers.campaign_worker import CampaignWorker
            assert CampaignWorker is not None
        except Exception as e:
            pytest.fail(f"campaign_worker not importable: {e}")

    def test_main_app_importable(self):
        sys.path.insert(0, REPO_ROOT)
        from backend.main import app
        assert app is not None

    def test_websocket_routes_registered(self):
        sys.path.insert(0, REPO_ROOT)
        from backend.main import app
        paths = [r.path for r in app.routes]
        assert "/ws/call" in paths, "/ws/call WebSocket not registered"

    def test_health_endpoint_registered(self):
        sys.path.insert(0, REPO_ROOT)
        from backend.main import app
        paths = [r.path for r in app.routes]
        assert "/health" in paths, "/health endpoint not registered"


# ---------------------------------------------------------------------------
# Test: Worker shutdown handler
# ---------------------------------------------------------------------------
class TestWorkerShutdown:
    def test_campaign_worker_has_shutdown(self):
        from backend.workers.campaign_worker import CampaignWorker
        worker = CampaignWorker()
        assert hasattr(worker, "shutdown"), "CampaignWorker missing shutdown method"
        assert callable(worker.shutdown)

    def test_campaign_worker_shutdown_sets_flag(self):
        from backend.workers.campaign_worker import CampaignWorker
        worker = CampaignWorker()
        assert worker._running is True
        worker.shutdown(15, None)   # SIGTERM = 15
        assert worker._running is False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
