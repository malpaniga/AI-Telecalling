import uuid
from backend.providers.base import TelephonyProvider
class MockTelephonyProvider(TelephonyProvider):
    provider_name = "mock"
    def __init__(self): self.calls = {}
    async def initiate_call(self, to, from_number, **kwargs):
        ident = f"mock-call-{uuid.uuid4()}"; call={"provider_resource_id": ident,"to":to,"from":from_number,"status":"queued"}; self.calls[ident]=call; return call
    async def hangup_call(self, provider_resource_id): self.calls[provider_resource_id]["status"]="completed"
    async def get_call_status(self, provider_resource_id): return self.calls[provider_resource_id]
    def get_capabilities(self): return {"outbound_calling": True, "streaming_audio": True}
