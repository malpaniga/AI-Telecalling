"""Call audio recording engine.

Captures caller audio (inbound PCM) and AI agent audio (outbound TTS PCM),
aligns them onto a unified conversation timeline, and mixes them into a standard
16 kHz 16-bit mono WAV file for browser playback and direct download.
"""

import logging
import os
import tempfile
import time
import wave
from pathlib import Path
from typing import Optional

try:
    import audioop
except ImportError:
    import audioop_lts as audioop  # type: ignore

log = logging.getLogger("telephony.recording")

# Standard recording directory and fallback paths
RECORDINGS_DIR = Path("data/recordings")


def get_candidate_dirs() -> list[Path]:
    """Return ordered list of directories to attempt reading/writing recordings."""
    dirs: list[Path] = [RECORDINGS_DIR]
    fallbacks = [
        Path("/tmp/recordings"),
        Path(tempfile.gettempdir()) / "telecalling_recordings",
    ]
    for fb in fallbacks:
        if fb not in dirs:
            dirs.append(fb)
    return dirs


def get_recordings_dir() -> Path:
    for candidate in get_candidate_dirs():
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            # Test write permission
            test_file = candidate / f".write_test_{os.getpid()}"
            test_file.touch()
            test_file.unlink()
            return candidate
        except (PermissionError, OSError):
            continue
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    return RECORDINGS_DIR


def get_recording_path(call_id: str) -> Optional[Path]:
    """Return Path to local recording if it exists on disk."""
    if not call_id:
        return None
    for d in get_candidate_dirs():
        for ext in (".wav", ".mp3", ".ogg"):
            p = d / f"{call_id}{ext}"
            if p.exists() and p.stat().st_size > 44:  # > WAV header size
                return p
    return None


class CallAudioRecorder:
    """Records full-duplex call audio onto a synchronized timeline."""

    def __init__(self, call_id: str, sample_rate: int = 16000):
        self.call_id = call_id
        self.sample_rate = sample_rate
        self.bytes_per_sample = 2  # 16-bit PCM
        self.bytes_per_second = sample_rate * self.bytes_per_sample  # 32000

        self.start_time: Optional[float] = None
        self.caller_track = bytearray()
        self.agent_track = bytearray()
        self.active = False

    def start(self) -> None:
        """Begin recording timeline."""
        self.start_time = time.monotonic()
        self.active = True
        try:
            get_recordings_dir()
        except Exception:
            pass

    def record_caller_pcm(self, pcm16: bytes, sample_rate: int = 16000) -> None:
        """Feed a chunk of caller PCM audio."""
        if not self.active or not pcm16 or self.start_time is None:
            return

        # Resample to target rate if needed
        if sample_rate != self.sample_rate:
            try:
                pcm16, _ = audioop.ratecv(pcm16, 2, 1, sample_rate, self.sample_rate, None)
            except Exception as e:
                log.debug("failed resampling caller audio: %s", e)

        now = time.monotonic()
        elapsed = max(0.0, now - self.start_time)
        target_byte_pos = int(elapsed * self.bytes_per_second)
        target_byte_pos = (target_byte_pos // 2) * 2  # 2-byte alignment

        curr_len = len(self.caller_track)
        if target_byte_pos > curr_len:
            # Pad silence up to current timestamp
            silence_bytes = min(target_byte_pos - curr_len, self.bytes_per_second * 60)
            self.caller_track.extend(b"\x00" * silence_bytes)

        self.caller_track.extend(pcm16)

    def record_agent_pcm(self, pcm16: bytes, sample_rate: int = 16000) -> None:
        """Feed a chunk of AI agent synthesized speech."""
        if not self.active or not pcm16 or self.start_time is None:
            return

        if sample_rate != self.sample_rate:
            try:
                pcm16, _ = audioop.ratecv(pcm16, 2, 1, sample_rate, self.sample_rate, None)
            except Exception as e:
                log.debug("failed resampling agent audio: %s", e)

        now = time.monotonic()
        elapsed = max(0.0, now - self.start_time)
        target_byte_pos = int(elapsed * self.bytes_per_second)
        target_byte_pos = (target_byte_pos // 2) * 2

        curr_len = len(self.agent_track)
        if target_byte_pos > curr_len:
            silence_bytes = min(target_byte_pos - curr_len, self.bytes_per_second * 60)
            self.agent_track.extend(b"\x00" * silence_bytes)

        self.agent_track.extend(pcm16)

    def save_wav(self) -> Optional[str]:
        """Mix timeline tracks into a 16 kHz 16-bit mono WAV file."""
        if not self.active or self.start_time is None:
            return None
        self.active = False

        caller_len = len(self.caller_track)
        agent_len = len(self.agent_track)
        max_len = max(caller_len, agent_len)

        # Nothing recorded
        if max_len < (self.sample_rate * 2 * 0.2):  # less than 200ms
            log.info("recording for call %s too short (%d bytes), skipping save", self.call_id, max_len)
            return None

        # Pad shorter track to match
        if caller_len < max_len:
            self.caller_track.extend(b"\x00" * (max_len - caller_len))
        if agent_len < max_len:
            self.agent_track.extend(b"\x00" * (max_len - agent_len))

        # Mix the two tracks
        try:
            mixed = audioop.add(bytes(self.caller_track), bytes(self.agent_track), 2)
        except Exception as e:
            log.warning("audioop.add mix failed: %s; falling back to non-empty track", e)
            mixed = bytes(self.caller_track) if caller_len > 0 else bytes(self.agent_track)

        # Attempt saving in candidate directories
        for target_dir in get_candidate_dirs():
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                file_path = target_dir / f"{self.call_id}.wav"
                with wave.open(str(file_path), "wb") as wf:
                    wf.setnchannels(1)  # Mono
                    wf.setsampwidth(self.bytes_per_sample)  # 16-bit
                    wf.setframerate(self.sample_rate)  # 16 kHz
                    wf.writeframes(mixed)

                duration_s = max_len / self.bytes_per_second
                log.info(
                    "saved call recording for %s -> %s (%.1fs, %d bytes)",
                    self.call_id,
                    file_path,
                    duration_s,
                    len(mixed),
                )
                return f"/api/v1/calls/{self.call_id}/recording"
            except (PermissionError, OSError) as pe:
                log.warning("could not write recording to %s: %s; trying next directory", target_dir, pe)
                continue
            except Exception as exc:
                log.error("failed saving WAV for call %s: %s", self.call_id, exc)
                return None

        log.error("all candidate recording directories failed for call %s", self.call_id)
        return None
