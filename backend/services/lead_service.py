"""Lead CRM service — import pipeline and CRUD.

Import pipeline:
  1. Parse file (CSV / XLSX / JSON)
  2. Apply column mapping  (source_col → standard_field)
  3. Validate each row     (phone required, status valid, etc.)
  4. Normalize phone numbers
  5. DNC check             (filter out org's DNC numbers)
  6. Deduplicate           (skip phones already in org)
  7. Bulk insert
  8. Return import report  {imported, skipped_dnc, skipped_duplicate, errors}

Phone normalization:
  - Strip spaces, dashes, parentheses
  - If 10-digit Indian number without country code, prefix +91
  - E.164 format preferred

Designed for 4000+ leads — uses bulk_insert (not one-by-one).
"""

import io
import logging
import re
from datetime import datetime
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.base import new_id, utcnow
from backend.models.lead import Lead, LEAD_STATUSES
from backend.repositories.lead_repo import DNCRepository, LeadRepository
from backend.repositories.campaign_lead_repo import CampaignLeadRepository

log = logging.getLogger("service.lead")

# Standard field names for the import pipeline
STANDARD_FIELDS = {
    "phone", "name", "email", "status", "tags", "source",
    "next_contact_at",
}
NAME_ALIASES = {"user_name", "customer_name", "contact_name", "lead_name", "full_name"}

# Required fields for a valid lead
REQUIRED_FIELDS = {"phone"}


def normalize_phone(raw: str) -> str:
    """Normalize a phone number to E.164 (best-effort for Indian numbers)."""
    # Remove all non-digit characters except leading +
    cleaned = re.sub(r"[^\d+]", "", raw.strip())
    if not cleaned:
        return ""
    # Already E.164
    if cleaned.startswith("+"):
        return cleaned
    # 10-digit Indian mobile
    if len(cleaned) == 10 and cleaned[0] in "6789":
        return f"+91{cleaned}"
    # 12-digit with country code (no +)
    if len(cleaned) == 12 and cleaned.startswith("91"):
        return f"+{cleaned}"
    # Return as-is if we can't normalize
    return cleaned if cleaned else raw.strip()


def _parse_csv(content: bytes) -> tuple[list[str], list[list[str]]]:
    """Parse CSV bytes → (headers, rows)."""
    import csv
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text))
    rows = list(reader)
    if not rows:
        return [], []
    return rows[0], rows[1:]


def _parse_xlsx(content: bytes) -> tuple[list[str], list[list[Any]]]:
    """Parse XLSX bytes → (headers, rows)."""
    import openpyxl
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    wb.close()
    if not all_rows:
        return [], []
    headers = [str(h) if h is not None else "" for h in all_rows[0]]
    data = [[str(c) if c is not None else "" for c in row] for row in all_rows[1:]]
    return headers, data


def _parse_json(content: bytes) -> tuple[list[str], list[dict]]:
    """Parse JSON bytes → (headers derived from keys, rows as dicts)."""
    import json
    data = json.loads(content.decode("utf-8"))
    if not isinstance(data, list):
        raise ValueError("JSON must be a list of objects")
    if not data:
        return [], []
    headers = list(data[0].keys())
    return headers, data


def _apply_mapping(
    headers: list[str],
    rows: list,
    column_mapping: Optional[dict[str, str]] = None,
) -> list[dict[str, Any]]:
    """Apply column mapping to raw rows → list of dicts with standard and custom field names.

    column_mapping: {source_col_name: target_field_name}
    If no mapping provided, auto-map by matching header names case-insensitively.
    """
    mapping = dict(column_mapping or {})

    # Auto-map: try to match standard fields by name
    if not mapping:
        for h in headers:
            normalized = h.strip().lower().replace(" ", "_").replace("-", "_")
            if normalized in STANDARD_FIELDS:
                mapping[h] = normalized
            # Common aliases
            elif normalized in ("mobile", "mobile_number", "phone_number", "contact"):
                mapping[h] = "phone"
            elif normalized in ("full_name", "customer_name", "contact_name", "lead_name", "user_name"):
                mapping[h] = "name"
            elif normalized in ("email_address", "mail"):
                mapping[h] = "email"

    result = []
    for row in rows:
        record: dict[str, Any] = {}
        items = (
            row.items()
            if isinstance(row, dict)
            else [(headers[i], row[i]) for i in range(min(len(headers), len(row)))]
        )

        for src_key, raw_val in items:
            str_val = str(raw_val).strip() if raw_val is not None else ""
            target = mapping.get(src_key)

            if target:
                norm_target = target.strip().lower().replace(" ", "_")
                if norm_target in STANDARD_FIELDS:
                    record[norm_target] = str_val
                    record.setdefault("_custom", {})[norm_target] = str_val
                    if norm_target == "name":
                        record.setdefault("_custom", {})["user_name"] = str_val
                elif norm_target in NAME_ALIASES:
                    record.setdefault("name", str_val)
                    record.setdefault("_custom", {})[norm_target] = str_val
                    record.setdefault("_custom", {})["name"] = str_val
                    record.setdefault("_custom", {})["user_name"] = str_val
                else:
                    # Custom variable (e.g. city, address, due_amount)
                    record.setdefault("_custom", {})[norm_target] = str_val
                    record.setdefault("_custom", {})[src_key] = str_val
            else:
                # Unmapped field stored under original header
                record.setdefault("_custom", {})[src_key] = raw_val

        # Ensure name is mirrored in custom fields
        if record.get("name"):
            record.setdefault("_custom", {})["name"] = record["name"]
            record.setdefault("_custom", {})["user_name"] = record["name"]

        result.append(record)
    return result


class LeadService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.lead_repo = LeadRepository(db)
        self.dnc_repo = DNCRepository(db)

    # ---- CRUD ----

    async def create_lead(
        self,
        organization_id: str,
        phone: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        custom_fields: Optional[dict] = None,
        tags: Optional[list] = None,
        source: str = "manual",
    ) -> Lead:
        phone = normalize_phone(phone)
        if not phone:
            raise ValueError("phone is required")
        # Check DNC
        if await self.dnc_repo.is_dnc(organization_id, phone):
            raise ValueError(f"Phone {phone} is on the DNC list")
        # Check duplicate
        existing = await self.lead_repo.find_by_phone_org(phone, organization_id)
        if existing:
            raise ValueError(f"Lead with phone {phone} already exists")
        return await self.lead_repo.create(
            organization_id=organization_id,
            phone=phone,
            name=name,
            email=email,
            custom_fields=custom_fields,
            tags=tags,
            source=source,
        )

    async def get_lead(
        self, lead_id: str, organization_id: str
    ) -> Optional[Lead]:
        lead = await self.lead_repo.find_by_id(lead_id)
        if lead is None or lead.organization_id != organization_id:
            return None
        return lead

    async def list_leads(
        self,
        organization_id: str,
        campaign_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        skip: int = 0,
    ) -> tuple[list[Lead], int]:
        leads = await self.lead_repo.list_for_org(
            organization_id, campaign_id=campaign_id,
            status=status, limit=limit, skip=skip,
        )
        total = await self.lead_repo.count_for_org(organization_id, campaign_id)
        return leads, total

    async def update_lead(
        self,
        lead_id: str,
        organization_id: str,
        updates: dict[str, Any],
    ) -> Optional[Lead]:
        lead = await self.get_lead(lead_id, organization_id)
        if lead is None:
            return None
        # Strip fields that should not be directly updated
        safe = {k: v for k, v in updates.items()
                if k not in ("organization_id", "_id")}
        await self.lead_repo.update_by_id(lead_id, safe)
        return await self.lead_repo.find_by_id(lead_id)

    async def delete_lead(
        self, lead_id: str, organization_id: str
    ) -> bool:
        return await self.lead_repo.delete_for_org(lead_id, organization_id)

    # ---- DNC ----

    async def add_to_dnc(
        self,
        organization_id: str,
        phone: str,
        reason: Optional[str] = None,
        added_by: Optional[str] = None,
        source: str = "manual",
    ) -> bool:
        phone = normalize_phone(phone)
        entry = await self.dnc_repo.add(
            organization_id, phone, reason, added_by, source
        )
        if entry:
            # Update lead status to dnc
            lead = await self.lead_repo.find_by_phone_org(phone, organization_id)
            if lead:
                await self.lead_repo.update_status(lead.id, organization_id, "dnc")
        return entry is not None

    async def check_dnc(self, organization_id: str, phone: str) -> bool:
        return await self.dnc_repo.is_dnc(organization_id, normalize_phone(phone))

    # ---- Import pipeline ----

    async def import_leads(
        self,
        organization_id: str,
        content: bytes,
        file_format: str,                       # "csv" | "xlsx" | "json"
        column_mapping: Optional[dict] = None,
        campaign_id: Optional[str] = None,
        source: str = "import",
        tags: Optional[list] = None,
    ) -> dict:
        """
        Full import pipeline. Returns:
        {
          imported: int,
          skipped_dnc: int,
          skipped_duplicate: int,
          skipped_invalid: int,
          errors: [{row, phone, error}],
          total_rows: int,
          batch_id: str,
        }
        """
        batch_id = new_id()

        # 1. Parse
        try:
            fmt = file_format.lower()
            if fmt == "csv":
                headers, rows = _parse_csv(content)
            elif fmt == "xlsx":
                headers, rows = _parse_xlsx(content)
            elif fmt == "json":
                headers, raw_dicts = _parse_json(content)
                rows = raw_dicts
            else:
                raise ValueError(f"Unsupported format: {file_format}")
        except Exception as exc:
            return {
                "imported": 0, "skipped_dnc": 0, "skipped_duplicate": 0,
                "skipped_invalid": 0, "errors": [{"row": None, "error": str(exc)}],
                "total_rows": 0, "batch_id": batch_id,
            }

        total_rows = len(rows)
        log.info("import_leads org=%s format=%s rows=%d batch=%s",
                 organization_id, fmt, total_rows, batch_id)

        # 2. Apply column mapping
        if fmt == "json":
            mapped_rows = _apply_mapping(headers, rows, column_mapping)
        else:
            mapped_rows = _apply_mapping(headers, rows, column_mapping)

        # 3. Validate + normalize
        valid_docs = []
        validation_errors = []
        raw_phones = []

        for i, row in enumerate(mapped_rows):
            row_num = i + 2  # 1-indexed, skip header
            phone_raw = row.get("phone", "").strip()
            if not phone_raw:
                validation_errors.append({
                    "row": row_num, "phone": "",
                    "error": "phone is required",
                })
                continue
            phone = normalize_phone(phone_raw)
            if not phone:
                validation_errors.append({
                    "row": row_num, "phone": phone_raw,
                    "error": f"Could not normalize phone: {phone_raw}",
                })
                continue
            raw_phones.append(phone)
            valid_docs.append({
                "_id": new_id(),
                "organization_id": organization_id,
                "phone": phone,
                "name": row.get("name") or None,
                "email": row.get("email") or None,
                "campaign_id": campaign_id,
                "status": "new",
                "score": 0,
                "qualification": {},
                "custom_fields": row.get("_custom", {}),
                "tags": tags or [],
                "source": source,
                "attempts": 0,
                "import_batch_id": batch_id,
                "original_row": row_num,
                "created_at": utcnow(),
                "updated_at": utcnow(),
            })

        if not valid_docs:
            return {
                "imported": 0, "skipped_dnc": 0, "skipped_duplicate": 0,
                "skipped_invalid": len(validation_errors),
                "errors": validation_errors,
                "total_rows": total_rows, "batch_id": batch_id,
            }

        # 4. DNC filter
        dnc_phones = await self.dnc_repo.bulk_check(organization_id, raw_phones)
        pre_dnc_count = len(valid_docs)
        valid_docs = [d for d in valid_docs if d["phone"] not in dnc_phones]
        skipped_dnc = pre_dnc_count - len(valid_docs)

        # 5. Partition into new vs existing contacts (upsert)
        cursor = self.db["leads"].find(
            {
                "organization_id": organization_id,
                "phone": {"$in": [d["phone"] for d in valid_docs]},
            }
        )
        existing_list = await cursor.to_list(length=len(valid_docs))
        existing_by_phone = {d["phone"]: d for d in existing_list}

        new_docs = []
        updated_docs = []
        campaign_items = []

        now = utcnow()
        for d in valid_docs:
            phone = d["phone"]
            custom_data = d.get("custom_fields", {})
            if phone in existing_by_phone:
                existing = existing_by_phone[phone]
                lead_id = str(existing["_id"])

                merged_custom = dict(existing.get("custom_fields") or {})
                merged_custom.update(custom_data)

                updates: dict[str, Any] = {
                    "custom_fields": merged_custom,
                    "updated_at": now,
                }
                if d.get("name"):
                    updates["name"] = d["name"]
                if d.get("email"):
                    updates["email"] = d["email"]
                if tags:
                    existing_tags = set(existing.get("tags") or [])
                    existing_tags.update(tags)
                    updates["tags"] = list(existing_tags)

                await self.db["leads"].update_one(
                    {"_id": existing["_id"]},
                    {"$set": updates},
                )
                updated_docs.append(existing)
            else:
                lead_id = d["_id"]
                new_docs.append(d)

            if campaign_id:
                campaign_items.append({
                    "lead_id": lead_id,
                    "phone": phone,
                    "custom_fields": custom_data,
                })

        inserted_count = 0
        if new_docs:
            result = await self.lead_repo.bulk_insert(new_docs, organization_id)
            inserted_count = result["inserted"]

        # 6. Campaign enrollment vs Standalone contact import
        if campaign_id:
            camp_lead_repo = CampaignLeadRepository(self.db)
            enroll_res = await camp_lead_repo.bulk_enroll(campaign_id, organization_id, campaign_items)
            total_imported = enroll_res["enrolled"]
            skipped_dup = enroll_res["skipped"]
        else:
            total_imported = inserted_count
            skipped_dup = len(updated_docs)

        return {
            "imported": total_imported,
            "skipped_dnc": skipped_dnc,
            "skipped_duplicate": skipped_dup,
            "skipped_invalid": len(validation_errors),
            "errors": validation_errors,
            "total_rows": total_rows,
            "batch_id": batch_id,
        }
