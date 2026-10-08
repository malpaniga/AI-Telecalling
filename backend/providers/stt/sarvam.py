from backend.audio.stt import SarvamSTT
from backend.providers.base import STTProvider
class SarvamSTTProvider(STTProvider):
    provider_name="sarvam"
    def __init__(self): self.client=SarvamSTT()
    async def transcribe(self, audio, **kwargs): return await self.client.transcribe(audio, **kwargs)
    def get_capabilities(self): return {"languages": ["hi-IN", "mr-IN", "en-IN"], "streaming": False}
