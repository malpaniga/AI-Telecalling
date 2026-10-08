"""Twilio adapter; the Media Streams transport remains in backend.telephony.twilio."""
from backend.config import settings
from backend.providers.base import TelephonyProvider
class TwilioProvider(TelephonyProvider):
    provider_name="twilio"
    def _client(self):
        from twilio.rest import Client
        return Client(settings.twilio_account_sid, settings.twilio_auth_token)
    async def initiate_call(self, to, from_number, **kwargs):
        import asyncio
        call = await asyncio.to_thread(self._client().calls.create, to=to, from_=from_number, url=kwargs["url"])
        return {"provider_resource_id": call.sid, "status": call.status}
    async def hangup_call(self, provider_resource_id):
        import asyncio
        await asyncio.to_thread(self._client().calls(provider_resource_id).update, status="completed")
    async def get_call_status(self, provider_resource_id):
        import asyncio
        call = await asyncio.to_thread(self._client().calls(provider_resource_id).fetch)
        return {"provider_resource_id": call.sid, "status": call.status}
    def get_capabilities(self): return {"outbound_calling": True, "streaming_audio": True}
