"""Tests for CallEventBroadcaster and live call transcript monitoring."""

import asyncio
from backend.telephony.broadcaster import CallEventBroadcaster


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_broadcaster_pubsub():
    async def _test():
        broadcaster = CallEventBroadcaster()
        call_id = "test-call-123"

        q1 = broadcaster.subscribe(call_id)
        q2 = broadcaster.subscribe(call_id)

        event1 = {"type": "agent", "text": "Hello, how can I help?"}
        await broadcaster.broadcast(call_id, event1)

        # Both listeners receive the event
        recv1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        recv2 = await asyncio.wait_for(q2.get(), timeout=1.0)
        assert recv1 == event1
        assert recv2 == event1

        # History is retained for new subscribers
        history = broadcaster.get_history(call_id)
        assert len(history) == 1
        assert history[0]["text"] == "Hello, how can I help?"

        # Unsubscribe works cleanly
        broadcaster.unsubscribe(call_id, q1)
        broadcaster.unsubscribe(call_id, q2)
        assert call_id not in broadcaster._listeners

    run(_test())


def test_broadcaster_empty_and_cleanup():
    async def _test():
        broadcaster = CallEventBroadcaster()
        call_id = "test-call-456"

        # Broadcasting with no listeners doesn't fail and retains history
        await broadcaster.broadcast(call_id, {"type": "ready", "status": "connected"})
        assert len(broadcaster.get_history(call_id)) == 1

        broadcaster.cleanup(call_id)
        assert len(broadcaster.get_history(call_id)) == 0

    run(_test())

