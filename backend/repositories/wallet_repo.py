"""Wallet, WalletTransaction, CreditLot, and CallingPack repositories.

All credit operations use atomic MongoDB $inc to prevent race conditions.
Every successful credit operation creates an immutable WalletTransaction.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from backend.models.base import new_id, utcnow
from backend.models.wallet import CallingPack, CreditLot, Wallet, WalletTransaction
from backend.repositories.base import BaseRepository

log = logging.getLogger("repo.wallet")


class CallingPackRepository(BaseRepository):
    collection_name = "calling_packs"
    model_class = CallingPack

    async def create(
        self,
        name: str,
        slug: str,
        credits: int,
        price_paise: int,
        description: str = "",
        validity_days: int = 365,
        bonus_credits: int = 0,
        is_public: bool = True,
        sort_order: int = 0,
    ) -> CallingPack:
        pack = CallingPack(
            _id=new_id(),
            name=name,
            slug=slug,
            credits=credits,
            price_paise=price_paise,
            description=description,
            validity_days=validity_days,
            bonus_credits=bonus_credits,
            is_public=is_public,
            sort_order=sort_order,
        )
        await self.insert(pack)
        log.info("calling pack created id=%s slug=%s credits=%d", pack.id, pack.slug, credits)
        return pack

    async def find_by_slug(self, slug: str) -> Optional[CallingPack]:
        return await self.find_one({"slug": slug})

    async def list_public(self) -> list[CallingPack]:
        return await self.find_many(
            {"is_active": True, "is_public": True},
            sort=[("sort_order", ASCENDING)],
        )

    async def list_all(self, include_inactive: bool = False) -> list[CallingPack]:
        q = {} if include_inactive else {"is_active": True}
        return await self.find_many(q, sort=[("sort_order", ASCENDING)])


class WalletRepository(BaseRepository):
    collection_name = "wallets"
    model_class = Wallet

    async def get_or_create(self, organization_id: str) -> Wallet:
        """Get existing wallet or create one if it doesn't exist."""
        wallet = await self.find_one({"organization_id": organization_id})
        if wallet:
            return wallet
        wallet = Wallet(_id=new_id(), organization_id=organization_id)
        try:
            await self.insert(wallet)
        except DuplicateKeyError:
            # Race condition: another process created it
            wallet = await self.find_one({"organization_id": organization_id})
        return wallet

    async def atomic_credit_available(
        self,
        wallet_id: str,
        delta: int,
        require_sufficient: bool = True,
    ) -> Optional[dict]:
        """
        Atomically change available_credits by delta.
        If require_sufficient=True, only succeeds if balance won't go negative.
        Returns the updated wallet doc or None if insufficient credits.
        """
        query = {"_id": wallet_id}
        if require_sufficient and delta < 0:
            # Only allow deduction if balance is sufficient
            query["available_credits"] = {"$gte": abs(delta)}

        update = {
            "$inc": {
                "available_credits": delta,
                "updated_at": 0,  # will be overridden below
            },
            "$set": {"updated_at": utcnow()},
        }
        if delta > 0:
            update["$inc"]["total_purchased"] = delta  # approximate; refined per type below

        result = await self.col.find_one_and_update(
            query,
            {"$inc": {"available_credits": delta},
             "$set": {"updated_at": utcnow()}},
            return_document=True,
        )
        return result

    async def atomic_reserve(
        self,
        wallet_id: str,
        credits: int,
    ) -> Optional[dict]:
        """Move credits from available → reserved. Returns updated doc or None if insufficient."""
        query = {"_id": wallet_id, "available_credits": {"$gte": credits}}
        result = await self.col.find_one_and_update(
            query,
            {
                "$inc": {"available_credits": -credits, "reserved_credits": credits},
                "$set": {"updated_at": utcnow()},
            },
            return_document=True,
        )
        return result

    async def atomic_release(
        self,
        wallet_id: str,
        credits: int,
    ) -> Optional[dict]:
        """Move credits from reserved → available (call cancelled, not billed)."""
        query = {"_id": wallet_id, "reserved_credits": {"$gte": credits}}
        result = await self.col.find_one_and_update(
            query,
            {
                "$inc": {"available_credits": credits, "reserved_credits": -credits},
                "$set": {"updated_at": utcnow()},
            },
            return_document=True,
        )
        return result

    async def atomic_consume(
        self,
        wallet_id: str,
        reserved_credits: int,
        actual_credits: int,
    ) -> Optional[dict]:
        """
        Finalize call billing: remove from reserved, add difference back to available.
        actual_credits ≤ reserved_credits (we over-reserve, then settle exact amount).
        """
        refund_to_available = reserved_credits - actual_credits
        query = {"_id": wallet_id, "reserved_credits": {"$gte": reserved_credits}}
        result = await self.col.find_one_and_update(
            query,
            {
                "$inc": {
                    "reserved_credits": -reserved_credits,
                    "available_credits": refund_to_available,
                    "total_consumed": actual_credits,
                },
                "$set": {"updated_at": utcnow()},
            },
            return_document=True,
        )
        return result

    async def atomic_add(
        self,
        wallet_id: str,
        credits: int,
        field: str = "total_purchased",
    ) -> Optional[dict]:
        """Add credits to available_credits and update a lifetime counter."""
        result = await self.col.find_one_and_update(
            {"_id": wallet_id},
            {
                "$inc": {"available_credits": credits, field: credits},
                "$set": {"updated_at": utcnow()},
            },
            return_document=True,
        )
        return result

    async def atomic_expire(
        self,
        wallet_id: str,
        credits: int,
    ) -> Optional[dict]:
        """Remove expired credits from available_credits."""
        query = {"_id": wallet_id, "available_credits": {"$gte": credits}}
        result = await self.col.find_one_and_update(
            query,
            {
                "$inc": {"available_credits": -credits, "total_expired": credits},
                "$set": {"updated_at": utcnow()},
            },
            return_document=True,
        )
        return result


class WalletTransactionRepository(BaseRepository):
    collection_name = "wallet_transactions"
    model_class = WalletTransaction

    async def record(
        self,
        organization_id: str,
        wallet_id: str,
        transaction_type: str,
        credits_delta: int,
        available_delta: int,
        reserved_delta: int,
        balance_after: int,
        description: str = "",
        call_id: Optional[str] = None,
        order_id: Optional[str] = None,
        credit_lot_id: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> Optional[WalletTransaction]:
        """Record an immutable ledger entry.
        Returns None if idempotency_key already exists (duplicate prevention).
        """
        if idempotency_key:
            existing = await self.find_one({"idempotency_key": idempotency_key})
            if existing:
                log.info("duplicate transaction prevented key=%s", idempotency_key)
                return None

        txn = WalletTransaction(
            _id=new_id(),
            organization_id=organization_id,
            wallet_id=wallet_id,
            transaction_type=transaction_type,
            credits_delta=credits_delta,
            available_delta=available_delta,
            reserved_delta=reserved_delta,
            balance_after=balance_after,
            description=description,
            call_id=call_id,
            order_id=order_id,
            credit_lot_id=credit_lot_id,
            idempotency_key=idempotency_key,
            created_by=created_by,
        )
        await self.insert(txn)
        return txn

    async def list_for_org(
        self,
        organization_id: str,
        limit: int = 100,
        skip: int = 0,
        txn_type: Optional[str] = None,
    ) -> list[WalletTransaction]:
        query: dict = {"organization_id": organization_id}
        if txn_type:
            query["transaction_type"] = txn_type
        return await self.find_many(
            query,
            sort=[("created_at", DESCENDING)],
            limit=limit,
            skip=skip,
        )


class CreditLotRepository(BaseRepository):
    collection_name = "credit_lots"
    model_class = CreditLot

    async def create(
        self,
        organization_id: str,
        wallet_id: str,
        transaction_id: str,
        credits: int,
        source: str = "purchase",
        order_id: Optional[str] = None,
        calling_pack_id: Optional[str] = None,
        validity_days: int = 365,
    ) -> CreditLot:
        from datetime import timedelta
        expires_at = None
        if validity_days > 0:
            expires_at = utcnow() + timedelta(days=validity_days)

        lot = CreditLot(
            _id=new_id(),
            organization_id=organization_id,
            wallet_id=wallet_id,
            transaction_id=transaction_id,
            original_credits=credits,
            remaining_credits=credits,
            source=source,
            order_id=order_id,
            calling_pack_id=calling_pack_id,
            expires_at=expires_at,
            is_active=True,
        )
        await self.insert(lot)
        return lot

    async def list_active(
        self, organization_id: str
    ) -> list[CreditLot]:
        """Active lots, sorted FIFO (oldest first for consumption)."""
        return await self.find_many(
            {"organization_id": organization_id, "is_active": True},
            sort=[("purchased_at", ASCENDING)],
        )

    async def list_expiring_soon(
        self,
        before: datetime,
    ) -> list[CreditLot]:
        """Lots expiring before `before` with remaining credits > 0."""
        return await self.find_many(
            {
                "is_active": True,
                "expires_at": {"$lte": before, "$ne": None},
                "remaining_credits": {"$gt": 0},
            },
            sort=[("expires_at", ASCENDING)],
        )

    async def consume_from_lots(
        self,
        organization_id: str,
        credits_needed: int,
    ) -> int:
        """
        Consume credits_needed from active lots in FIFO order.
        Returns actual credits consumed (may be less if insufficient).
        """
        lots = await self.list_active(organization_id)
        remaining = credits_needed
        consumed_total = 0

        for lot in lots:
            if remaining <= 0:
                break
            if lot.is_expired:
                continue
            available = lot.available_from_lot
            if available <= 0:
                continue

            consume = min(available, remaining)
            new_remaining = lot.remaining_credits - consume

            await self.update_by_id(lot.id, {
                "remaining_credits": new_remaining,
                "is_active": new_remaining > 0 or lot.reserved_from_lot > 0,
            })
            consumed_total += consume
            remaining -= consume

        return consumed_total

    async def deactivate_expired(self) -> int:
        """Mark fully-expired lots as inactive. Returns count."""
        now = utcnow()
        result = await self.col.update_many(
            {
                "is_active": True,
                "expires_at": {"$lte": now, "$ne": None},
            },
            {"$set": {"is_active": False, "updated_at": now}},
        )
        return result.modified_count
