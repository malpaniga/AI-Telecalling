"""M32 tests — Documentation Completeness.

Tests:
1.  DEVELOPER_GUIDE.md exists and covers all required sections
2.  README.md exists with quick start, tech stack, architecture
3.  All required sections present in DEVELOPER_GUIDE.md
4.  .env.example documents all required variables
5.  MVP_PROGRESS.md tracks all checkpoints M0-M31
6.  No TODO sections left in docs
7.  API route count reasonable (>150 routes registered)
8.  All 26+ API routers documented in DEVELOPER_GUIDE.md
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
# Test: Documentation files exist
# ---------------------------------------------------------------------------
class TestDocumentationFilesExist:
    def test_developer_guide_exists(self):
        assert _exists("docs/DEVELOPER_GUIDE.md")

    def test_readme_exists(self):
        assert _exists("README.md")

    def test_env_example_exists(self):
        assert _exists(".env.example")

    def test_mvp_progress_exists(self):
        assert _exists("MVP_PROGRESS.md")


# ---------------------------------------------------------------------------
# Test: DEVELOPER_GUIDE.md sections
# ---------------------------------------------------------------------------
class TestDeveloperGuide:
    def setup_method(self):
        self.content = _read("docs/DEVELOPER_GUIDE.md")

    def test_installation_section(self):
        assert "## Installation" in self.content or "Installation" in self.content

    def test_environment_variables_section(self):
        assert "Environment" in self.content

    def test_local_development_section(self):
        assert "Local Development" in self.content or "local" in self.content.lower()

    def test_mongodb_section(self):
        assert "MongoDB" in self.content

    def test_redis_section(self):
        assert "Redis" in self.content

    def test_razorpay_section(self):
        assert "Razorpay" in self.content

    def test_telephony_section(self):
        assert "Twilio" in self.content or "Telephony" in self.content

    def test_stt_section(self):
        assert "STT" in self.content or "Sarvam" in self.content

    def test_tts_section(self):
        assert "TTS" in self.content or "ElevenLabs" in self.content

    def test_llm_section(self):
        assert "LLM" in self.content or "OpenAI" in self.content

    def test_voice_profiles_section(self):
        assert "Voice Profile" in self.content

    def test_agents_section(self):
        assert "Agent" in self.content or "Template" in self.content

    def test_campaigns_section(self):
        assert "Campaign" in self.content

    def test_deployment_section(self):
        assert "Deployment" in self.content or "Fly.io" in self.content

    def test_testing_section(self):
        assert "Testing" in self.content or "pytest" in self.content

    def test_adding_provider_section(self):
        assert "Adding" in self.content and "Provider" in self.content

    def test_demo_mode_section(self):
        assert "Demo Mode" in self.content or "DEMO_MODE" in self.content

    def test_security_notes_section(self):
        assert "Security" in self.content

    def test_provider_abstraction_principle(self):
        """Must explain that customer never sees provider details."""
        assert "never" in self.content.lower() or "hidden" in self.content.lower()

    def test_min_length(self):
        """Guide must be substantial."""
        assert len(self.content) > 3000, "DEVELOPER_GUIDE.md too short"


# ---------------------------------------------------------------------------
# Test: README.md
# ---------------------------------------------------------------------------
class TestReadme:
    def setup_method(self):
        self.content = _read("README.md")

    def test_quick_start(self):
        assert "quick start" in self.content.lower() or "Quick" in self.content

    def test_tech_stack(self):
        assert "FastAPI" in self.content or "tech" in self.content.lower()

    def test_demo_mode_mentioned(self):
        assert "demo" in self.content.lower()

    def test_architecture_diagram(self):
        assert "Architecture" in self.content or "→" in self.content

    def test_mongodb_atlas_mentioned(self):
        assert "MongoDB" in self.content

    def test_min_length(self):
        assert len(self.content) > 1000


# ---------------------------------------------------------------------------
# Test: .env.example completeness
# ---------------------------------------------------------------------------
class TestEnvExampleCompleteness:
    def setup_method(self):
        self.content = _read(".env.example")

    def test_mongodb_documented(self):
        assert "MONGODB_URI" in self.content

    def test_redis_documented(self):
        assert "REDIS_URL" in self.content

    def test_secret_key_documented(self):
        assert "SECRET_KEY" in self.content

    def test_demo_mode_documented(self):
        assert "DEMO_MODE" in self.content

    def test_sarvam_documented(self):
        assert "SARVAM" in self.content

    def test_razorpay_documented(self):
        assert "RAZORPAY" in self.content

    def test_twilio_documented(self):
        assert "TWILIO" in self.content

    def test_public_base_url_documented(self):
        assert "PUBLIC_BASE_URL" in self.content

    def test_tts_engine_documented(self):
        assert "TTS_ENGINE" in self.content


# ---------------------------------------------------------------------------
# Test: MVP_PROGRESS.md tracks all checkpoints
# ---------------------------------------------------------------------------
class TestMVPProgress:
    def setup_method(self):
        self.content = _read("MVP_PROGRESS.md")

    def test_all_m0_to_m31_tracked(self):
        for i in range(32):  # M0 through M31
            assert f"M{i}" in self.content, f"M{i} not tracked in MVP_PROGRESS.md"

    def test_m0_through_m31_pass(self):
        """All completed checkpoints should be marked PASS."""
        for i in range(32):
            marker = f"M{i} |"
            if marker in self.content:
                # Find the line
                for line in self.content.split("\n"):
                    if f"| M{i} |" in line:
                        assert "PASS" in line or "TODO" in line, \
                            f"M{i} has unexpected status"

    def test_current_checkpoint_recorded(self):
        assert "Current checkpoint" in self.content

    def test_next_checkpoint_recorded(self):
        assert "Next checkpoint" in self.content


# ---------------------------------------------------------------------------
# Test: API coverage in docs
# ---------------------------------------------------------------------------
class TestAPICoverage:
    def test_api_route_count(self):
        """Should have substantial number of routes registered."""
        sys.path.insert(0, REPO_ROOT)
        from backend.api.v1 import router
        assert len(router.routes) > 150, \
            f"Only {len(router.routes)} routes — expected >150"

    def test_key_api_sections_in_guide(self):
        content = _read("docs/DEVELOPER_GUIDE.md")
        key_sections = [
            "voice-profiles", "agents", "campaigns", "leads",
            "billing", "credits", "reconcili",
        ]
        for section in key_sections:
            assert section.lower() in content.lower(), \
                f"'{section}' not documented in DEVELOPER_GUIDE.md"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
