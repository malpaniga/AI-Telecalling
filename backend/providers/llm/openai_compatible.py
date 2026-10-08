"""OpenAI-compatible adapter boundary; concrete transport is selected by route."""
import httpx
from backend.config import settings
from backend.providers.base import LLMProvider
class OpenAICompatibleLLMProvider(LLMProvider):
    provider_name="openai_compatible"
    def __init__(self, client=None, base_url=None, api_key=None): self.client=client or httpx.AsyncClient(base_url=(base_url or settings.openai_base_url).rstrip("/"), headers={"Authorization":f"Bearer {api_key or settings.openai_api_key}"}, timeout=30)
    async def generate(self, messages, **kwargs):
        r=await self.client.post("/chat/completions", json={"model":kwargs.get("model",settings.openai_model),"messages":messages,"temperature":kwargs.get("temperature",0.6)}); r.raise_for_status(); return r.json()["choices"][0]["message"]["content"]
