"""Exotel REST adapter boundary; credentials stay in platform configuration."""
import httpx
from backend.config import settings
from backend.providers.base import TelephonyProvider
class ExotelProvider(TelephonyProvider):
    provider_name="exotel"
    def __init__(self, client=None): self.client=client or httpx.AsyncClient(auth=(settings.exotel_api_key, settings.exotel_api_token), timeout=20)
    @property
    def _base(self): return f"https://{settings.exotel_subdomain}/v1/Accounts/{settings.exotel_sid}"
    async def initiate_call(self, to, from_number, **kwargs):
        r=await self.client.post(f"{self._base}/Calls/connect.json", data={"From":from_number,"To":to,"Url":kwargs["url"]}); r.raise_for_status(); data=r.json(); return {"provider_resource_id": data.get("Call",{}).get("Sid"),"status":"queued"}
    async def hangup_call(self, provider_resource_id):
        r=await self.client.post(f"{self._base}/Calls/{provider_resource_id}.json", data={"Status":"completed"}); r.raise_for_status()
    async def get_call_status(self, provider_resource_id):
        r=await self.client.get(f"{self._base}/Calls/{provider_resource_id}.json"); r.raise_for_status(); call=r.json().get("Call",{}); return {"provider_resource_id":provider_resource_id,"status":call.get("Status")}
    def get_capabilities(self): return {"outbound_calling": True}
