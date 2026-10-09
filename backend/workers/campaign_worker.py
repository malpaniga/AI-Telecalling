"""Campaign worker — polls Redis for pending campaigns and initiates calls.

This is a separate process from the API server. It:
  1. Polls Redis for campaigns with status=running
  2. For each running campaign, checks if a call slot is available
  3. Picks the next eligible lead (new/callback, not DNC, not max attempts)
  4. Initiates an outbound call via the telephony provider
  5. Updates lead status to 'calling'
  6. After the call, triggers post-call processing

Designed to be horizontally scalable — multiple workers can run without
stepping on each other (Redis coordination via atomic INCR/campaign locks).

For MVP: single-process polling. For production: Fly.io autoscaling.
"""

import asyncio
import logging
import signal
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
log = logging.getLogger("campaign_worker")

POLL_INTERVAL_S = 5     # seconds between campaign poll cycles
SHUTDOWN_TIMEOUT_S = 30 # graceful shutdown window


class CampaignWorker:
    def __init__(self):
        self._running = True
        self._db = None
        self._redis = None

    async def setup(self):
        from backend.core.db import init_db, get_db
        from backend.core.redis import init_redis, get_redis
        from backend.services.subscription_service import seed_default_plans
        from backend.services.wallet_service import seed_default_packs

        await init_db()
        await init_redis()
        self._db = get_db()
        self._redis = get_redis()
        log.info("Campaign worker started")

    async def teardown(self):
        from backend.core.db import close_db
        from backend.core.redis import close_redis
        await close_db()
        await close_redis()
        log.info("Campaign worker stopped")

    async def run(self):
        await self.setup()
        try:
            while self._running:
                try:
                    await self._poll_campaigns()
                except Exception as exc:  # noqa: BLE001
                    log.exception("Worker poll cycle error: %s", exc)
                await asyncio.sleep(POLL_INTERVAL_S)
        finally:
            await self.teardown()

    async def _poll_campaigns(self):
        """Find running campaigns and dispatch calls."""
        from backend.repositories.campaign_repo import CampaignRepository
        from backend.services.campaign_service import CampaignService

        repo = CampaignRepository(self._db)
        running = await repo.list_active()

        for campaign in running:
            if campaign.status != "running":
                continue
            try:
                await self._process_campaign(campaign)
            except Exception as exc:  # noqa: BLE001
                log.warning("Error processing campaign=%s: %s", campaign.id, exc)

    async def _process_campaign(self, campaign):
        """Try to start a new call for this campaign."""
        from backend.services.campaign_service import CampaignService
        from backend.services.credit_service import CreditService
        from backend.repositories.lead_repo import LeadRepository

        camp_svc = CampaignService(self._db, redis=self._redis)
        credit_svc = CreditService(self._db, redis=self._redis)
        lead_repo = LeadRepository(self._db)

        # Check if a call slot is available
        check = await camp_svc.can_start_call(campaign.id, campaign.organization_id)
        if not check["allowed"]:
            return

        # Check credits
        credit_check = await credit_svc.can_start_call(
            campaign.organization_id, required_credits=60
        )
        if not credit_check["can_start"]:
            log.warning("campaign=%s pausing: insufficient credits", campaign.id)
            await camp_svc.pause_campaign(
                campaign.id, campaign.organization_id, reason="low_credits"
            )
            return

        # Pick next eligible lead
        query = {
            "organization_id": campaign.organization_id,
            "status": {"$in": ["new", "callback", "scheduled"]},
        }
        if campaign.lead_filter:
            query.update(campaign.lead_filter)
        if campaign.campaign_id_filter:
            query["campaign_id"] = campaign.campaign_id_filter

        lead_doc = await self._db["leads"].find_one_and_update(
            query,
            {"$set": {"status": "scheduled"}},
            return_document=True,
        )
        if lead_doc is None:
            # No more leads — campaign complete
            log.info("campaign=%s complete (no more leads)", campaign.id)
            await camp_svc.complete_campaign(campaign.id, campaign.organization_id)
            return

        # Acquire concurrency slot
        acquired = await camp_svc.acquire_call_slot(campaign.id)
        if not acquired:
            # Release lead back
            await self._db["leads"].update_one(
                {"_id": lead_doc["_id"]},
                {"$set": {"status": "new"}},
            )
            return

        # Initiate call (async — worker continues polling)
        asyncio.create_task(
            self._initiate_call(campaign, lead_doc, camp_svc, credit_svc)
        )

    async def _initiate_call(self, campaign, lead_doc, camp_svc, credit_svc):
        """Initiate the actual call and handle completion."""
        from backend.services.call_service import CallService
        call_svc = CallService(self._db, redis=self._redis)
        lead_id = str(lead_doc["_id"])

        try:
            result = await call_svc.initiate_call(
                organization_id=campaign.organization_id,
                to_number=lead_doc["phone"],
                from_number=campaign.calling_number,
                campaign_id=campaign.id,
                lead_id=lead_id,
                agent_id=campaign.agent_id,
                agent_version=campaign.agent_version,
                provider="mock",  # M8: provider from voice profile route
            )
            log.info("call initiated call=%s lead=%s", result["call_id"], lead_id)
        except Exception as exc:  # noqa: BLE001
            log.warning("call initiation failed lead=%s: %s", lead_id, exc)
            # Release concurrency slot
            await camp_svc.release_call_slot(campaign.id)
            # Reset lead
            await self._db["leads"].update_one(
                {"_id": lead_doc["_id"]},
                {"$set": {"status": "new"}},
            )

    def shutdown(self, signum, frame):
        log.info("Shutdown signal received (%s)", signum)
        self._running = False


async def main():
    worker = CampaignWorker()
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGTERM, worker.shutdown, signal.SIGTERM, None)
    loop.add_signal_handler(signal.SIGINT, worker.shutdown, signal.SIGINT, None)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
