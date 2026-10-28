"""Credit reservation and settlement service.

This is the credit accounting layer for active calls.

Lifecycle:
  1. reserve(org_id, call_id, max_credits)
       → moves credits available → reserved in wallet (atomic)
       → writes Redis key for fast in-flight check
       → creates WalletTransaction(type="reserve")

  2a. On call end (billed):
       settle(org_id, call_id, actual_credits)
       → consumes actual_credits from reserved, returns remainder to available
       → creates WalletTransaction(type="consume")
       → removes Redis reservation key
       → updates CreditLot(s) via FIFO consume

  2b. On call fail / cancel (not billed):
       release(org_id, call_id)
       → returns all reserved credits back to available
       → creates WalletTransaction(type="release")
       → removes Redis reservation key

Properties enforced:
  - available + reserved never decreases below zero
  - Double-settle (same call_id twice) is idempotent — second call is a no-op
  - Insufficient credits → raises, call must not start
  - All operations create immutable WalletTransaction ledger entries
  - Redis holds temporary reservation state; MongoDB is source of truth

Redis keys:
  credit_reserve:{org_id}:{call_id}  →  reserved_credits (int, TTL 4h)
"""

import logging
import math
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.base import new_id, utcnow
from backend.repositories.wallet_repo import (
    CreditLotRepository,
    WalletRepository,
    WalletTransactionRepository,
)

log = logging.getLogger("service.credit")

_RESERVE_TTL = 4 * 3600          # 4-hour TTL on reservation keys
_RESERVE_PREFIX = "credit_reserve:"


def _reserve_key(org_id: str, call_id: str) -> str:
    return f"{_RESERVE_PREFIX}{org_id}:{call_id}"


class CreditService:
    def __init__(self, db: AsyncIOMotorDatabase, redis=None):
        self.db = db
        self._redis = redis   # injected; fetched lazily if None
        self.wallet_repo = WalletRepository(db)
        self.txn_repo = WalletTransactionRepository(db)
        self.lot_repo = CreditLotRepository(db)

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            from backend.core.redis import get_redis
            return get_redis()
        except Exception:  # noqa: BLE001
            return None

    # -----------------------------------------------------------------------
    # Reserve
    # -----------------------------------------------------------------------
    async def reserve(
        self,
        organization_id: str,
        call_id: str,
        max_credits: int,
    ) -> dict:
        """
        Reserve up to max_credits for an active call.
        Raises ValueError if insufficient credits are available.
        Returns {reserved_credits, new_available_balance}.
        """
        if max_credits <= 0:
            raise ValueError(f"max_credits must be positive; got {max_credits}")

        wallet = await self.wallet_repo.get_or_create(organization_id)

        # Check for an existing reservation (idempotency — call may retry)
        redis = self._get_redis()
        if redis:
            existing = await redis.get(_reserve_key(organization_id, call_id))
            if existing:
                log.info("reserve: already reserved call=%s credits=%s", call_id, existing)
                return {
                    "reserved_credits": int(existing),
                    "new_available_balance": wallet.available_credits,
                    "idempotent": True,
                }

        # Atomic: move available → reserved in MongoDB
        updated = await self.wallet_repo.atomic_reserve(wallet.id, max_credits)
        if updated is None:
            available = wallet.available_credits
            raise ValueError(
                f"Insufficient credits to start call. "
                f"Required: {max_credits}, Available: {available}"
            )

        new_available = updated["available_credits"]

        # Ledger entry
        await self.txn_repo.record(
            organization_id=organization_id,
            wallet_id=wallet.id,
            transaction_type="reserve",
            credits_delta=0,            # total doesn't change; just bucket shift
            available_delta=-max_credits,
            reserved_delta=max_credits,
            balance_after=new_available,
            description=f"Reserved for call {call_id[:8]}",
            call_id=call_id,
            idempotency_key=f"reserve:{call_id}",
        )

        # Redis fast-path marker
        if redis:
            await redis.set(
                _reserve_key(organization_id, call_id),
                str(max_credits),
                ex=_RESERVE_TTL,
            )

        log.info("reserve org=%s call=%s credits=%d available_after=%d",
                 organization_id, call_id, max_credits, new_available)

        return {
            "reserved_credits": max_credits,
            "new_available_balance": new_available,
        }

    # -----------------------------------------------------------------------
    # Release (call cancelled / failed before billing)
    # -----------------------------------------------------------------------
    async def release(
        self,
        organization_id: str,
        call_id: str,
    ) -> dict:
        """
        Return all reserved credits for call_id back to available.
        Idempotent: if no reservation exists, returns gracefully.
        """
        redis = self._get_redis()
        reserved_str = None
        if redis:
            reserved_str = await redis.get(_reserve_key(organization_id, call_id))

        # Check MongoDB for reservation via ledger
        if reserved_str is None:
            reserve_txns = await self.txn_repo.find_many({
                "call_id": call_id,
                "transaction_type": "reserve",
                "organization_id": organization_id,
            })
            if not reserve_txns:
                call_doc = await self.db.calls.find_one({"_id": call_id, "organization_id": organization_id})
                if call_doc and call_doc.get("credits_reserved"):
                    reserved_credits = call_doc["credits_reserved"]
                else:
                    log.info("release: no reservation found for call=%s (already released?)", call_id)
                    return {"released_credits": 0, "idempotent": True}
            else:
                # Check not already released/settled
                settled = await self.txn_repo.find_one({
                    "call_id": call_id,
                    "transaction_type": {"$in": ["release", "consume"]},
                    "organization_id": organization_id,
                })
                if settled:
                    log.info("release: call=%s already settled", call_id)
                    return {"released_credits": 0, "idempotent": True}
                reserved_credits = sum(abs(t.available_delta) for t in reserve_txns)
        else:
            reserved_credits = int(reserved_str)

        wallet = await self.wallet_repo.get_or_create(organization_id)
        updated = await self.wallet_repo.atomic_release(wallet.id, reserved_credits)
        if updated is None:
            log.warning("release: wallet update failed for call=%s — reservations may be stale", call_id)
            reserved_credits = wallet.reserved_credits
            updated = await self.wallet_repo.atomic_release(wallet.id, reserved_credits)
            if updated is None:
                return {"released_credits": 0, "error": "wallet_update_failed"}

        new_available = updated["available_credits"]

        await self.txn_repo.record(
            organization_id=organization_id,
            wallet_id=wallet.id,
            transaction_type="release",
            credits_delta=0,
            available_delta=reserved_credits,
            reserved_delta=-reserved_credits,
            balance_after=new_available,
            description=f"Released reservation for call {call_id[:8]}",
            call_id=call_id,
            idempotency_key=f"release:{call_id}",
        )

        if redis:
            await redis.delete(_reserve_key(organization_id, call_id))

        log.info("release org=%s call=%s credits=%d available_after=%d",
                 organization_id, call_id, reserved_credits, new_available)

        return {"released_credits": reserved_credits, "new_available_balance": new_available}

    # -----------------------------------------------------------------------
    # Settle (call completed — bill exact usage)
    # -----------------------------------------------------------------------
    async def settle(
        self,
        organization_id: str,
        call_id: str,
        actual_credits: int,
        idempotency_key: Optional[str] = None,
    ) -> dict:
        """
        Finalize billing for a completed call.
        actual_credits ≤ reserved_credits.
        Returns any over-reserved credits to available.
        Idempotent: same call_id can only be settled once.
        """
        if actual_credits < 0:
            raise ValueError("actual_credits cannot be negative")

        # Idempotency check
        idem_key = idempotency_key or f"settle:{call_id}"
        existing_settle = await self.txn_repo.find_one({
            "idempotency_key": idem_key,
            "organization_id": organization_id,
        })
        if existing_settle:
            log.info("settle: idempotent replay call=%s", call_id)
            return {"billed_credits": actual_credits, "idempotent": True}

        # Find reserved amount from reserve ledger entries
        reserve_txns = await self.txn_repo.find_many({
            "call_id": call_id,
            "transaction_type": "reserve",
            "organization_id": organization_id,
        })

        redis = self._get_redis()
        if not reserve_txns and redis:
            reserved_str = await redis.get(_reserve_key(organization_id, call_id))
            if reserved_str:
                reserved_credits = int(reserved_str)
            else:
                call_doc = await self.db.calls.find_one({"_id": call_id, "organization_id": organization_id})
                if call_doc and call_doc.get("credits_reserved"):
                    reserved_credits = call_doc["credits_reserved"]
                else:
                    log.warning("settle: no reservation found for call=%s", call_id)
                    reserved_credits = actual_credits
        elif reserve_txns:
            reserved_credits = sum(abs(t.available_delta) for t in reserve_txns)
        else:
            call_doc = await self.db.calls.find_one({"_id": call_id, "organization_id": organization_id})
            if call_doc and call_doc.get("credits_reserved"):
                reserved_credits = call_doc["credits_reserved"]
            else:
                log.warning("settle: no reservation found for call=%s — using actual", call_id)
                reserved_credits = actual_credits

        # Cap actual to reserved (safety)
        actual_credits = min(actual_credits, reserved_credits)
        refund_credits = reserved_credits - actual_credits

        wallet = await self.wallet_repo.get_or_create(organization_id)

        # Atomic: remove reserved_credits from reserved; return refund to available
        updated = await self.wallet_repo.atomic_consume(
            wallet.id, reserved_credits, actual_credits
        )
        if updated is None:
            # Should not happen with the fallback in atomic_consume, but guard anyway
            wallet_doc = await self.wallet_repo.find_by_id(wallet.id)
            new_available = wallet_doc.available_credits if wallet_doc else 0
        else:
            new_available = updated.get("available_credits", 0) if isinstance(updated, dict) else updated.available_credits

        # Consume from credit lots (FIFO)
        if actual_credits > 0:
            await self.lot_repo.consume_from_lots(organization_id, actual_credits)

        # Ledger entry for actual consumption or full refund
        if actual_credits > 0:
            await self.txn_repo.record(
                organization_id=organization_id,
                wallet_id=wallet.id,
                transaction_type="consume",
                credits_delta=-actual_credits,
                available_delta=refund_credits,
                reserved_delta=-reserved_credits,
                balance_after=new_available,
                description=f"Call billed: {actual_credits} min for call {call_id[:8]}",
                call_id=call_id,
                idempotency_key=idem_key,
            )
        elif reserved_credits > 0:
            await self.txn_repo.record(
                organization_id=organization_id,
                wallet_id=wallet.id,
                transaction_type="release",
                credits_delta=0,
                available_delta=refund_credits,
                reserved_delta=-reserved_credits,
                balance_after=new_available,
                description=f"Call ended (0 credits billed): released hold of {reserved_credits} credits for call {call_id[:8]}",
                call_id=call_id,
                idempotency_key=idem_key,
            )

        # Clean Redis
        if redis:
            await redis.delete(_reserve_key(organization_id, call_id))

        log.info("settle org=%s call=%s billed=%d reserved=%d refund=%d available_after=%d",
                 organization_id, call_id, actual_credits, reserved_credits, refund_credits, new_available)

        return {
            "billed_credits": actual_credits,
            "reserved_credits": reserved_credits,
            "refunded_credits": refund_credits,
            "new_available_balance": new_available,
        }

    # -----------------------------------------------------------------------
    # Settle Duration (Minutes ceiling rounding)
    # -----------------------------------------------------------------------
    async def settle_duration(
        self,
        organization_id: str,
        call_id: str,
        duration_seconds: int,
        idempotency_key: Optional[str] = None,
    ) -> dict:
        """
        Settle call by duration in seconds, applying 1 credit = 1 minute ceil rounding:
        - duration <= 0: 0 credits
        - 1 to 60s: 1 credit
        - 61 to 120s: 2 credits
        """
        secs = max(0, int(duration_seconds))
        billed_minutes = math.ceil(secs / 60) if secs > 0 else 0
        idem_key = idempotency_key or f"settle_dur:{call_id}"
        result = await self.settle(
            organization_id=organization_id,
            call_id=call_id,
            actual_credits=billed_minutes,
            idempotency_key=idem_key,
        )
        result["duration_seconds"] = secs
        return result

    # -----------------------------------------------------------------------
    # Extend Hold (for live calls passing 5-minute threshold)
    # -----------------------------------------------------------------------
    async def extend_hold(
        self,
        organization_id: str,
        call_id: str,
        additional_credits: int = 5,
    ) -> dict:
        """
        Extend an active reservation by additional_credits (default 5 minutes).
        Reserves min(additional_credits, wallet.available_credits).
        Returns {extended_credits, total_reserved_credits, new_available_balance}.
        """
        if additional_credits <= 0:
            raise ValueError("additional_credits must be positive")

        wallet = await self.wallet_repo.get_or_create(organization_id)
        to_reserve = min(additional_credits, wallet.available_credits)
        if to_reserve <= 0:
            return {
                "extended_credits": 0,
                "total_reserved_credits": wallet.reserved_credits,
                "new_available_balance": wallet.available_credits,
                "can_extend": False,
            }

        updated = await self.wallet_repo.atomic_reserve(wallet.id, to_reserve)
        if updated is None:
            return {
                "extended_credits": 0,
                "total_reserved_credits": wallet.reserved_credits,
                "new_available_balance": wallet.available_credits,
                "can_extend": False,
            }

        new_available = updated["available_credits"]
        new_reserved = updated["reserved_credits"]

        # Redis update
        redis = self._get_redis()
        current_redis_reserved = to_reserve
        if redis:
            val = await redis.get(_reserve_key(organization_id, call_id))
            if val:
                current_redis_reserved = int(val) + to_reserve
            await redis.set(_reserve_key(organization_id, call_id), str(current_redis_reserved), ex=_RESERVE_TTL)

        # Ledger entry
        await self.txn_repo.record(
            organization_id=organization_id,
            wallet_id=wallet.id,
            transaction_type="reserve",
            credits_delta=0,
            available_delta=-to_reserve,
            reserved_delta=to_reserve,
            balance_after=new_available,
            description=f"Extended hold for call {call_id[:8]} (+{to_reserve} mins)",
            call_id=call_id,
        )

        return {
            "extended_credits": to_reserve,
            "total_reserved_credits": current_redis_reserved if redis else new_reserved,
            "new_available_balance": new_available,
            "can_extend": True,
        }

    # -----------------------------------------------------------------------
    # Check: can this org start a call?
    # -----------------------------------------------------------------------
    async def can_start_call(
        self,
        organization_id: str,
        required_credits: int = 5,
    ) -> dict:
        """Quick check before reserving — no state change."""
        wallet = await self.wallet_repo.get_or_create(organization_id)
        sufficient = wallet.available_credits >= required_credits
        return {
            "can_start": sufficient,
            "available_credits": wallet.available_credits,
            "required_credits": required_credits,
            "shortfall": max(0, required_credits - wallet.available_credits),
        }

    # -----------------------------------------------------------------------
    # Concurrent reservation summary (admin / monitoring)
    # -----------------------------------------------------------------------
    async def get_active_reservations(self, organization_id: str) -> list[dict]:
        """Return all outstanding reserve transactions for the org."""
        reserve_txns = await self.txn_repo.find_many(
            {
                "organization_id": organization_id,
                "transaction_type": "reserve",
            },
            sort=[("created_at", -1)],
            limit=100,
        )
        settled_call_ids = set()
        settle_txns = await self.txn_repo.find_many(
            {
                "organization_id": organization_id,
                "transaction_type": {"$in": ["release", "consume"]},
            }
        )
        for t in settle_txns:
            if t.call_id:
                settled_call_ids.add(t.call_id)

        active = []
        for t in reserve_txns:
            if t.call_id and t.call_id not in settled_call_ids:
                active.append({
                    "call_id": t.call_id,
                    "reserved_credits": abs(t.available_delta),
                    "reserved_at": t.created_at.isoformat(),
                })
        return active
