from backend.audio.tts import SarvamEngine
from backend.providers.base import TTSProvider
class SarvamTTSProvider(TTSProvider):
    provider_name="sarvam"
    def __init__(self): self.engine=SarvamEngine()
    async def synthesize(self, text, **kwargs):
        audio, sample_rate=await self.engine.synthesize(text, kwargs.get("language")); return {"audio":audio,"sample_rate":sample_rate}
