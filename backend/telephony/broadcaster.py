"""In-memory real-time event broadcaster for live phone calls."""

import asyncio
import logging
from typing import Any

log = logging.getLogger("telephony.broadcaster")


class CallEventBroadcaster:
    """Pub/sub broadcaster delivering real-time call events (turns, status, disposition)
    from active phone calls (Vobiz/Twilio) to connected UI WebSocket clients."""

    def __init__(self) -> None:
        # call_id -> set of asyncio.Queue
        self._listeners: dict[str, set[asyncio.Queue]] = {}
        # call_id -> list of buffered recent events
        self._history: dict[str, list[dict[str, Any]]] = {}

    def subscribe(self, call_id: str) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self._listeners.setdefault(call_id, set()).add(q)
        return q

    def unsubscribe(self, call_id: str, q: asyncio.Queue) -> None:
        if call_id in self._listeners:
            self._listeners[call_id].discard(q)
            if not self._listeners[call_id]:
                del self._listeners[call_id]

    async def broadcast(self, call_id: str, event: dict[str, Any]) -> None:
        if not call_id:
            return
        # Store in recent history (keep up to 60 events per call)
        hist = self._history.setdefault(call_id, [])
        hist.append(event)
        if len(hist) > 60:
            hist.pop(0)

        # Deliver to any active listeners
        listeners = self._listeners.get(call_id)
        if listeners:
            for q in list(listeners):
                try:
                    q.put_nowait(event)
                except Exception:
                    pass

    def get_history(self, call_id: str) -> list[dict[str, Any]]:
        return list(self._history.get(call_id, []))

    def cleanup(self, call_id: str) -> None:
        self._history.pop(call_id, None)
        self._listeners.pop(call_id, None)


call_broadcaster = CallEventBroadcaster()
