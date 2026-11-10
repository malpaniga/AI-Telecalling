import pytest
import mongomock_motor
from backend.models.campaign import Campaign
from backend.repositories.campaign_repo import CampaignRepository
from backend.services.campaign_service import CampaignService
from backend.api.v1.campaigns import CreateCampaignRequest, UpdateCampaignRequest, _campaign_response

@pytest.fixture
def anyio_backend():
    return "asyncio"

@pytest.fixture
def mock_db():
    client = mongomock_motor.AsyncMongoMockClient()
    return client["test_campaign_vm_config_db"]

def test_campaign_model_detect_voicemail_default():
    c = Campaign(
        organization_id="org_test",
        name="Test Campaign",
        agent_id="agent_1",
        agent_version=1,
        voice_profile_id="vp_1",
        voice_profile_version=1,
        calling_number_id="pn_1",
        calling_number="+918064262028",
    )
    assert c.detect_voicemail is True

    c2 = Campaign(
        organization_id="org_test",
        name="Test Campaign",
        agent_id="agent_1",
        agent_version=1,
        voice_profile_id="vp_1",
        voice_profile_version=1,
        calling_number_id="pn_1",
        calling_number="+918064262028",
        detect_voicemail=False,
    )
    assert c2.detect_voicemail is False

@pytest.mark.anyio
async def test_campaign_repo_and_service_persists_detect_voicemail(mock_db):
    camp_repo = CampaignRepository(mock_db)
    c1 = await camp_repo.create(
        organization_id="org_1",
        name="Default VM Campaign",
        agent_id="ag_1",
        agent_version=1,
        voice_profile_id="vp_1",
        voice_profile_version=1,
        calling_number_id="pn_1",
        calling_number="+918064262028",
    )
    assert c1.detect_voicemail is True

    c2 = await camp_repo.create(
        organization_id="org_1",
        name="Disabled VM Campaign",
        agent_id="ag_1",
        agent_version=1,
        voice_profile_id="vp_1",
        voice_profile_version=1,
        calling_number_id="pn_1",
        calling_number="+918064262028",
        detect_voicemail=False,
    )
    assert c2.detect_voicemail is False

    svc = CampaignService(mock_db)
    c3 = await svc.create_campaign(
        organization_id="org_1",
        name="Service VM Campaign",
        agent_id="ag_1",
        agent_version=1,
        voice_profile_id="vp_1",
        voice_profile_version=1,
        calling_number_id="pn_1",
        calling_number="+918064262028",
        detect_voicemail=False,
    )
    assert c3.detect_voicemail is False

def test_api_schema_and_response_serialization():
    req_default = CreateCampaignRequest(
        name="Req Default",
        agent_id="ag_1",
        agent_version=1,
        voice_profile_id="vp_1",
        voice_profile_version=1,
        calling_number_id="pn_1",
        calling_number="+918064262028",
    )
    assert req_default.detect_voicemail is True

    req_custom = CreateCampaignRequest(
        name="Req Custom",
        agent_id="ag_1",
        agent_version=1,
        voice_profile_id="vp_1",
        voice_profile_version=1,
        calling_number_id="pn_1",
        calling_number="+918064262028",
        detect_voicemail=False,
    )
    assert req_custom.detect_voicemail is False

    upd = UpdateCampaignRequest(detect_voicemail=False)
    assert upd.detect_voicemail is False

    c = Campaign(
        organization_id="org_test",
        name="Test Campaign",
        agent_id="agent_1",
        agent_version=1,
        voice_profile_id="vp_1",
        voice_profile_version=1,
        calling_number_id="pn_1",
        calling_number="+918064262028",
        detect_voicemail=False,
    )
    resp = _campaign_response(c)
    assert resp["detect_voicemail"] is False
