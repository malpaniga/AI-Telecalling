import asyncio
import pytest
from backend.providers.registry import build_demo_registry


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

def test_router_selects_healthy_capable_primary():
    from backend.providers.router import ProviderRouter
    route={'provider':'mock','provider_type':'tts','provider_resource_id':'voice','language':'en-IN'}
    resolved=ProviderRouter(build_demo_registry()).resolve(route)
    assert resolved.provider.provider_name=='mock' and resolved.provider_resource_id=='voice'

def test_router_falls_back_and_records_failover():
    from backend.providers.router import ProviderRouter
    events=[]
    route={'provider':'primary','provider_type':'tts','fallback_provider':'mock','fallback_resource_id':'fallback'}
    router=ProviderRouter(build_demo_registry(), health={('tts','primary'):False}, failover_log=events)
    resolved=router.resolve(route)
    assert resolved.provider.provider_name=='mock' and events[0]['to_provider']=='mock'

def test_router_rejects_missing_capability_or_language():
    from backend.providers.router import ProviderRouter
    router=ProviderRouter(build_demo_registry())
    with pytest.raises(ValueError): router.resolve({'provider':'mock','provider_type':'tts','language':'mr-IN'})

@pytest.mark.skipif(__import__('importlib').util.find_spec('mongomock_motor') is None, reason='mongomock_motor not installed')
def test_router_persists_failover_event():
    import asyncio, mongomock_motor
    from backend.providers.router import ProviderRouter
    async def scenario():
        db=mongomock_motor.AsyncMongoMockClient()['test']
        router=ProviderRouter(build_demo_registry(), health={('tts','primary'):False}, db=db)
        await router.resolve_and_record({'provider':'primary','provider_type':'tts','fallback_provider':'mock'})
        event=await db['provider_failover_events'].find_one({})
        assert event['from_provider']=='primary' and event['to_provider']=='mock'
    run(scenario())
