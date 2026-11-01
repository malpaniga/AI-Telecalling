"""Unit & Integration tests for Call Recording and Call Duration.

Verifies:
1. CallAudioRecorder multi-track PCM recording, timeline synchronization, and WAV export.
2. CallService and CallRepository recording_url & duration_s persistence.
3. GET /api/v1/calls/{call_id}/recording playback streaming and download attachment headers.
4. Token-based and Bearer authentication for audio streaming in browser tags.
"""

import asyncio
import mongomock_motor
import os
import wave
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import ASGITransport, AsyncClient

from backend.telephony.recording import (
    CallAudioRecorder,
    get_recording_path,
    get_recordings_dir,
)
from backend.models.call import Call
from backend.repositories.call_repo import CallRepository
from backend.services.call_service import CallService
from backend.core.auth import create_access_token


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestCallAudioRecorder:
    def test_recorder_timeline_and_wav_generation(self, tmp_path):
        with patch("backend.telephony.recording.RECORDINGS_DIR", tmp_path):
            call_id = "test-call-audio-123"
            recorder = CallAudioRecorder(call_id=call_id, sample_rate=16000)
            recorder.start()

            # 16000 Hz, 16-bit PCM: 32000 bytes/sec
            # Simulate 0.5s of caller audio (16000 bytes)
            caller_pcm = b"\x01\x00" * 8000
            recorder.record_caller_pcm(caller_pcm, sample_rate=16000)

            # Simulate 0.5s of agent audio
            agent_pcm = b"\x02\x00" * 8000
            recorder.record_agent_pcm(agent_pcm, sample_rate=16000)

            url = recorder.save_wav()
            assert url == f"/api/v1/calls/{call_id}/recording"

            # Verify file on disk
            wav_path = tmp_path / f"{call_id}.wav"
            assert wav_path.exists()
            assert wav_path.stat().st_size > 44

            with wave.open(str(wav_path), "rb") as wf:
                assert wf.getnchannels() == 1  # Mono mixed
                assert wf.getsampwidth() == 2  # 16-bit
                assert wf.getframerate() == 16000  # 16 kHz
                frames = wf.readframes(wf.getnframes())
                assert len(frames) >= 16000

    def test_recorder_too_short_skipped(self, tmp_path):
        with patch("backend.telephony.recording.RECORDINGS_DIR", tmp_path):
            call_id = "tiny-call"
            recorder = CallAudioRecorder(call_id=call_id, sample_rate=16000)
            recorder.start()
            # Feed 10 bytes (negligible/empty)
            recorder.record_caller_pcm(b"\x00" * 10)
            url = recorder.save_wav()
            assert url is None


class TestCallRecordingPersistenceAndService:
    def setup_method(self):
        self.client = mongomock_motor.AsyncMongoMockClient()
        self.db = self.client["test_call_recording"]
        self.repo = CallRepository(self.db)
        self.svc = CallService(self.db, redis=None)

    def test_finalize_call_persists_recording_and_duration(self):
        async def _test():
            call = await self.repo.create(
                organization_id="org-rec-test",
                to_number="+919876543210",
                from_number="+918000000000",
            )

            res = await self.svc.finalize_call(
                call_id=call.id,
                organization_id="org-rec-test",
                status="completed",
                recording_url=f"/api/v1/calls/{call.id}/recording",
            )

            assert res["status"] == "completed"
            updated = await self.repo.find_by_id(call.id)
            assert updated is not None
            assert updated.recording_url == f"/api/v1/calls/{call.id}/recording"
            assert updated.duration_s is not None
        run(_test())


class TestCallRecordingAPI:
    def setup_method(self):
        self.client = mongomock_motor.AsyncMongoMockClient()
        self.db = self.client["test_call_recording_api"]
        self.repo = CallRepository(self.db)

    def test_get_recording_stream_and_download(self, tmp_path):
        async def _test():
            from backend.main import app

            call_id = "call-api-rec-456"
            org_id = "org-rec-api"

            # Create dummy WAV in tmp_path
            wav_file = tmp_path / f"{call_id}.wav"
            with wave.open(str(wav_file), "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(b"\x00\x00" * 8000)

            # Seed call in DB
            await self.repo.create(
                call_id=call_id,
                organization_id=org_id,
                to_number="+919999999999",
                from_number="+918888888888",
            )
            await self.repo.set_recording_url(call_id, f"/api/v1/calls/{call_id}/recording")

            token = create_access_token(
                user_id="user-rec-1",
                email="user@rec.test",
                role="org_admin",
                org_id=org_id,
            )

            with patch("backend.telephony.recording.RECORDINGS_DIR", tmp_path), \
                 patch("backend.api.v1.calls.get_db", return_value=self.db):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    # 1. Inline playback (Bearer header)
                    res = await ac.get(
                        f"/api/v1/calls/{call_id}/recording",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    assert res.status_code == 200
                    assert res.headers["content-type"] == "audio/wav"
                    assert "Accept-Ranges" in res.headers

                    # 2. Direct download (Content-Disposition: attachment)
                    res_dl = await ac.get(
                        f"/api/v1/calls/{call_id}/recording?download=true",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    assert res_dl.status_code == 200
                    assert "attachment" in res_dl.headers.get("content-disposition", "")
                    assert f"call_{call_id}.wav" in res_dl.headers.get("content-disposition", "")

                    # 3. Audio player token in query param (for standard <audio src="..."> HTML tag)
                    res_tag = await ac.get(
                        f"/api/v1/calls/{call_id}/recording?token={token}",
                    )
                    assert res_tag.status_code == 200
                    assert res_tag.headers["content-type"] == "audio/wav"

                    # 4. Non-existent call -> 404
                    res_nf = await ac.get(
                        "/api/v1/calls/nonexistent-call/recording",
                        headers={"Authorization": f"Bearer {token}"},
                    )
                    assert res_nf.status_code == 404

        run(_test())
