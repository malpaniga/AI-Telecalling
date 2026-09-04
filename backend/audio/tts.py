"""Text-to-speech behind a pluggable engine interface.

Sprint 1 ships the `PiperEngine` (CPU, self-contained, reliable) so we can get the
full mic->speaker loop working today. Sprint 4 adds an `OrpheusEngine` (local GPU,
higher quality) behind this same interface — swapping is a one-line config change
(`TTS_ENGINE=orpheus`) with no changes to the call loop.

Every engine returns raw 16-bit mono PCM plus its sample rate. `pcm_to_wav`
wraps that into a WAV container the browser can play directly.
"""

import asyncio
import base64
import io
import logging
import time
import wave
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from pathlib import Path

from backend.config import settings

log = logging.getLogger("tts")


def pcm_to_wav(pcm: bytes, sample_rate: int) -> bytes:
    """Wrap raw 16-bit mono PCM in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def _wav_to_pcm(wav_bytes: bytes) -> tuple[bytes, int]:
    """Extract 16-bit mono PCM + sample rate from a WAV container."""
    with wave.open(io.BytesIO(wav_bytes)) as wf:
        sr = wf.getframerate()
        channels = wf.getnchannels()
        pcm = wf.readframes(wf.getnframes())
    if channels == 2:  # downmix to mono if ever stereo
        import audioop

        pcm = audioop.tomono(pcm, 2, 0.5, 0.5)
    return pcm, sr


class TTSEngine(ABC):
    """A synthesis engine. `synthesize` returns (pcm_int16_bytes, sample_rate)."""

    sample_rate: int

    @abstractmethod
    async def synthesize(self, text: str, language: str | None = None) -> tuple[bytes, int]:
        ...

    async def synthesize_wav(self, text: str, language: str | None = None) -> bytes:
        pcm, sr = await self.synthesize(text, language)
        return pcm_to_wav(pcm, sr)

    async def synthesize_stream(
        self, text: str, language: str | None = None
    ) -> AsyncIterator[tuple[bytes, int]]:
        """Yield (pcm16_chunk, sample_rate) as audio is produced. Default: one
        chunk (full synthesis). Engines that support progressive audio override
        this to start speaking sooner."""
        pcm, sr = await self.synthesize(text, language)
        if pcm:
            yield pcm, sr


class PiperEngine(TTSEngine):
    def __init__(self, model_path: str | None = None, use_cuda: bool | None = None):
        from piper import PiperVoice

        path = Path(model_path or settings.piper_model_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Piper voice not found at {path}. Download a voice into models/piper/."
            )
        cuda = settings.piper_use_cuda if use_cuda is None else use_cuda
        self.voice = PiperVoice.load(str(path), use_cuda=cuda)
        self.sample_rate = self.voice.config.sample_rate
        log.info("PiperEngine loaded %s @ %d Hz (cuda=%s)", path.name, self.sample_rate, cuda)

    def _synth_blocking(self, text: str) -> bytes:
        chunks = bytearray()
        for chunk in self.voice.synthesize(text):
            chunks.extend(chunk.audio_int16_bytes)
        return bytes(chunks)

    async def synthesize(self, text: str, language: str | None = None) -> tuple[bytes, int]:
        # Piper voice is English-only; language is ignored.
        text = text.strip()
        if not text:
            return b"", self.sample_rate
        started = time.perf_counter()
        pcm = await asyncio.to_thread(self._synth_blocking, text)
        log.info("tts %r -> %d bytes (%.0f ms)", text[:40], len(pcm),
                 (time.perf_counter() - started) * 1000)
        return pcm, self.sample_rate


class SarvamEngine(TTSEngine):
    """Sarvam Bulbul — native Indian voices over the REST API.

    Handles code-mixed English/Hindi (Hinglish) and speaks with an authentic
    Indian voice. Each sentence is a short HTTPS call; the returned base64 WAV is
    decoded to PCM so the browser + Twilio transports use it unchanged.
    """

    _URL = "https://api.sarvam.ai/text-to-speech"

    def __init__(self):
        import httpx

        if not settings.sarvam_tts_api_key:
            raise RuntimeError("SARVAM_TTS_API_KEY is not set")
        self.model = settings.sarvam_model
        self.speaker = settings.sarvam_speaker
        self.language = settings.sarvam_language
        self.sample_rate = 22050
        self._client = httpx.AsyncClient(
            timeout=20.0,
            headers={"api-subscription-key": settings.sarvam_tts_api_key},
        )
        log.info(
            "SarvamEngine ready (model=%s speaker=%s lang=%s)",
            self.model, self.speaker, self.language,
        )

    async def synthesize(self, text: str, language: str | None = None) -> tuple[bytes, int]:
        text = text.strip()
        if not text:
            return b"", self.sample_rate
        started = time.perf_counter()
        resp = await self._client.post(
            self._URL,
            json={
                "text": text,
                "target_language_code": language or self.language,
                "speaker": self.speaker,
                "model": self.model,
                "speech_sample_rate": self.sample_rate,
            },
        )
        resp.raise_for_status()
        audios = resp.json().get("audios") or []
        if not audios:
            log.warning("sarvam returned no audio for %r", text[:40])
            return b"", self.sample_rate
        pcm, sr = _wav_to_pcm(base64.b64decode(audios[0]))
        self.sample_rate = sr
        log.info("tts(sarvam) %r -> %d bytes (%.0f ms)", text[:40], len(pcm),
                 (time.perf_counter() - started) * 1000)
        return pcm, sr

    async def synthesize_stream(
        self, text: str, language: str | None = None
    ) -> AsyncIterator[tuple[bytes, int]]:
        """Progressive synthesis via Sarvam's streaming endpoint (linear16 = raw
        headerless PCM16). First audio arrives in ~0.5 s instead of ~2.5 s."""
        text = text.strip()
        if not text:
            return
        sr = self.sample_rate
        body = {
            "text": text,
            "target_language_code": language or self.language,
            "speaker": self.speaker,
            "model": self.model,
            "speech_sample_rate": sr,
            "output_audio_codec": "linear16",
        }
        started = time.perf_counter()
        carry = b""  # keep 16-bit samples byte-aligned across chunks
        first = True
        async with self._client.stream(
            "POST", "https://api.sarvam.ai/text-to-speech/stream", json=body
        ) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_bytes():
                if not chunk:
                    continue
                data = carry + chunk
                if len(data) % 2:
                    carry, data = data[-1:], data[:-1]
                else:
                    carry = b""
                if not data:
                    continue
                if first:
                    log.info("tts(sarvam-stream) first audio %.0f ms",
                             (time.perf_counter() - started) * 1000)
                    first = False
                yield data, sr


class OrpheusEngine(TTSEngine):
    """Local GPU Orpheus (llama-cpp GGUF + SNAC decode). Planned upgrade."""

    def __init__(self, *_, **__):
        raise NotImplementedError(
            "OrpheusEngine is not wired yet. Use TTS_ENGINE=piper or sarvam."
        )

    async def synthesize(self, text: str, language: str | None = None) -> tuple[bytes, int]:  # pragma: no cover
        raise NotImplementedError


_engine: TTSEngine | None = None


def get_tts_engine() -> TTSEngine:
    """Process-wide singleton, chosen by settings.tts_engine."""
    global _engine
    if _engine is None:
        name = settings.tts_engine.lower()
        if name == "piper":
            _engine = PiperEngine()
        elif name == "sarvam":
            _engine = SarvamEngine()
        elif name == "orpheus":
            _engine = OrpheusEngine()
        else:
            raise ValueError(f"unknown TTS_ENGINE: {settings.tts_engine!r}")
    return _engine


async def _smoke_test() -> None:
    logging.basicConfig(level="INFO")
    engine = get_tts_engine()
    wav = await engine.synthesize_wav(
        "Hi there! Thanks for calling. Are you looking to buy or rent?"
    )
    out = Path("/tmp/tts_test.wav")
    out.write_bytes(wav)
    print(f"wrote {len(wav)} bytes to {out}")


if __name__ == "__main__":
    asyncio.run(_smoke_test())
