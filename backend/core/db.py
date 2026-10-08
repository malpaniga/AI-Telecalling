"""MongoDB async client via Motor.

Single process-wide client. Use get_db() anywhere you need the database handle.
Collections are accessed as: db["organizations"], db["users"], etc.

Index creation is idempotent — safe to call on every startup.
"""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

from backend.config import settings

log = logging.getLogger("db")

_client: Optional[AsyncIOMotorClient] = None
_db: Optional[AsyncIOMotorDatabase] = None


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("MongoDB client not initialized. Call init_db() first.")
    return _client


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("MongoDB not initialized. Call init_db() first.")
    return _db


async def init_db() -> None:
    """Connect to MongoDB and create all indexes."""
    global _client, _db
    _client = AsyncIOMotorClient(
        settings.mongodb_uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
        maxPoolSize=50,
        minPoolSize=5,
    )
    _db = _client[settings.mongodb_database]
    log.info("MongoDB connected: %s / %s", settings.mongodb_uri.split("@")[-1], settings.mongodb_database)
    await _ensure_indexes(_db)


async def close_db() -> None:
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        log.info("MongoDB connection closed")


async def ping_db() -> bool:
    """Health check — returns True if MongoDB is reachable."""
    try:
        if _client is None:
            return False
        await _client.admin.command("ping")
        return True
    except Exception as exc:  # noqa: BLE001
        log.warning("MongoDB ping failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Index definitions
# ---------------------------------------------------------------------------
async def _ensure_indexes(db: AsyncIOMotorDatabase) -> None:
    """Create all collection indexes. Idempotent."""
    log.info("ensuring MongoDB indexes...")

    # organizations
    await db["organizations"].create_indexes([
        IndexModel([("slug", ASCENDING)], unique=True),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # users
    await db["users"].create_indexes([
        IndexModel([("email", ASCENDING)], unique=True),
        IndexModel([("organization_id", ASCENDING)]),
        IndexModel([("organization_id", ASCENDING), ("role", ASCENDING)]),
    ])

    # audit_logs
    await db["audit_logs"].create_indexes([
        IndexModel([("organization_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # subscription_plans
    await db["subscription_plans"].create_indexes([
        IndexModel([("slug", ASCENDING)], unique=True),
        IndexModel([("is_active", ASCENDING)]),
    ])

    # subscriptions
    await db["subscriptions"].create_indexes([
        IndexModel([("organization_id", ASCENDING)], unique=True),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("renews_at", ASCENDING)]),
    ])

    # wallets
    await db["wallets"].create_indexes([
        IndexModel([("organization_id", ASCENDING)], unique=True),
    ])

    # wallet_transactions
    await db["wallet_transactions"].create_indexes([
        IndexModel([("organization_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("idempotency_key", ASCENDING)], unique=True, sparse=True),
        IndexModel([("call_id", ASCENDING)], sparse=True),
    ])

    # credit_lots
    await db["credit_lots"].create_indexes([
        IndexModel([("organization_id", ASCENDING), ("expires_at", ASCENDING)]),
        IndexModel([("organization_id", ASCENDING), ("remaining_credits", DESCENDING)]),
    ])

    # orders
    await db["orders"].create_indexes([
        IndexModel([("organization_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("razorpay_order_id", ASCENDING)], sparse=True),
    ])

    # payments
    await db["payments"].create_indexes([
        IndexModel([("organization_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("razorpay_payment_id", ASCENDING)], sparse=True),
    ])

    # invoices
    await db["invoices"].create_indexes([
        IndexModel([("organization_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("invoice_number", ASCENDING)], unique=True),
    ])

    # webhook_events
    await db["webhook_events"].create_indexes([
        IndexModel([("provider", ASCENDING), ("event_id", ASCENDING)], unique=True),
        IndexModel([("created_at", DESCENDING)]),
    ])

    # phone_numbers
    await db["phone_numbers"].create_indexes([
        IndexModel([("number", ASCENDING)], unique=True),
        IndexModel([("organization_id", ASCENDING)], sparse=True),
        IndexModel([("status", ASCENDING)]),
        IndexModel([("provider", ASCENDING)]),
    ])

    # phone_number_assignments
    await db["phone_number_assignments"].create_indexes([
        IndexModel([("phone_number_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("organization_id", ASCENDING)]),
    ])

    # provider_configs
    await db["provider_configs"].create_indexes([
        IndexModel([("provider_type", ASCENDING), ("provider_name", ASCENDING)], unique=True),
    ])

    # voice_profiles
    await db["voice_profiles"].create_indexes([
        IndexModel([("organization_id", ASCENDING)], sparse=True),
        IndexModel([("is_platform", ASCENDING)]),
    ])

    # voice_profile_versions
    await db["voice_profile_versions"].create_indexes([
        IndexModel([("voice_profile_id", ASCENDING), ("version", DESCENDING)], unique=True),
        IndexModel([("voice_profile_id", ASCENDING), ("is_published", ASCENDING)]),
    ])

    # provider_routes
    await db["provider_routes"].create_indexes([
        IndexModel([("voice_profile_version_id", ASCENDING)]),
        IndexModel([("provider_type", ASCENDING), ("provider_name", ASCENDING)]),
    ])

    await db["provider_failover_events"].create_index([("created_at", DESCENDING)])

    # agents
    await db["agents"].create_indexes([
        IndexModel([("organization_id", ASCENDING)]),
        IndexModel([("organization_id", ASCENDING), ("is_active", ASCENDING)]),
    ])

    # agent_versions
    await db["agent_versions"].create_indexes([
        IndexModel([("agent_id", ASCENDING), ("version", DESCENDING)]),
    ])

    # business_templates
    await db["business_templates"].create_indexes([
        IndexModel([("slug", ASCENDING)], unique=True),
        IndexModel([("is_active", ASCENDING)]),
    ])

    # knowledge_bases
    await db["knowledge_bases"].create_indexes([
        IndexModel([("organization_id", ASCENDING)]),
    ])

    # leads
    await db["leads"].create_indexes([
        IndexModel([("organization_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("organization_id", ASCENDING), ("phone", ASCENDING)]),
        IndexModel([("organization_id", ASCENDING), ("status", ASCENDING)]),
        IndexModel([("campaign_id", ASCENDING)], sparse=True),
        IndexModel([("organization_id", ASCENDING), ("phone", ASCENDING)], unique=True, sparse=True),
    ])

    # dnc_entries
    await db["dnc_entries"].create_indexes([
        IndexModel([("organization_id", ASCENDING), ("phone", ASCENDING)], unique=True),
    ])

    # campaigns
    await db["campaigns"].create_indexes([
        IndexModel([("organization_id", ASCENDING)]),
        IndexModel([("organization_id", ASCENDING), ("status", ASCENDING)]),
        IndexModel([("scheduled_at", ASCENDING)], sparse=True),
    ])

    # calls
    await db["calls"].create_indexes([
        IndexModel([("organization_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("campaign_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("lead_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("status", ASCENDING)]),
    ])

    # transcripts
    await db["transcripts"].create_indexes([
        IndexModel([("call_id", ASCENDING)], unique=True),
        IndexModel([("organization_id", ASCENDING)]),
    ])

    # appointments
    await db["appointments"].create_indexes([
        IndexModel([("organization_id", ASCENDING), ("scheduled_at", ASCENDING)]),
        IndexModel([("lead_id", ASCENDING)]),
        IndexModel([("call_id", ASCENDING)], sparse=True),
    ])

    # usage_events
    await db["usage_events"].create_indexes([
        IndexModel([("organization_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("call_id", ASCENDING)]),
        IndexModel([("idempotency_key", ASCENDING)], unique=True, sparse=True),
    ])

    # provider_usage
    await db["provider_usage"].create_indexes([
        IndexModel([("provider", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("call_id", ASCENDING)]),
    ])

    # analytics_daily
    await db["analytics_daily"].create_indexes([
        IndexModel([("organization_id", ASCENDING), ("date", DESCENDING)]),
        IndexModel([("organization_id", ASCENDING), ("date", ASCENDING)], unique=True),
    ])

    # notifications
    await db["notifications"].create_indexes([
        IndexModel([("organization_id", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("organization_id", ASCENDING), ("is_read", ASCENDING)]),
    ])

    log.info("MongoDB indexes ensured")
