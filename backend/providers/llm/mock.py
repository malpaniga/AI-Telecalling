from backend.providers.base import LLMProvider
class MockLLMProvider(LLMProvider):
    provider_name="mock"
    def __init__(self, response=""): self.response=response
    async def generate(self, messages, **kwargs): return self.response
    def get_capabilities(self): return {"streaming": True}
