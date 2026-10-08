import httpx
from backend.config import settings
from backend.providers.base import TTSProvider
class ElevenLabsTTSProvider(TTSProvider):
    provider_name="elevenlabs"
    def __init__(self, client=None): self.client=client or httpx.AsyncClient(base_url="https://api.elevenlabs.io/v1", headers={"xi-api-key":settings.elevenlabs_api_key}, timeout=30)
    async def synthesize(self, text, **kwargs):
        voice_id=kwargs["provider_resource_id"]; r=await self.client.post(f"/text-to-speech/{voice_id}", json={"text":text,"model_id":kwargs.get("model","eleven_multilingual_v2"),"output_format":"pcm_16000"}); r.raise_for_status(); return {"audio":r.content,"sample_rate":16000}
