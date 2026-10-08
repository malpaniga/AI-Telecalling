"""M8 provider contracts and registry tests."""
import asyncio


def run(coro):
    return asyncio.run(coro)


def test_registry_resolves_typed_mock_providers_without_provider_branches():
    from backend.providers.registry import ProviderRegistry
    from backend.providers.telephony.mock import MockTelephonyProvider
    from backend.providers.stt.mock import MockSTTProvider
    from backend.providers.tts.mock import MockTTSProvider
    from backend.providers.llm.mock import MockLLMProvider
    from backend.providers.phone_number.mock import MockPhoneNumberProvider

    registry = ProviderRegistry()
    registry.register("telephony", MockTelephonyProvider())
    registry.register("stt", MockSTTProvider())
    registry.register("tts", MockTTSProvider())
    registry.register("llm", MockLLMProvider())
    registry.register("phone_number", MockPhoneNumberProvider())

    assert registry.get("telephony", "mock").provider_name == "mock"
    assert registry.get("stt", "mock").provider_name == "mock"
    assert registry.get("tts", "mock").provider_name == "mock"
    assert registry.get("llm", "mock").provider_name == "mock"
    assert registry.get("phone_number", "mock").provider_name == "mock"


def test_registry_rejects_unknown_provider_and_duplicate_registration():
    from backend.providers.registry import ProviderRegistry
    from backend.providers.telephony.mock import MockTelephonyProvider

    registry = ProviderRegistry()
    registry.register("telephony", MockTelephonyProvider())
    try:
        registry.register("telephony", MockTelephonyProvider())
        assert False, "duplicate registration must fail"
    except ValueError:
        pass
    try:
        registry.get("telephony", "twilio")
        assert False, "unknown provider must fail"
    except LookupError:
        pass


def test_mock_providers_implement_offline_calling_media_and_llm_flow():
    from backend.providers.telephony.mock import MockTelephonyProvider
    from backend.providers.stt.mock import MockSTTProvider
    from backend.providers.tts.mock import MockTTSProvider
    from backend.providers.llm.mock import MockLLMProvider
    from backend.providers.phone_number.mock import MockPhoneNumberProvider

    async def scenario():
        telephony = MockTelephonyProvider()
        call = await telephony.initiate_call("+919000000001", "+919000000002")
        assert call["status"] == "queued"
        assert (await telephony.get_call_status(call["provider_resource_id"]))["status"] == "queued"
        assert await MockSTTProvider(transcript="hello").transcribe(b"audio") == "hello"
        audio = await MockTTSProvider().synthesize("hello")
        assert audio["audio"]
        assert await MockLLMProvider(response="welcome").generate([{"role": "user", "content": "hi"}]) == "welcome"
        number = await MockPhoneNumberProvider().provision_number("IN")
        assert number["provider_resource_id"]
    run(scenario())


def test_demo_registry_registers_all_runtime_provider_categories():
    from backend.providers.registry import build_demo_registry
    registry = build_demo_registry()
    for kind in ("telephony", "stt", "tts", "llm", "phone_number"):
        assert registry.get(kind, "mock").provider_name == "mock"


def test_live_http_adapters_normalize_provider_responses_without_network():
    from backend.providers.llm.openai_compatible import OpenAICompatibleLLMProvider
    from backend.providers.telephony.exotel import ExotelProvider
    from backend.providers.tts.elevenlabs import ElevenLabsTTSProvider

    class Response:
        def __init__(self, payload=None, content=b""):
            self.payload, self.content = payload or {}, content
        def raise_for_status(self): pass
        def json(self): return self.payload

    class Client:
        def __init__(self): self.calls = []
        async def post(self, path, **kwargs):
            self.calls.append(("post", path, kwargs))
            if "connect" in path: return Response({"Call": {"Sid": "exotel-call"}})
            if "text-to-speech" in path: return Response(content=b"pcm")
            return Response({"choices": [{"message": {"content": "hello"}}]})
        async def get(self, path, **kwargs):
            self.calls.append(("get", path, kwargs)); return Response({"Call": {"Status": "completed"}})

    async def scenario():
        exotel_client = Client()
        exotel = ExotelProvider(client=exotel_client)
        call = await exotel.initiate_call("+9190", "+9180", url="https://example.test/voice")
        assert call == {"provider_resource_id": "exotel-call", "status": "queued"}
        assert (await exotel.get_call_status("exotel-call"))["status"] == "completed"
        eleven = ElevenLabsTTSProvider(client=Client())
        assert (await eleven.synthesize("hi", provider_resource_id="voice"))["audio"] == b"pcm"
        llm = OpenAICompatibleLLMProvider(client=Client())
        assert await llm.generate([{"role": "user", "content": "hi"}]) == "hello"
    run(scenario())
