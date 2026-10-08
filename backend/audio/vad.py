"""Streaming voice-activity detection + endpointing.

Fed continuous 16-bit mono PCM, this detects when the caller starts speaking
(`speech_start`, used for barge-in) and when they finish (`utterance`).

The default backend is **Silero VAD** (a small neural model run via onnxruntime —
no torch). It is far better than webrtcvad at ignoring non-speech noise (TV,
traffic, fans), which is what makes turn-taking survive a real, noisy room. On top
of the frame classifier we add:

- an **energy floor** so very quiet sounds never count as speech,
- a **debounced onset** — barge-in only fires after a short burst of *sustained*
  speech, so a cough or click can't cut the agent off,
- **trailing-silence endpointing** tolerant of natural pauses, plus a
  **max-utterance flush** so steady noise can never freeze a turn forever.

webrtcvad remains available as a fallback (`VAD_BACKEND=webrtc`).
"""

import collections
import logging
import math
from collections.abc import Iterator

import numpy as np

from backend.config import settings

log = logging.getLogger("vad")

SPEECH_START = "speech_start"
UTTERANCE = "utterance"


# ---------------------------------------------------------------------------
# Frame classifiers
# ---------------------------------------------------------------------------
class SileroVAD:
    """Silero VAD v5 over onnxruntime. Returns P(speech) for a 512-sample window."""

    WINDOW = 512  # samples @ 16 kHz (~32 ms)
    CONTEXT = 64  # v5 prepends the previous 64 samples to each window

    def __init__(self, model_path: str, sample_rate: int = 16000):
        import onnxruntime as ort

        opts = ort.SessionOptions()
        opts.inter_op_num_threads = 1
        opts.intra_op_num_threads = 1
        self.session = ort.InferenceSession(
            model_path, sess_options=opts, providers=["CPUExecutionProvider"]
        )
        self._sr = np.array(sample_rate, dtype=np.int64)
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, self.CONTEXT), dtype=np.float32)

    def reset(self) -> None:
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, self.CONTEXT), dtype=np.float32)

    def prob(self, frame_i16: np.ndarray) -> float:
        window = (frame_i16.astype(np.float32) / 32768.0).reshape(1, -1)
        # Silero v5 expects [64-sample context] + [512-sample window].
        x = np.concatenate([self._context, window], axis=1)
        out, self._state = self.session.run(
            None, {"input": x, "state": self._state, "sr": self._sr}
        )
        self._context = x[:, -self.CONTEXT:]
        return float(out[0][0])


class _WebRTCVAD:
    """Fallback: webrtcvad on 20 ms frames -> boolean speech."""

    WINDOW_MS = 20

    def __init__(self, sample_rate: int, aggressiveness: int):
        import webrtcvad

        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = sample_rate
        self.window = int(sample_rate * self.WINDOW_MS / 1000)

    def reset(self) -> None:  # stateless
        pass

    def prob(self, frame_i16: np.ndarray) -> float:
        try:
            return 1.0 if self.vad.is_speech(frame_i16.tobytes(), self.sample_rate) else 0.0
        except Exception:  # noqa: BLE001
            return 0.0


def _rms_dbfs(frame_i16: np.ndarray) -> float:
    if frame_i16.size == 0:
        return -120.0
    rms = math.sqrt(float(np.mean(frame_i16.astype(np.float32) ** 2)))
    return 20.0 * math.log10(rms / 32768.0 + 1e-9)


# ---------------------------------------------------------------------------
# Endpointer state machine (shared by both backends)
# ---------------------------------------------------------------------------
class VADEndpointer:
    def __init__(self, sample_rate: int | None = None):
        self.sample_rate = sample_rate or settings.audio_sample_rate
        backend = settings.vad_backend.lower()

        if backend == "silero":
            import os
            model_path = settings.silero_model_path
            if not os.path.exists(model_path):
                log.warning(
                    "Silero VAD model not found at %s — falling back to webrtc backend",
                    model_path,
                )
                backend = "webrtc"
            else:
                self._clf = SileroVAD(model_path, self.sample_rate)
                self.window = SileroVAD.WINDOW
                self.speech_prob = settings.vad_speech_prob

        if backend != "silero":
            self._clf = _WebRTCVAD(self.sample_rate, settings.vad_aggressiveness)
            self.window = self._clf.window
            self.speech_prob = 0.5
        log.info("VAD backend=%s window=%d samples", backend, self.window)

        self.window_bytes = self.window * 2
        self.window_ms = self.window / self.sample_rate * 1000.0
        self.energy_floor_dbfs = settings.vad_energy_floor_dbfs

        def _n(ms: int) -> int:
            return max(1, round(ms / self.window_ms))

        self.confirm_windows = _n(settings.vad_speech_confirm_ms)
        self.silence_windows = _n(settings.vad_silence_ms)
        self.min_speech_windows = _n(settings.vad_min_speech_ms)
        self.max_windows = _n(settings.vad_max_utterance_ms)

        self._buf = bytearray()
        # Pre-roll keeps the audio just before onset so we don't clip the first word.
        self._preroll: collections.deque = collections.deque(maxlen=self.confirm_windows + 3)
        self._reset_state()

    def _reset_state(self) -> None:
        self._triggered = False
        self._voiced: list[np.ndarray] = []
        self._speech_run = 0
        self._trailing_silence = 0
        self._preroll.clear()
        self._clf.reset()

    def reset(self) -> None:
        self._reset_state()

    def _is_speech(self, frame: np.ndarray) -> bool:
        if _rms_dbfs(frame) < self.energy_floor_dbfs:
            return False
        return self._clf.prob(frame) >= self.speech_prob

    def process(self, pcm: bytes) -> Iterator[tuple[str, bytes | None]]:
        self._buf.extend(pcm)
        while len(self._buf) >= self.window_bytes:
            chunk = bytes(self._buf[: self.window_bytes])
            del self._buf[: self.window_bytes]
            frame = np.frombuffer(chunk, dtype=np.int16)
            yield from self._process_frame(frame)

    def _process_frame(self, frame: np.ndarray) -> Iterator[tuple[str, bytes | None]]:
        speech = self._is_speech(frame)

        if not self._triggered:
            self._preroll.append(frame)
            self._speech_run = self._speech_run + 1 if speech else 0
            if self._speech_run >= self.confirm_windows:
                # Confirmed sustained speech -> real turn start (barge-in).
                self._triggered = True
                self._trailing_silence = 0
                self._voiced = list(self._preroll)
                self._preroll.clear()
                yield (SPEECH_START, None)
        else:
            self._voiced.append(frame)
            self._trailing_silence = 0 if speech else self._trailing_silence + 1
            ended = self._trailing_silence >= self.silence_windows
            flushed = len(self._voiced) >= self.max_windows
            if ended or flushed:
                speech_windows = len(self._voiced) - self._trailing_silence
                audio = np.concatenate(self._voiced).tobytes()
                self._reset_state()
                if speech_windows >= self.min_speech_windows:
                    yield (UTTERANCE, audio)
                else:
                    log.debug("dropped short/low-speech clip (%d windows)", speech_windows)
