"""Data Migration Script: Convert legacy second-based credits to 1-credit-per-minute system.

Actions:
1. Backfills organization settings:
   - free_test_sessions_remaining: 10
   - free_test_session_max_minutes: 3
   - max_call_duration_minutes: 7
2. Safely converts legacy second-based wallets to minutes:
   new_balance = math.ceil(old_seconds / 60)
3. Supports --dry-run to preview changes without modifying MongoDB.
"""

import argparse
import asyncio
import logging
import math
import sys
from motor.motor_asyncio import AsyncIOMotorClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("migration.credits")


async def run_migration(mongo_uri: str, db_name: str, dry_run: bool = False):
    log.info("Connecting to MongoDB: %s (db: %s)", mongo_uri, db_name)
    client = AsyncIOMotorClient(mongo_uri)
    db = client[db_name]

    log.info("Starting migration (dry_run=%s)...", dry_run)

    # 1. Backfill Organizations Settings
    orgs_cursor = db.organizations.find({})
    org_count = 0
    org_updated = 0

    async for org in orgs_cursor:
        org_count += 1
        org_id = org["_id"]
        settings = org.get("settings") or {}

        updates = {}
        if "free_test_sessions_remaining" not in settings:
            updates["settings.free_test_sessions_remaining"] = 10
        if "free_test_session_max_minutes" not in settings:
            updates["settings.free_test_session_max_minutes"] = 3
        if "max_call_duration_minutes" not in settings:
            updates["settings.max_call_duration_minutes"] = 7

        if updates:
            org_updated += 1
            log.info("Org %s (%s): applying updates %s", org_id, org.get("name"), updates)
            if not dry_run:
                await db.organizations.update_one({"_id": org_id}, {"$set": updates})

    log.info("Organizations scanned: %d, backfilled: %d", org_count, org_updated)

    # 2. Migrate Wallets
    wallets_cursor = db.wallets.find({})
    wallet_count = 0
    wallet_updated = 0

    async for w in wallets_cursor:
        wallet_count += 1
        w_id = w["_id"]
        org_id = w.get("organization_id")
        
        # Check if already migrated
        if w.get("is_minute_billing_migrated"):
            continue

        old_purchased = w.get("total_purchased", 0)
        old_consumed = w.get("total_consumed", 0)
        old_bonus = w.get("total_bonus", 0)
        old_expired = w.get("total_expired", 0)
        old_reserved = w.get("reserved_credits", 0)

        # Convert to minutes with ceiling rounding
        new_purchased = math.ceil(old_purchased / 60) if old_purchased > 0 else 0
        new_consumed = math.ceil(old_consumed / 60) if old_consumed > 0 else 0
        new_bonus = math.ceil(old_bonus / 60) if old_bonus > 0 else 0
        new_expired = math.ceil(old_expired / 60) if old_expired > 0 else 0
        new_reserved = math.ceil(old_reserved / 60) if old_reserved > 0 else 0

        new_available = max(0, new_purchased + new_bonus - new_consumed - new_expired - new_reserved)

        wallet_updates = {
            "total_purchased": new_purchased,
            "total_consumed": new_consumed,
            "total_bonus": new_bonus,
            "total_expired": new_expired,
            "reserved_credits": new_reserved,
            "available_credits": new_available,
            "is_minute_billing_migrated": True,
        }

        wallet_updated += 1
        log.info(
            "Wallet %s (org: %s): converted purchased=%s->%s, consumed=%s->%s, available=%s->%s",
            w_id, org_id, old_purchased, new_purchased, old_consumed, new_consumed, w.get("available_credits"), new_available
        )

        if not dry_run:
            await db.wallets.update_one({"_id": w_id}, {"$set": wallet_updates})

    log.info("Wallets scanned: %d, migrated: %d", wallet_count, wallet_updated)
    log.info("Migration complete!")


def main():
    parser = argparse.ArgumentParser(description="Migrate credits from seconds to minutes")
    parser.add_argument("--mongo-uri", default="mongodb://localhost:27017", help="MongoDB connection URI")
    parser.add_argument("--db-name", default="saas", help="Database name")
    parser.add_argument("--dry-run", action="store_true", help="Preview migration without modifying data")
    args = parser.parse_args()

    asyncio.run(run_migration(args.mongo_uri, args.db_name, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
