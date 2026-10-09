"""Release command: ensure MongoDB indexes exist.
Run by Fly.io on every deploy before routing traffic.
Safe to run multiple times (idempotent).
"""

import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

logging.basicConfig(level="INFO")
log = logging.getLogger("ensure_indexes")


async def main():
    from backend.config import settings
    from backend.core.db import init_db, close_db, ping_db

    log.info("Connecting to MongoDB: %s", settings.mongodb_database)
    await init_db()

    ok = await ping_db()
    if not ok:
        log.error("MongoDB ping failed — aborting")
        sys.exit(1)

    log.info("MongoDB connected. Indexes ensured.")
    await close_db()
    log.info("Done.")


if __name__ == "__main__":
    asyncio.run(main())
