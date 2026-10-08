import asyncio
import pytest

def run(coro): return asyncio.run(coro)

@pytest.mark.skipif(__import__('importlib').util.find_spec('mongomock_motor') is None, reason='mongomock_motor not installed')
def test_customer_voice_profile_hides_provider_route_and_versions_are_immutable():
    import mongomock_motor
    from backend.services.voice_profile_service import VoiceProfileService
    db=mongomock_motor.AsyncMongoMockClient()['test']
    async def scenario():
        svc=VoiceProfileService(db)
        profile=await svc.create_profile('Marathi AI Voice','mr-IN')
        version=await svc.create_version(profile.id, routes={'tts': {'provider':'elevenlabs','provider_resource_id':'secret'}})
        customer=await svc.get_customer_profile(profile.id, 'org-a')
        assert customer['display_name']=='Marathi AI Voice'
        assert customer['active_version']==version.version
        assert 'routes' not in customer and 'provider' not in str(customer)
        with pytest.raises(ValueError): await svc.update_version_routes(version.id, {'tts': {}})
    run(scenario())

@pytest.mark.skipif(__import__('importlib').util.find_spec('mongomock_motor') is None, reason='mongomock_motor not installed')
def test_org_voice_profile_is_tenant_isolated():
    import mongomock_motor
    from backend.services.voice_profile_service import VoiceProfileService
    db=mongomock_motor.AsyncMongoMockClient()['test']
    async def scenario():
        svc=VoiceProfileService(db)
        profile=await svc.create_profile('Private Voice','en-IN', organization_id='org-a')
        await svc.create_version(profile.id, routes={})
        assert await svc.get_customer_profile(profile.id, 'org-b') is None
        assert (await svc.get_customer_profile(profile.id, 'org-a'))['id']==profile.id
    run(scenario())


def test_customer_view_has_no_internal_route_fields():
    from backend.services.voice_profile_service import _customer_view
    from backend.models.voice_profile import VoiceProfile
    view = _customer_view(VoiceProfile(_id='voice', display_name='Hindi AI Voice', language='hi-IN', active_version=1))
    assert set(view) == {'id', 'display_name', 'language', 'active_version', 'is_active'}


@pytest.mark.skipif(__import__('importlib').util.find_spec('mongomock_motor') is None, reason='mongomock_motor not installed')
def test_voice_profile_http_customer_redaction_and_admin_rbac():
    import mongomock_motor
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from backend.api.v1.auth import router as auth_router
    from backend.api.v1.voice_profiles import router as voice_router
    from backend.core import db as db_module, redis as redis_module
    from backend.core.auth import create_token_pair
    from backend.services.voice_profile_service import VoiceProfileService
    from unittest.mock import AsyncMock, MagicMock
    db = mongomock_motor.AsyncMongoMockClient()['test']; db_module._db = db
    redis = MagicMock(); redis.set = AsyncMock(); redis.exists = AsyncMock(return_value=0); redis_module._redis = redis
    async def seed():
        svc = VoiceProfileService(db); profile = await svc.create_profile('Marathi AI Voice', 'mr-IN')
        await svc.create_version(profile.id, {'tts': {'provider': 'elevenlabs', 'provider_resource_id': 'secret'}})
    run(seed())
    app = FastAPI(); app.include_router(auth_router, prefix='/api/v1'); app.include_router(voice_router, prefix='/api/v1')
    client = TestClient(app)
    signup = client.post('/api/v1/auth/signup', json={'org_name':'Voice Org','org_email':'voice@example.com','email':'owner@example.com','password':'Password1!'}).json()
    customer = {'Authorization': f"Bearer {signup['access_token']}"}
    result = client.get('/api/v1/voice-profiles', headers=customer)
    assert result.status_code == 200 and result.json()[0]['display_name'] == 'Marathi AI Voice'
    assert 'provider' not in str(result.json()) and 'secret' not in str(result.json())
    assert client.post('/api/v1/voice-profiles/admin', headers=customer, json={'display_name':'Nope','language':'en-IN'}).status_code == 403
    admin = create_token_pair('admin', 'admin@example.com', 'platform_admin', None)['access_token']
    assert client.post('/api/v1/voice-profiles/admin', headers={'Authorization':f'Bearer {admin}'}, json={'display_name':'Admin Voice','language':'en-IN'}).status_code == 200
