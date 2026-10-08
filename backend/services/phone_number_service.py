"""Phone number service — inventory management.

All operations record an immutable PhoneNumberAssignment for audit history.

Customer-facing methods return numbers WITHOUT provider details.
Admin methods include provider details.

Concurrent reservation:
  The reserve step uses atomic_reserve() which uses a single MongoDB document
  update with {status: "available"} as the query filter. Only ONE request can
  win; concurrent requests get None back and raise.
"""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.phone_number import PhoneNumber, PhoneNumberAssignment
from backend.repositories.phone_number_repo import (
    PhoneNumberAssignmentRepository,
    PhoneNumberRepository,
)

log = logging.getLogger("service.phone_number")

# Default seed numbers for DEMO_MODE / testing
SEED_NUMBERS = [
    {"number": "+911800123001", "provider": "mock", "display_name": "Mumbai DID 1",
     "country_code": "IN", "number_type": "local", "can_voice": True, "can_sms": True},
    {"number": "+911800123002", "provider": "mock", "display_name": "Mumbai DID 2",
     "country_code": "IN", "number_type": "local", "can_voice": True, "can_sms": False},
    {"number": "+911800123003", "provider": "mock", "display_name": "Delhi DID 1",
     "country_code": "IN", "number_type": "local", "can_voice": True, "can_sms": True},
    {"number": "+911800123004", "provider": "mock", "display_name": "Bangalore DID 1",
     "country_code": "IN", "number_type": "local", "can_voice": True, "can_sms": False},
    {"number": "+911800123005", "provider": "mock", "display_name": "Toll-Free 1",
     "country_code": "IN", "number_type": "toll_free", "can_voice": True, "can_sms": False},
]


async def seed_demo_numbers(db: AsyncIOMotorDatabase) -> list[PhoneNumber]:
    """Seed demo phone numbers for DEMO_MODE. Idempotent."""
    repo = PhoneNumberRepository(db)
    created = []
    for num_data in SEED_NUMBERS:
        existing = await repo.find_by_number(num_data["number"])
        if existing is None:
            pn = await repo.create(**num_data)
            created.append(pn)
    return created


def _to_customer_view(pn: PhoneNumber) -> dict:
    """Strip all provider details for customer-facing responses."""
    return {
        "id": pn.id,
        "number": pn.number,
        "display_name": pn.display_name,
        "country_code": pn.country_code,
        "number_type": pn.number_type,
        "can_voice": pn.can_voice,
        "can_sms": pn.can_sms,
        "can_whatsapp": pn.can_whatsapp,
        "status": pn.status,
        "organization_id": pn.organization_id,
        "assigned_at": pn.assigned_at.isoformat() if pn.assigned_at else None,
    }
    # NOTE: provider, provider_resource_id, provider_metadata, rental_paise_per_month
    # are deliberately omitted — customers must never see provider details.


def _to_admin_view(pn: PhoneNumber) -> dict:
    """Full view including provider details — admin only."""
    base = _to_customer_view(pn)
    base.update({
        "provider": pn.provider,
        "provider_resource_id": pn.provider_resource_id,
        "rental_paise_per_month": pn.rental_paise_per_month,
        "created_at": pn.created_at.isoformat(),
    })
    return base


class PhoneNumberService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.repo = PhoneNumberRepository(db)
        self.assignment_repo = PhoneNumberAssignmentRepository(db)

    # ---- Customer-facing ------------------------------------------------

    async def list_org_numbers(self, organization_id: str) -> list[dict]:
        """Numbers assigned to an org — no provider details."""
        numbers = await self.repo.list_for_org(organization_id)
        return [_to_customer_view(pn) for pn in numbers]

    async def get_number_for_org(
        self, phone_number_id: str, organization_id: str
    ) -> Optional[dict]:
        """Get a specific number only if it belongs to this org."""
        pn = await self.repo.find_by_id(phone_number_id)
        if pn is None or pn.organization_id != organization_id:
            return None
        return _to_customer_view(pn)

    # ---- Admin-facing ---------------------------------------------------

    async def add_to_inventory(
        self,
        number: str,
        provider: str,
        provider_resource_id: Optional[str] = None,
        display_name: Optional[str] = None,
        country_code: str = "IN",
        number_type: str = "local",
        can_voice: bool = True,
        can_sms: bool = False,
        can_whatsapp: bool = False,
        rental_paise_per_month: int = 0,
        provider_metadata: Optional[dict] = None,
    ) -> PhoneNumber:
        """Add a new number to the platform inventory."""
        existing = await self.repo.find_by_number(number)
        if existing:
            raise ValueError(f"Number {number} already in inventory")
        return await self.repo.create(
            number=number,
            provider=provider,
            provider_resource_id=provider_resource_id,
            display_name=display_name,
            country_code=country_code,
            number_type=number_type,
            can_voice=can_voice,
            can_sms=can_sms,
            can_whatsapp=can_whatsapp,
            rental_paise_per_month=rental_paise_per_month,
            provider_metadata=provider_metadata,
        )

    async def assign_to_org(
        self,
        phone_number_id: str,
        organization_id: str,
        performed_by: Optional[str] = None,
    ) -> dict:
        """
        Atomically assign an available number to an organization.
        Returns customer-safe view (no provider details).
        Raises if number is not available or already taken.
        """
        # Step 1: atomic reserve (concurrent-safe)
        reserved = await self.repo.atomic_reserve(phone_number_id)
        if reserved is None:
            # Number not available — check why
            pn = await self.repo.find_by_id(phone_number_id)
            if pn is None:
                raise ValueError(f"Phone number {phone_number_id} not found")
            raise ValueError(
                f"Number {pn.number} is not available (status: {pn.status})"
            )

        # Step 2: finalize assignment
        assigned = await self.repo.atomic_assign(phone_number_id, organization_id)
        if assigned is None:
            # Race condition — rare, but log it
            log.warning("assign: atomic_assign failed after reserve for id=%s", phone_number_id)
            raise RuntimeError("Assignment failed — please try again")

        # Audit record
        await self.assignment_repo.record(
            phone_number_id=phone_number_id,
            number=assigned.number,
            organization_id=organization_id,
            action="assigned",
            performed_by=performed_by,
            rental_paise_per_month=assigned.rental_paise_per_month,
        )

        log.info("number assigned id=%s number=%s org=%s",
                 phone_number_id, assigned.number, organization_id)
        return _to_customer_view(assigned)

    async def release_from_org(
        self,
        phone_number_id: str,
        performed_by: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> bool:
        """Return a number to the available pool."""
        pn = await self.repo.find_by_id(phone_number_id)
        if pn is None:
            raise ValueError(f"Phone number {phone_number_id} not found")
        if pn.status not in ("assigned", "suspended"):
            raise ValueError(f"Number cannot be released (status: {pn.status})")

        org_id = pn.organization_id
        ok = await self.repo.release(phone_number_id)
        if ok and org_id:
            await self.assignment_repo.record(
                phone_number_id=phone_number_id,
                number=pn.number,
                organization_id=org_id,
                action="released",
                performed_by=performed_by,
                notes=notes,
            )
        log.info("number released id=%s number=%s", phone_number_id, pn.number)
        return ok

    async def suspend_number(
        self,
        phone_number_id: str,
        performed_by: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> bool:
        pn = await self.repo.find_by_id(phone_number_id)
        if pn is None:
            raise ValueError(f"Phone number {phone_number_id} not found")
        ok = await self.repo.suspend(phone_number_id)
        if ok and pn.organization_id:
            await self.assignment_repo.record(
                phone_number_id=phone_number_id,
                number=pn.number,
                organization_id=pn.organization_id,
                action="suspended",
                performed_by=performed_by,
                notes=reason,
            )
        return ok

    async def reactivate_number(
        self,
        phone_number_id: str,
        performed_by: Optional[str] = None,
    ) -> bool:
        pn = await self.repo.find_by_id(phone_number_id)
        if pn is None:
            raise ValueError(f"Phone number {phone_number_id} not found")
        if pn.status != "suspended":
            raise ValueError(f"Number is not suspended (status: {pn.status})")
        ok = await self.repo.reactivate(phone_number_id)
        if ok and pn.organization_id:
            await self.assignment_repo.record(
                phone_number_id=phone_number_id,
                number=pn.number,
                organization_id=pn.organization_id,
                action="reactivated",
                performed_by=performed_by,
            )
        return ok

    async def list_available(
        self,
        country_code: Optional[str] = None,
        number_type: Optional[str] = None,
        limit: int = 50,
    ) -> list[dict]:
        """Available numbers — customer-safe view (no provider details)."""
        numbers = await self.repo.list_available(
            country_code=country_code,
            number_type=number_type,
            limit=limit,
        )
        return [_to_customer_view(pn) for pn in numbers]

    async def list_all_admin(
        self,
        status: Optional[str] = None,
        provider: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> list[dict]:
        """Full inventory view for platform admin — includes provider details."""
        numbers = await self.repo.list_all(
            status=status, provider=provider, limit=limit, skip=skip
        )
        return [_to_admin_view(pn) for pn in numbers]

    async def get_inventory_stats(self) -> dict:
        counts = await self.repo.count_by_status()
        return {
            "available": counts.get("available", 0),
            "assigned": counts.get("assigned", 0),
            "reserved": counts.get("reserved", 0),
            "suspended": counts.get("suspended", 0),
            "retired": counts.get("retired", 0),
            "total": sum(counts.values()),
        }
