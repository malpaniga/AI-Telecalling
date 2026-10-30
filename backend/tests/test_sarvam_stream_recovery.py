"""A failed TTS stream must not replay speech the caller already heard."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.providers.tts.sarvam import SarvamTTSProvider


@pytest.mark.parametrize("partial", [False, True])
def test_stream_fallback_only_before_audio_is_emitted(partial):
    async def scenario():
        async def chunks():
            if partial:
                yield b"\x01\x00"
            raise RuntimeError("connection dropped")

        response = MagicMock()
        response.aiter_bytes = chunks
        context = AsyncMock()
        context.__aenter__.return_value = response
        client = MagicMock()
        client.stream.return_value = context
        provider = SarvamTTSProvider(api_key="test", _client=client)
        provider.synthesize = AsyncMock(return_value={"audio": b"fallback", "sample_rate": 16000})
        received = []
        if partial:
            with pytest.raises(RuntimeError, match="connection dropped"):
                async for result in provider.stream("Hello there"):
                    received.append(result["audio"])
            assert received == [b"\x01\x00"]
            provider.synthesize.assert_not_awaited()
        else:
            async for result in provider.stream("Hello there"):
                received.append(result["audio"])
            assert received == [b"fallback"]
            provider.synthesize.assert_awaited_once()

    asyncio.run(scenario())
