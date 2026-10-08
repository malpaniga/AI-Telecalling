"""Latency metrics service.

Records per-turn latency observations and provides aggregate stats per call.

Latency targets (from docs/EXECUTION_PLAN.md):
  Response latency (silence → first audio):  good <1200ms, great <800ms
  Barge-in stop (interrupt → agent silent):  good <300ms, great <150ms
  STT finalize after speech end:             good <250ms, great <150ms
  LLM time-to-first-token:                  good <400ms, great <250ms
  TTS time-to-first-audio-chunk:             good <250ms, great <150ms

Stored in Redis (ephemeral, fast) during active calls.
Persisted to call record on finalization.
"""

import logging
from typing import Optional

log = logging.getLogger("service.latency")

# Latency budget thresholds (ms)
LATENCY_TARGETS = {
    "response_good": 1200,
    "response_great": 800,
    "barge_in_good": 300,
    "barge_in_great": 150,
}

_LATENCY_KEY = "call_latency:{}"
_LATENCY_TTL = 4 * 3600  # 4 hours


class LatencyMetrics:
    """In-memory latency accumulator for a single call."""

    def __init__(self):
        self.turns: list[dict] = []
        self.barge_in_events: list[int] = []  # barge-in response times (ms)

    def record_turn(
        self,
        first_audio_ms: Optional[int],
        total_ms: int,
        turn_index: int = 0,
    ) -> None:
        self.turns.append({
            "turn": turn_index,
            "first_audio_ms": first_audio_ms,
            "total_ms": total_ms,
        })

    def record_barge_in(self, response_ms: int) -> None:
        self.barge_in_events.append(response_ms)

    def summary(self) -> dict:
        if not self.turns:
            return {
                "turn_count": 0,
                "avg_first_audio_ms": None,
                "avg_total_ms": None,
                "p50_ms": None,
                "p95_ms": None,
                "barge_in_count": len(self.barge_in_events),
                "avg_barge_in_ms": None,
                "grade": "no_data",
            }

        first_audio_vals = [t["first_audio_ms"] for t in self.turns if t["first_audio_ms"]]
        total_vals = [t["total_ms"] for t in self.turns]
        sorted_totals = sorted(total_vals)

        avg_fa = int(sum(first_audio_vals) / len(first_audio_vals)) if first_audio_vals else None
        avg_total = int(sum(total_vals) / len(total_vals))
        p50 = sorted_totals[len(sorted_totals) // 2]
        p95 = sorted_totals[int(len(sorted_totals) * 0.95)]

        avg_barge_in = None
        if self.barge_in_events:
            avg_barge_in = int(sum(self.barge_in_events) / len(self.barge_in_events))

        grade = _grade_latency(avg_fa or avg_total)

        return {
            "turn_count": len(self.turns),
            "avg_first_audio_ms": avg_fa,
            "avg_total_ms": avg_total,
            "p50_ms": p50,
            "p95_ms": p95,
            "barge_in_count": len(self.barge_in_events),
            "avg_barge_in_ms": avg_barge_in,
            "grade": grade,
        }


def _grade_latency(avg_ms: int) -> str:
    if avg_ms <= LATENCY_TARGETS["response_great"]:
        return "great"
    if avg_ms <= LATENCY_TARGETS["response_good"]:
        return "good"
    return "needs_improvement"


class LatencyService:
    """Redis-backed latency tracker for active calls."""

    def __init__(self, redis=None):
        self._redis = redis

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            from backend.core.redis import get_redis
            return get_redis()
        except Exception:  # noqa: BLE001
            return None

    async def record_turn(
        self,
        call_id: str,
        first_audio_ms: Optional[int],
        total_ms: int,
    ) -> None:
        r = self._get_redis()
        if not r:
            return
        import json
        key = _LATENCY_KEY.format(call_id)
        entry = json.dumps({"first_audio_ms": first_audio_ms, "total_ms": total_ms})
        await r.rpush(key, entry)
        await r.expire(key, _LATENCY_TTL)

    async def get_call_latency(self, call_id: str) -> dict:
        r = self._get_redis()
        if not r:
            return {"error": "redis_unavailable"}
        import json
        key = _LATENCY_KEY.format(call_id)
        raw_entries = await r.lrange(key, 0, -1)
        metrics = LatencyMetrics()
        for i, raw in enumerate(raw_entries or []):
            try:
                entry = json.loads(raw)
                metrics.record_turn(entry.get("first_audio_ms"), entry["total_ms"], i)
            except Exception:  # noqa: BLE001
                pass
        return metrics.summary()

    async def clear(self, call_id: str) -> None:
        r = self._get_redis()
        if r:
            await r.delete(_LATENCY_KEY.format(call_id))
