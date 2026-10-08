"""M18 tests — Appointments.

Tests:
1.  Appointment model — valid statuses, duration validation, generic type field
2.  Status FSM — valid transitions allowed, invalid blocked
3.  AppointmentRepository — create, get_for_org (tenant isolation), list, upcoming
4.  AppointmentService.create — auto-populates lead info, updates lead status on call appt
5.  AppointmentService.confirm → confirmed
6.  AppointmentService.complete — with outcome notes
7.  AppointmentService.cancel — with reason
8.  AppointmentService.mark_no_show
9.  AppointmentService.reschedule — old marked rescheduled, new created
10. Invalid transitions raise ValueError
11. Tenant isolation — Org A cannot access Org B appointments
12. dashboard_summary returns correct counts + upcoming list
13. list with filters (status, type, lead_id)
14. HTTP: create, list, get, confirm, complete, cancel, reschedule, summary, upcoming
15. HTTP: tenant isolation 404
"""

import asyncio
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _mongomock_available():
    try:
        import mongomock_motor
        return True
    except ImportError:
        return False


SKIP = pytest.mark.skipif(not _mongomock_available(), reason="mongomock_motor not installed")


def _get_mock_db():
    import mongomock_motor
    return mongomock_motor.AsyncMongoMockClient()["test"]


def _future_dt(days: int = 7) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=days)


# ---------------------------------------------------------------------------
# Test: Model
# ---------------------------------------------------------------------------
class TestAppointmentModel:
    def test_default_status(self):
        from backend.models.appointment import Appointment
        from backend.models.base import new_id
        a = Appointment(_id=new_id(), organization_id="o",
                        scheduled_at=_future_dt())
        assert a.status == "scheduled"
        assert a.appointment_type == "general"
        assert a.duration_minutes == 30

    def test_all_valid_statuses(self):
        from backend.models.appointment import Appointment, APPOINTMENT_STATUSES
        from backend.models.base import new_id
        for s in APPOINTMENT_STATUSES:
            a = Appointment(_id=new_id(), organization_id="o",
                            scheduled_at=_future_dt(), status=s)
            assert a.status == s

    def test_invalid_status_raises(self):
        from backend.models.appointment import Appointment
        from backend.models.base import new_id
        with pytest.raises(Exception):
            Appointment(_id=new_id(), organization_id="o",
                        scheduled_at=_future_dt(), status="bad_status")

    def test_zero_duration_raises(self):
        from backend.models.appointment import Appointment
        from backend.models.base import new_id
        with pytest.raises(Exception):
            Appointment(_id=new_id(), organization_id="o",
                        scheduled_at=_future_dt(), duration_minutes=0)

    def test_appointment_type_is_generic(self):
        from backend.models.appointment import Appointment
        from backend.models.base import new_id
        for t in ["site_survey", "property_viewing", "demo", "consultation",
                  "delivery", "general", "follow_up"]:
            a = Appointment(_id=new_id(), organization_id="o",
                            scheduled_at=_future_dt(), appointment_type=t)
            assert a.appointment_type == t


# ---------------------------------------------------------------------------
# Test: Repository
# ---------------------------------------------------------------------------
@SKIP
class TestAppointmentRepository:
    def setup_method(self):
        self.db = _get_mock_db()

    def test_create_and_find(self):
        from backend.repositories.appointment_repo import AppointmentRepository
        repo = AppointmentRepository(self.db)
        async def _t():
            a = await repo.create("org-1", _future_dt(), appointment_type="site_survey")
            assert a.id is not None
            assert a.status == "scheduled"
            found = await repo.find_by_id(a.id)
            assert found.appointment_type == "site_survey"
        run(_t())

    def test_get_for_org_tenant_isolation(self):
        from backend.repositories.appointment_repo import AppointmentRepository
        repo = AppointmentRepository(self.db)
        async def _t():
            a = await repo.create("org-A", _future_dt())
            assert await repo.get_for_org(a.id, "org-A") is not None
            assert await repo.get_for_org(a.id, "org-B") is None
        run(_t())

    def test_list_for_org_scoped(self):
        from backend.repositories.appointment_repo import AppointmentRepository
        repo = AppointmentRepository(self.db)
        async def _t():
            await repo.create("org-X", _future_dt(3), appointment_type="demo")
            await repo.create("org-X", _future_dt(5), appointment_type="site_survey")
            await repo.create("org-Y", _future_dt(2), appointment_type="demo")
            ax = await repo.list_for_org("org-X")
            ay = await repo.list_for_org("org-Y")
            assert len(ax) == 2
            assert len(ay) == 1
            assert all(a.organization_id == "org-X" for a in ax)
        run(_t())

    def test_list_upcoming(self):
        from backend.repositories.appointment_repo import AppointmentRepository
        repo = AppointmentRepository(self.db)
        async def _t():
            await repo.create("org-up", _future_dt(1))
            await repo.create("org-up", _future_dt(3))
            # Past appointment (status=scheduled but in past — would not show in upcoming)
            past = await repo.create("org-up", _future_dt(-1))
            upcoming = await repo.list_upcoming("org-up")
            # Past appointment should NOT appear in upcoming
            upcoming_ids = {a.id for a in upcoming}
            assert past.id not in upcoming_ids
            assert len(upcoming) == 2
        run(_t())

    def test_transition_status(self):
        from backend.repositories.appointment_repo import AppointmentRepository
        repo = AppointmentRepository(self.db)
        async def _t():
            a = await repo.create("org-1", _future_dt())
            ok = await repo.transition_status(a.id, "org-1", "confirmed")
            assert ok
            updated = await repo.find_by_id(a.id)
            assert updated.status == "confirmed"
        run(_t())

    def test_transition_wrong_org_fails(self):
        from backend.repositories.appointment_repo import AppointmentRepository
        repo = AppointmentRepository(self.db)
        async def _t():
            a = await repo.create("org-owner", _future_dt())
            ok = await repo.transition_status(a.id, "org-other", "confirmed")
            assert not ok   # tenant isolation
            unchanged = await repo.find_by_id(a.id)
            assert unchanged.status == "scheduled"
        run(_t())


# ---------------------------------------------------------------------------
# Test: Service — lifecycle
# ---------------------------------------------------------------------------
@SKIP
class TestAppointmentService:
    def setup_method(self):
        self.db = _get_mock_db()

    def _svc(self):
        from backend.services.appointment_service import AppointmentService
        return AppointmentService(self.db)

    def test_create_basic(self):
        async def _t():
            svc = self._svc()
            a = await svc.create("org-1", _future_dt(), appointment_type="demo")
            assert a.status == "scheduled"
            assert a.appointment_type == "demo"
        run(_t())

    def test_create_with_lead_populates_info(self):
        async def _t():
            # Insert a lead first
            await self.db["leads"].insert_one({
                "_id": "lead-appt-1", "organization_id": "org-2",
                "phone": "+919001000001", "name": "Alice", "email": "alice@test.com",
                "status": "new",
            })
            svc = self._svc()
            a = await svc.create("org-2", _future_dt(), lead_id="lead-appt-1")
            assert a.lead_name == "Alice"
            assert a.lead_phone == "+919001000001"
            assert a.lead_email == "alice@test.com"
        run(_t())

    def test_create_with_lead_wrong_org_raises(self):
        async def _t():
            await self.db["leads"].insert_one({
                "_id": "lead-wrong-org", "organization_id": "org-owner",
                "phone": "+919001000002", "name": "Bob",
            })
            svc = self._svc()
            with pytest.raises(ValueError, match="[Nn]ot found"):
                await svc.create("org-other", _future_dt(), lead_id="lead-wrong-org")
        run(_t())

    def test_confirm(self):
        async def _t():
            svc = self._svc()
            a = await svc.create("org-1", _future_dt())
            confirmed = await svc.confirm(a.id, "org-1")
            assert confirmed.status == "confirmed"
        run(_t())

    def test_complete_with_outcome(self):
        async def _t():
            svc = self._svc()
            a = await svc.create("org-1", _future_dt())
            await svc.confirm(a.id, "org-1")
            completed = await svc.complete(a.id, "org-1",
                                           outcome_notes="Deal signed!")
            assert completed.status == "completed"
            assert completed.outcome_notes == "Deal signed!"
        run(_t())

    def test_cancel(self):
        async def _t():
            svc = self._svc()
            a = await svc.create("org-1", _future_dt())
            cancelled = await svc.cancel(a.id, "org-1", reason="Lead declined")
            assert cancelled.status == "cancelled"
        run(_t())

    def test_mark_no_show_from_confirmed(self):
        async def _t():
            svc = self._svc()
            a = await svc.create("org-1", _future_dt())
            await svc.confirm(a.id, "org-1")
            ns = await svc.mark_no_show(a.id, "org-1")
            assert ns.status == "no_show"
        run(_t())

    def test_reschedule_creates_new_and_marks_old(self):
        async def _t():
            svc = self._svc()
            a = await svc.create("org-1", _future_dt(3), appointment_type="site_survey")
            new_a = await svc.reschedule(a.id, "org-1", _future_dt(10))
            # Old is rescheduled
            old = await svc.get(a.id, "org-1")
            assert old.status == "rescheduled"
            # New is scheduled with same type
            assert new_a.status == "scheduled"
            assert new_a.appointment_type == "site_survey"
            # New has different ID
            assert new_a.id != a.id
        run(_t())

    def test_invalid_transition_raises(self):
        async def _t():
            svc = self._svc()
            a = await svc.create("org-1", _future_dt())
            # Cannot complete from scheduled (need to confirm first)
            with pytest.raises(ValueError, match="[Cc]annot transition"):
                await svc.complete(a.id, "org-1")
        run(_t())

    def test_terminal_state_no_transitions(self):
        async def _t():
            svc = self._svc()
            a = await svc.create("org-1", _future_dt())
            await svc.confirm(a.id, "org-1")
            await svc.complete(a.id, "org-1")
            # completed is terminal
            with pytest.raises(ValueError):
                await svc.cancel(a.id, "org-1")
        run(_t())

    def test_tenant_isolation_get(self):
        async def _t():
            svc = self._svc()
            a = await svc.create("org-A", _future_dt())
            assert await svc.get(a.id, "org-A") is not None
            assert await svc.get(a.id, "org-B") is None
        run(_t())

    def test_dashboard_summary(self):
        async def _t():
            svc = self._svc()
            await svc.create("org-dash", _future_dt(1))
            await svc.create("org-dash", _future_dt(2))
            a3 = await svc.create("org-dash", _future_dt(3))
            await svc.confirm(a3.id, "org-dash")
            await svc.complete(a3.id, "org-dash")

            summary = await svc.dashboard_summary("org-dash")
            assert summary["total"] == 3
            assert summary["scheduled"] == 2
            assert summary["completed"] == 1
            assert "upcoming" in summary
        run(_t())

    def test_list_with_status_filter(self):
        async def _t():
            svc = self._svc()
            await svc.create("org-flt", _future_dt(1), appointment_type="demo")
            a2 = await svc.create("org-flt", _future_dt(2), appointment_type="site_survey")
            await svc.confirm(a2.id, "org-flt")

            scheduled = await svc.list("org-flt", status="scheduled")
            confirmed = await svc.list("org-flt", status="confirmed")
            assert len(scheduled) == 1
            assert len(confirmed) == 1
            assert all(a.status == "scheduled" for a in scheduled)
            assert all(a.status == "confirmed" for a in confirmed)
        run(_t())

    def test_list_with_type_filter(self):
        async def _t():
            svc = self._svc()
            await svc.create("org-typ", _future_dt(1), appointment_type="demo")
            await svc.create("org-typ", _future_dt(2), appointment_type="site_survey")
            await svc.create("org-typ", _future_dt(3), appointment_type="demo")

            demos = await svc.list("org-typ", appointment_type="demo")
            surveys = await svc.list("org-typ", appointment_type="site_survey")
            assert len(demos) == 2
            assert len(surveys) == 1
        run(_t())


# ---------------------------------------------------------------------------
# Test: HTTP endpoints
# ---------------------------------------------------------------------------
@SKIP
class TestAppointmentsHTTP:
    def setup_method(self):
        import mongomock_motor
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from backend.api.v1.auth import router as auth_router
        from backend.api.v1.appointments import router as appts_router
        from backend.core import db as db_module, redis as redis_module

        self.test_app = FastAPI()
        self.test_app.include_router(auth_router, prefix="/api/v1")
        self.test_app.include_router(appts_router, prefix="/api/v1")

        client = mongomock_motor.AsyncMongoMockClient()
        self.mock_db = client["test"]
        db_module._db = self.mock_db

        mock_redis = MagicMock()
        mock_redis.set = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)
        redis_module._redis = mock_redis

        self.client = TestClient(self.test_app)

        # Two orgs
        r1 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Appt Org",
            "org_email": "appt@org.com",
            "email": "user@appt.com",
            "password": "ApptPass1!",
        })
        self.token_a = r1.json()["access_token"]
        self.org_id_a = r1.json()["organization_id"]

        r2 = self.client.post("/api/v1/auth/signup", json={
            "org_name": "Other Appt",
            "org_email": "other5@org.com",
            "email": "user@other5.com",
            "password": "Other5Pass1!",
        })
        self.token_b = r2.json()["access_token"]

    def _auth(self, t): return {"Authorization": f"Bearer {t}"}

    def _create_body(self, **kwargs):
        base = {
            "scheduled_at": _future_dt(7).isoformat(),
            "appointment_type": "demo",
            "duration_minutes": 30,
        }
        return {**base, **kwargs}

    def test_create_appointment(self):
        resp = self.client.post("/api/v1/appointments",
                                json=self._create_body(),
                                headers=self._auth(self.token_a))
        assert resp.status_code == 201, resp.text
        data = resp.json()
        assert data["status"] == "scheduled"
        assert data["appointment_type"] == "demo"
        assert data["organization_id"] == self.org_id_a

    def test_list_appointments(self):
        self.client.post("/api/v1/appointments", json=self._create_body(),
                         headers=self._auth(self.token_a))
        resp = self.client.get("/api/v1/appointments",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_appointment(self):
        r = self.client.post("/api/v1/appointments", json=self._create_body(),
                             headers=self._auth(self.token_a))
        aid = r.json()["id"]
        resp = self.client.get(f"/api/v1/appointments/{aid}",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert resp.json()["id"] == aid

    def test_tenant_isolation_get(self):
        r = self.client.post("/api/v1/appointments", json=self._create_body(),
                             headers=self._auth(self.token_a))
        aid = r.json()["id"]
        resp = self.client.get(f"/api/v1/appointments/{aid}",
                               headers=self._auth(self.token_b))
        assert resp.status_code == 404

    def test_confirm_appointment(self):
        r = self.client.post("/api/v1/appointments", json=self._create_body(),
                             headers=self._auth(self.token_a))
        aid = r.json()["id"]
        resp = self.client.post(f"/api/v1/appointments/{aid}/confirm",
                                headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert resp.json()["status"] == "confirmed"

    def test_complete_appointment(self):
        r = self.client.post("/api/v1/appointments", json=self._create_body(),
                             headers=self._auth(self.token_a))
        aid = r.json()["id"]
        self.client.post(f"/api/v1/appointments/{aid}/confirm",
                         headers=self._auth(self.token_a))
        resp = self.client.post(f"/api/v1/appointments/{aid}/complete",
                                json={"outcome_notes": "Signed up!"},
                                headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"
        assert resp.json()["outcome_notes"] == "Signed up!"

    def test_cancel_appointment(self):
        r = self.client.post("/api/v1/appointments", json=self._create_body(),
                             headers=self._auth(self.token_a))
        aid = r.json()["id"]
        resp = self.client.post(f"/api/v1/appointments/{aid}/cancel",
                                json={"reason": "Lead unavailable"},
                                headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    def test_invalid_transition_returns_400(self):
        r = self.client.post("/api/v1/appointments", json=self._create_body(),
                             headers=self._auth(self.token_a))
        aid = r.json()["id"]
        # Cannot complete from scheduled directly
        resp = self.client.post(f"/api/v1/appointments/{aid}/complete",
                                json={},
                                headers=self._auth(self.token_a))
        assert resp.status_code == 400

    def test_reschedule_appointment(self):
        r = self.client.post("/api/v1/appointments", json=self._create_body(),
                             headers=self._auth(self.token_a))
        aid = r.json()["id"]
        new_dt = _future_dt(14).isoformat()
        resp = self.client.post(f"/api/v1/appointments/{aid}/reschedule",
                                json={"scheduled_at": new_dt},
                                headers=self._auth(self.token_a))
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "scheduled"
        assert data["id"] != aid   # new appointment created

    def test_summary_endpoint(self):
        self.client.post("/api/v1/appointments", json=self._create_body(),
                         headers=self._auth(self.token_a))
        resp = self.client.get("/api/v1/appointments/summary",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "by_status" in data
        assert "upcoming" in data

    def test_upcoming_endpoint(self):
        self.client.post("/api/v1/appointments", json=self._create_body(),
                         headers=self._auth(self.token_a))
        resp = self.client.get("/api/v1/appointments/upcoming",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_filter_by_status(self):
        self.client.post("/api/v1/appointments", json=self._create_body(),
                         headers=self._auth(self.token_a))
        resp = self.client.get("/api/v1/appointments?appt_status=scheduled",
                               headers=self._auth(self.token_a))
        assert resp.status_code == 200
        for a in resp.json():
            assert a["status"] == "scheduled"

    def test_unauthenticated_rejected(self):
        resp = self.client.get("/api/v1/appointments")
        assert resp.status_code == 401

    def test_no_show_appointment(self):
        r = self.client.post("/api/v1/appointments", json=self._create_body(),
                             headers=self._auth(self.token_a))
        aid = r.json()["id"]
        # Confirm first, then no-show
        self.client.post(f"/api/v1/appointments/{aid}/confirm",
                         headers=self._auth(self.token_a))
        resp = self.client.post(f"/api/v1/appointments/{aid}/no-show",
                                headers=self._auth(self.token_a))
        assert resp.status_code == 200
        assert resp.json()["status"] == "no_show"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
