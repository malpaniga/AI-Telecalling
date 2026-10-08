from backend.providers.base import TTSProvider
class MockTTSProvider(TTSProvider):
    provider_name="mock"
    async def synthesize(self, text, **kwargs): return {"audio": text.encode(), "sample_rate": 16000}
    def get_capabilities(self): return {"streaming": True, "languages": ["en-IN"]}
