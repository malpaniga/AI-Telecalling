from backend.providers.base import STTProvider
class MockSTTProvider(STTProvider):
    provider_name="mock"
    def __init__(self, transcript=""): self.transcript=transcript
    async def transcribe(self, audio, **kwargs): return self.transcript
    def get_capabilities(self): return {"streaming": True, "languages": ["en-IN"]}
