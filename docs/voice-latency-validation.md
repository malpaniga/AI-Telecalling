# Voice latency and interruption validation

## Changes in this pass

- Browser capture batches reduced from 4096 to 512 samples (256 ms to 32 ms at 16 kHz). This reduces input batching, not total provider latency.
- Removed browser energy gates that dropped quiet speech and trailing silence during playback. Browser echo cancellation and server VAD now receive a continuous stream.
- Interruption cancels speech producers and clears queued playback before waiting for responder cleanup. Pending browser audio work is invalidated on interruption.
- Greeting synthesis runs as a cancellable responder so transports can receive microphone audio immediately after session initialization.
- Pending filler synthesis no longer blocks a ready answer or survives cancellation.
- Sensitivity zero is preserved; sensitivity also changes speech confirmation duration for binary WebRTC VAD.
- Meaningful short answers, numeric replies, thanks, and goodbye are retained. Background extraction applies in conversation order, independently per call.
- Custom agents receive generic conversational guidance instead of forced solar-sales instructions.
- Agent Studio saves preserve configuration fields outside its editor and reset missing version settings consistently.
- Sarvam TTS only retries an entire sentence if no audio has been emitted, preventing partial-stream failures from repeating speech.

## Measure before claiming provider parity

Use the same language, voice, prompt, microphone, deployment region, and network for before/after calls. Collect at least 30 turns per configuration and report p50/p95, not only averages.

1. Measure caller speech end to audible agent response in a recording. Server `turn_end.first_audio_ms` starts when an utterance enters STT and ends at the first audio chunk handed to transport (including filler); it excludes VAD trailing silence, network delivery, and browser playback. Measure meaningful-answer latency separately so filler does not hide slow answers.
2. Measure caller interruption onset to audible agent silence. Test during greeting, first sentence, and queued later sentences.
3. Test quiet speech, speakerphone echo, fan noise, short acknowledgments, and explicit “stop”. Check false interruptions as well as missed ones.
4. Verify an interrupted answer does not resume or repeat, and the next response addresses the latest user question.
5. Save/reopen draft configurations with sensitivity 0, 70, and 100. Repeat in browser tests and real phone calls.

Existing project targets are response below 1200 ms (stretch 800 ms) and interruption below 300 ms (stretch 150 ms). These are acceptance targets, not measured results from this patch.

## Remaining limitations and next steps

- The current Sarvam STT adapter uploads a complete utterance after local VAD; it is not a realtime WebSocket STT implementation. Realtime STT is the next architectural candidate, requiring provider-event, reconnect, endpointing, and cancellation tests before replacement.
- Local VAD still waits for its configured trailing silence (default 500 ms). Tune against recorded language/noise samples; lowering it indiscriminately can cut off speakers.
- Browser capture still uses ScriptProcessor. An AudioWorklet migration can reduce main-thread scheduling sensitivity but needs browser/device validation.
- Speech-speed configuration is not yet wired through the backend voice pipeline.
- Background extraction can outlive call teardown, and farewell phrase heuristics can misinterpret phrases such as “take care of your account”. These require separate lifecycle/explicit-hangup fixes.
- Unit tests use controlled audio/providers; they do not certify live voice naturalness, echo rejection, or Sarvam-level latency.

Reference: [Sarvam production guide](https://docs.sarvam.ai/api/integration/pipecat-production-guide), covering interruption policy, streaming, turn management, and latency measurement. Its Pipecat-specific settings should not be copied directly into this custom pipeline.

## Changed files and regression checks

Runtime: `backend/call_session.py`, `backend/audio/vad.py`, `backend/agent/engine.py`, `backend/providers/tts/sarvam.py`.

Studio: `frontend/app/(dashboard)/agents/[id]/page.tsx`, `frontend/components/test-agent/TestAgentModal.tsx`.

Regression tests: `backend/tests/test_voice_runtime_regressions.py`, `backend/tests/test_conversation_natural_turns.py`, `backend/tests/test_sarvam_stream_recovery.py`, `frontend/tests/voice-playback.test.cjs`. The existing STT test in `backend/tests/test_test_agent.py` now supplies a WAV utterance instead of invalid short fake bytes.

Focused backend verification: 132 passing tests across the new regressions and existing calls, barge-in, agents, export/import, and knowledge integration suites. Frontend behavioral verification: 10 passing tests using the component functions with mocked Web Audio; this is not a real microphone/browser integration test. Python compilation and whitespace checks pass.

Frontend production build (`npm run build`) passes, including lint, type checking, and generation of 39 static pages.

Full backend run: 983 passed, 104 failed, 21 errors. Failures are outside the targeted voice/Studio suites, including legacy asyncio loop assumptions, credit-service async mock problems, and payment setup/dependency failures. A separate payment-suite reproduction reaches Razorpay's missing `pkg_resources` import. Full output: `.omx/voice-studio-final-pytest.log`. The repository-wide gate is not green; the targeted passing suite must not be presented as full-platform certification.

No dependencies added. Simplifications remove the duplicate browser energy gate and the domain-specific instructions applied to every custom agent. Existing billing changes were preserved.
