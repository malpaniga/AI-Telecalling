"""Wallet service — all credit operations.

Every operation:
1. Modifies wallet atomically via $inc
2. Creates an immutable WalletTransaction ledger entry
3. Creates/updates CreditLots where applicable

No floating point. No silent failures. No negative balances.
Idempotency via idempotency_key on WalletTransaction.

Seed calling packs on startup (idempotent).
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.wallet import CallingPack, CreditLot, Wallet, WalletTransaction
from backend.models.base import new_id, utcnow
from backend.repositories.wallet_repo import (
    CallingPackRepository,
    CreditLotRepository,
    WalletRepository,
    WalletTransactionRepository,
)

log = logging.getLogger("service.wallet")

# ---------------------------------------------------------------------------
# Default calling packs seeded on startup
# ---------------------------------------------------------------------------
DEFAULT_CALLING_PACKS = [
    {
        "name": "Trial Pack",
        "slug": "trial",
        "credits": 300,           # 5 minutes
        "price_paise": 0,         # free trial
        "description": "Try AI calling with 5 free minutes.",
        "validity_days": 30,
        "bonus_credits": 0,
        "sort_order": 0,
        "is_public": False,       # only granted by platform
    },
    {
        "name": "Starter Pack",
        "slug": "starter-pack",
        "credits": 1000,          # ~17 minutes
        "price_paise": 99900,     # ₹999
        "description": "1,000 calling credits (~17 minutes of AI calls).",
        "validity_days": 90,
        "bonus_credits": 0,
        "sort_order": 1,
    },
    {
        "name": "Growth Pack",
        "slug": "growth-pack",
        "credits": 5000,          # ~83 minutes
        "price_paise": 399900,    # ₹3,999
        "description": "5,000 calling credits (~83 minutes). Best value.",
        "validity_days": 180,
        "bonus_credits": 500,     # 10% bonus
        "sort_order": 2,
    },
    {
        "name": "Pro Pack",
        "slug": "pro-pack",
        "credits": 10000,         # ~167 minutes
        "price_paise": 699900,    # ₹6,999
        "description": "10,000 credits + 1,500 bonus (~192 minutes total).",
        "validity_days": 365,
        "bonus_credits": 1500,    # 15% bonus
        "sort_order": 3,
    },
]


async def seed_default_packs(db: AsyncIOMotorDatabase) -> list[CallingPack]:
    """Seed default calling packs. Idempotent."""
    repo = CallingPackRepository(db)
    created = []
    for pack_data in DEFAULT_CALLING_PACKS:
        if await repo.find_by_slug(pack_data["slug"]) is None:
            pack = await repo.create(**pack_data)
            created.append(pack)
            log.info("seeded calling pack: %s (%d credits)", pack.slug, pack.credits)
    return created


# ---------------------------------------------------------------------------
# Wallet service
# ---------------------------------------------------------------------------
class WalletService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.wallet_repo = WalletRepository(db)
        self.txn_repo = WalletTransactionRepository(db)
        self.lot_repo = CreditLotRepository(db)
        self.pack_repo = CallingPackRepository(db)

    async def get_or_create_wallet(self, organization_id: str) -> Wallet:
        return await self.wallet_repo.get_or_create(organization_id)

    async def get_balance(self, organization_id: str) -> dict:
        wallet = await self.wallet_repo.get_or_create(organization_id)
        return {
            "organization_id": organization_id,
            "available_credits": wallet.available_credits,
            "reserved_credits": wallet.reserved_credits,
            "total_credits": wallet.total_credits,
            "low_credit_threshold": wallet.low_credit_threshold,
            "is_low": wallet.available_credits <= wallet.low_credit_threshold,
        }

    # ---- Purchase (triggered by payment_service after successful payment) ----

    async def purchase_credits(
        self,
        organization_id: str,
        calling_pack_id: str,
        order_id: str,
        idempotency_key: Optional[str] = None,
    ) -> dict:
        """
        Grant credits from a calling pack purchase.
        Idempotent: same idempotency_key is safe to call multiple times.
        Returns: {credits_granted, transaction_id, lot_id, new_balance}
        """
        pack = await self.pack_repo.find_by_id(calling_pack_id)
        if pack is None:
            raise ValueError(f"CallingPack {calling_pack_id} not found")

        idem_key = idempotency_key or f"purchase:{order_id}:{calling_pack_id}"

        wallet = await self.wallet_repo.get_or_create(organization_id)
        total_credits = pack.total_credits  # base + bonus

        # Idempotency check BEFORE wallet update
        if await self.txn_repo.find_one({"idempotency_key": idem_key}):
            log.info("purchase_credits: idempotent replay key=%s", idem_key)
            balance = await self.get_balance(organization_id)
            return {"credits_granted": 0, "idempotent": True,
                    "new_balance": balance["available_credits"]}

        # Atomic wallet update
        updated = await self.wallet_repo.atomic_add(
            wallet.id, total_credits, field="total_purchased"
        )
        if updated is None:
            raise RuntimeError("Failed to update wallet")

        new_balance = updated["available_credits"]

        # Ledger entry
        txn = await self.txn_repo.record(
            organization_id=organization_id,
            wallet_id=wallet.id,
            transaction_type="purchase",
            credits_delta=total_credits,
            available_delta=total_credits,
            reserved_delta=0,
            balance_after=new_balance,
            description=f"Purchased {pack.name} ({total_credits} credits)",
            order_id=order_id,
            idempotency_key=idem_key,
        )
        if txn is None:
            # Idempotency: already processed — fetch existing balance
            return {
                "credits_granted": 0,
                "idempotent": True,
                "new_balance": new_balance,
            }

        # Credit lot (for expiry tracking)
        lot = await self.lot_repo.create(
            organization_id=organization_id,
            wallet_id=wallet.id,
            transaction_id=txn.id,
            credits=total_credits,
            source="purchase",
            order_id=order_id,
            calling_pack_id=calling_pack_id,
            validity_days=pack.validity_days,
        )

        log.info("purchase_credits org=%s credits=%d balance=%d",
                 organization_id, total_credits, new_balance)

        return {
            "credits_granted": total_credits,
            "transaction_id": txn.id,
            "lot_id": lot.id,
            "new_balance": new_balance,
            "expires_at": lot.expires_at.isoformat() if lot.expires_at else None,
        }

    # ---- Bonus ----

    async def grant_bonus(
        self,
        organization_id: str,
        credits: int,
        description: str = "Platform bonus",
        validity_days: int = 90,
        created_by: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> dict:
        """Grant free bonus credits. Admin action."""
        if credits <= 0:
            raise ValueError("Bonus credits must be positive")

        wallet = await self.wallet_repo.get_or_create(organization_id)

        # Check idempotency
        if idempotency_key:
            existing = await self.txn_repo.find_one({"idempotency_key": idempotency_key})
            if existing:
                return {"credits_granted": 0, "idempotent": True}

        updated = await self.wallet_repo.atomic_add(wallet.id, credits, field="total_bonus")
        if updated is None:
            raise RuntimeError("Failed to update wallet")

        txn = await self.txn_repo.record(
            organization_id=organization_id,
            wallet_id=wallet.id,
            transaction_type="bonus",
            credits_delta=credits,
            available_delta=credits,
            reserved_delta=0,
            balance_after=updated["available_credits"],
            description=description,
            idempotency_key=idempotency_key,
            created_by=created_by,
        )

        lot = await self.lot_repo.create(
            organization_id=organization_id,
            wallet_id=wallet.id,
            transaction_id=txn.id if txn else "bonus",
            credits=credits,
            source="bonus",
            validity_days=validity_days,
        )

        log.info("bonus org=%s credits=%d by=%s", organization_id, credits, created_by)
        return {
            "credits_granted": credits,
            "transaction_id": txn.id if txn else None,
            "lot_id": lot.id,
            "new_balance": updated["available_credits"],
        }

    # ---- Admin adjustment ----

    async def admin_adjustment(
        self,
        organization_id: str,
        credits_delta: int,
        reason: str,
        admin_user_id: str,
        idempotency_key: Optional[str] = None,
    ) -> dict:
        """
        Manual credit adjustment by platform admin.
        credits_delta positive = add, negative = deduct.
        """
        wallet = await self.wallet_repo.get_or_create(organization_id)

        if credits_delta == 0:
            raise ValueError("credits_delta cannot be zero")

        if credits_delta > 0:
            updated = await self.wallet_repo.atomic_add(
                wallet.id, credits_delta, field="total_bonus"
            )
        else:
            # Deduction — prevent negative balance
            updated = await self.wallet_repo.atomic_credit_available(
                wallet.id, credits_delta, require_sufficient=True
            )
            if updated is None:
                raise ValueError(
                    f"Insufficient credits for deduction. "
                    f"Requested: {abs(credits_delta)}, "
                    f"Available: {wallet.available_credits}"
                )

        txn = await self.txn_repo.record(
            organization_id=organization_id,
            wallet_id=wallet.id,
            transaction_type="admin_adjustment",
            credits_delta=credits_delta,
            available_delta=credits_delta,
            reserved_delta=0,
            balance_after=updated["available_credits"],
            description=reason,
            idempotency_key=idempotency_key,
            created_by=admin_user_id,
        )

        if credits_delta > 0 and txn:
            await self.lot_repo.create(
                organization_id=organization_id,
                wallet_id=wallet.id,
                transaction_id=txn.id,
                credits=credits_delta,
                source="admin_adjustment",
                validity_days=365,
            )

        log.info("admin_adjustment org=%s delta=%d by=%s", organization_id, credits_delta, admin_user_id)
        return {
            "credits_delta": credits_delta,
            "transaction_id": txn.id if txn else None,
            "new_balance": updated["available_credits"],
        }

    # ---- Expiry processing ----

    async def process_expiry(self, organization_id: str) -> dict:
        """
        Expire lots past their expiry date and remove those credits from wallet.
        Returns {expired_lots, expired_credits}.
        """
        wallet = await self.wallet_repo.get_or_create(organization_id)
        now = utcnow()

        # Find expired active lots
        lots = await self.lot_repo.find_many(
            {
                "organization_id": organization_id,
                "is_active": True,
                "expires_at": {"$lte": now, "$ne": None},
                "remaining_credits": {"$gt": 0},
            }
        )

        total_expired = 0
        for lot in lots:
            expire_credits = lot.remaining_credits
            if expire_credits <= 0:
                continue

            # Remove from wallet
            updated = await self.wallet_repo.atomic_expire(wallet.id, expire_credits)
            if updated is None:
                log.warning("expiry: wallet update failed for lot=%s", lot.id)
                continue

            # Deactivate lot
            await self.lot_repo.update_by_id(lot.id, {
                "remaining_credits": 0,
                "is_active": False,
            })

            # Ledger entry
            await self.txn_repo.record(
                organization_id=organization_id,
                wallet_id=wallet.id,
                transaction_type="expiry",
                credits_delta=-expire_credits,
                available_delta=-expire_credits,
                reserved_delta=0,
                balance_after=updated["available_credits"],
                description=f"Credits expired (lot {lot.id[:8]})",
                credit_lot_id=lot.id,
            )
            total_expired += expire_credits

        if total_expired > 0:
            log.info("expiry org=%s expired_credits=%d", organization_id, total_expired)

        return {"expired_lots": len(lots), "expired_credits": total_expired}

    # ---- Summary for API ----

    async def get_wallet_summary(self, organization_id: str) -> dict:
        wallet = await self.wallet_repo.get_or_create(organization_id)
        lots = await self.lot_repo.list_active(organization_id)

        # Next expiry
        next_expiry = None
        for lot in lots:
            if lot.expires_at and lot.remaining_credits > 0:
                if next_expiry is None or lot.expires_at < next_expiry:
                    next_expiry = lot.expires_at

        return {
            "available_credits": wallet.available_credits,
            "reserved_credits": wallet.reserved_credits,
            "total_credits": wallet.total_credits,
            "total_purchased": wallet.total_purchased,
            "total_consumed": wallet.total_consumed,
            "total_expired": wallet.total_expired,
            "total_bonus": wallet.total_bonus,
            "is_low": wallet.available_credits <= wallet.low_credit_threshold,
            "low_credit_threshold": wallet.low_credit_threshold,
            "next_expiry": next_expiry.isoformat() if next_expiry else None,
            "active_lots": len(lots),
        }
