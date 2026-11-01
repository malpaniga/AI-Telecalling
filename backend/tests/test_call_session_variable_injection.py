"""Tests for dynamic variable injection and template interpolation."""

import asyncio
import pytest
import mongomock_motor

from backend.agent.prompts import interpolate_template
from backend.telephony.vobiz import resolve_call_variables


def run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


class TestCallSessionVariableInjection:
    def setup_method(self):
        self.client = mongomock_motor.AsyncMongoMockClient()
        self.db = self.client["test_variable_injection"]

    def test_resolve_call_variables_hierarchy(self):
        async def _test():
            # Setup agent config, master lead, and campaign lead
            await self.db.agents.insert_one({"_id": "ag_1", "organization_id": "org_1"})
            await self.db.agent_versions.insert_one({
                "_id": "ver_1",
                "agent_id": "ag_1",
                "configuration": {
                    "system_prompt": "Hello {user_name}, your balance is {balance} in {city}.",
                    "greeting": "Hi {user_name} from {city}!",
                    "input_variables": {"balance": "0", "city": "Unknown"},
                },
            })
            await self.db.leads.insert_one({
                "_id": "lead_1",
                "organization_id": "org_1",
                "name": "Priya Patel",
                "phone": "+919876543210",
                "custom_fields": {"city": "Ahmedabad", "balance": "100"},
            })
            await self.db.campaign_leads.insert_one({
                "campaign_id": "camp_1",
                "lead_id": "lead_1",
                "custom_fields": {"balance": "12500"},  # Campaign override
            })
            await self.db.calls.insert_one({
                "_id": "call_1",
                "lead_id": "lead_1",
                "campaign_id": "camp_1",
                "agent_id": "ag_1",
            })

            variables = await resolve_call_variables(self.db, "call_1", "ag_1")
            assert variables["user_name"] == "Priya Patel"
            assert variables["name"] == "Priya Patel"
            assert variables["city"] == "Ahmedabad"
            assert variables["balance"] == "12500"  # Campaign override takes precedence over contact-level

        run(_test())

    def test_template_interpolation_greeting_and_prompt(self):
        variables = {
            "user_name": "Aarav Sharma",
            "city": "Delhi",
            "loan_amount": "50,000",
        }
        greeting = "Hello {user_name}! We have an offer of {loan_amount} in {city}."
        prompt = "You are assisting {user_name} located at {city}."

        interpolated_greeting = interpolate_template(greeting, variables)
        interpolated_prompt = interpolate_template(prompt, variables)

        assert interpolated_greeting == "Hello Aarav Sharma! We have an offer of 50,000 in Delhi."
        assert interpolated_prompt == "You are assisting Aarav Sharma located at Delhi."

    def test_resolve_call_variables_no_truth_value_testing(self):
        """Verify that PyMongo database objects that raise on bool(db) work cleanly."""
        class StrictDbWrapper:
            def __init__(self, inner):
                self._inner = inner
            def __bool__(self):
                raise NotImplementedError("Database objects do not implement truth value testing or bool()")
            def __getattr__(self, name):
                return getattr(self._inner, name)

        async def _test():
            await self.db.leads.insert_one({
                "_id": "lead_strict",
                "name": "Govind Sir",
                "phone": "+917249333373",
                "tags": ["VIP", "city:Washim"],
            })
            await self.db.calls.insert_one({
                "_id": "call_strict",
                "lead_id": "lead_strict",
            })
            strict_db = StrictDbWrapper(self.db)
            vars = await resolve_call_variables(strict_db, "call_strict")
            assert vars["name"] == "Govind Sir"
            assert vars["user_name"] == "Govind Sir"
            assert vars["phone"] == "+917249333373"
            assert vars["tags"] == "VIP, city:Washim"
            assert vars["city"] == "Washim"

        run(_test())
