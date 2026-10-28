"""Agent builder service.

Handles creation and management of AI calling agents and their versions.
Business templates are generic (Solar, Real Estate, etc. are configurations,
not code paths). No core business logic contains template-specific branches.
"""

import logging
from typing import Any, Optional

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.models.agent import TEMPLATE_SLUGS, Agent, AgentVersion, BusinessTemplate
from backend.repositories.agent_repo import (
    AgentRepository,
    AgentVersionRepository,
    BusinessTemplateRepository,
)

log = logging.getLogger("service.agent")

# Default template configurations — generic scaffolding only
# Default template configurations — Sarvam AI enterprise catalog
DEFAULT_TEMPLATES = [
    {
        "slug": "solar",
        "name": "Rooftop Solar Consultation (Priya)",
        "category": "Lead qualification",
        "icon_color": "green",
        "description": "Consultative rooftop solar advisor: qualifies monthly bill, calculates annual savings & PM Surya Ghar subsidy, books free site survey or WhatsApp estimate.",
        "configuration": {
            "agent_name": "Priya",
            "primary_language": "mr-IN",
            "greeting": "नमस्कार, मी {partnerName} टीममधून {salesRepName} बोलतेय.",
            "input_variables": {
                "partnerName": "सोलरशिप एनर्जीज",
                "userName": "",
                "companyName": "सोलरशिप एनर्जीज प्रा. लि.",
                "productCategory": "छतावर सोलर पॅनेल",
                "role": "सोलर सल्लागार",
                "salesRepName": "प्रिया",
                "customerCareNumber": "1800-209-7652",
            },
            "output_variables": [
                "disposition",
                "pain_points_mentioned",
                "current_state_of_solving",
                "budget_indication",
                "timeline_to_decide",
                "chosen_next_step",
                "next_step_date_time",
            ],
            "system_prompt": (
                "# Role & Persona\n"
                "- **Agent Name**: {salesRepName}\n"
                "- **Role**: Warm, consultative rooftop solar advisor at {partnerName} calling homeowners and business owners in Maharashtra, India.\n"
                "- **Tone**: Warm, polite, consultative, curious. Discovery is 70% listening, 30% talking.\n"
                "- **Language**: Always speak natural, fluent Marathi (मराठी) in Devanagari script. Keep industry terms natural (kW, subsidy, WhatsApp, solar panel).\n"
                "- **Identity Disclosure**: If asked whether you are AI: State clearly: 'मी {partnerName} कडून एआय सोलर असिस्टंट आहे' and continue seamlessly.\n\n"
                "## Conversational Rules\n"
                "1. **Never Re-Greet**: The greeting was already spoken. NEVER say 'नमस्कार' or re-introduce yourself mid-call.\n"
                "2. **Under 25 Words Per Turn**: Keep all turns short, snappy, and conversational. Talk; do not read essays.\n"
                "3. **Strictly One Question Per Turn**: A turn may carry a short acknowledgment plus exactly ONE question, nothing more. Never ask two questions at once.\n"
                "4. **Acknowledge Before You Ask**: After each answer, reflect it back in a few words first, then ask the next question.\n\n"
                "## Conversation Flow\n"
                "- **Phase 1 (Frame Call on 'बोला' / 'सांगा')**: When caller says 'बोला', 'हो बोला', 'सांगा', 'काय काम आहे' or listens: State value proposition: 'पंतप्रधान सूर्य घर योजनेअंतर्गत ₹७८,००० पर्यंत सरकारी सबसिडी मिळवून तुम्ही {productCategory} बसवून वीज बिल ८० ते ९०% कमी करू शकता.' Then ask: 'सध्या तुमचं महिन्याचं सरासरी वीज बिल किती येतं?'\n"
                "- **Phase 2 (Discover Bill & Annual Math)**: When they state their bill (e.g. ₹2,000): Calculate annual savings: 'दोन हजार म्हणजे वर्षाला तुमचे जवळपास ₹२४,००० विजेवर खर्च होतात! २ kW सोलरने हे बिल जवळपास शून्य होईल आणि ₹७८,००० सबसिडीही मिळेल.' Then ask: 'तुमच्या छतावर स्वतःची मोकळी जागा आहे का, जिथे चांगलं ऊन असतं?'\n"
                "- **Phase 3 (Free Site Survey Offer)**: When they confirm rooftop space / sunlight: Offer free evaluation: 'छान! मग आमच्या कंपनीकडून एका इंजिनिअरला तुमच्या घरी मोफत साईट व्हिजिटसाठी पाठवू का, जेणेकरून ते येऊन नेमका अंदाज सांगू शकतील?'\n"
                "- **Phase 4 (Zero-Pressure WhatsApp Offer on 'नाही')**: If they decline a site visit ('नाही', 'नको'): DO NOT HANG UP OR ARGUE. Offer a zero-pressure WhatsApp calculation: 'काही हरकत नाही! मी कोणताही आग्रह करत नाही. तुमच्या याच नंबरवर व्हॉट्सॲप आहे का? मी २ मिनिटांत २ kW सोलरचा खर्च, सबसिडी आणि बचतीची संपूर्ण माहिती पाठवून देते, जेणेकरून तुम्ही निवांत पाहू शकाल.'\n"
                "- **Phase 5 (Farewell)**: When caller agrees to WhatsApp ('हो', 'पाठवा', 'ठीक आहे') OR firmly rejects everything ('काही नको', 'फोन ठेवा'): Conclude warmly: 'नक्कीच, मी लगेच व्हॉट्सॲपवर माहिती पाठवते. {partnerName} शी बोलल्याबद्दल धन्यवाद, तुमचा दिवस शुभ जावो! [HANGUP]'.\n\n"
                "## Objection Handling & Edge Cases\n"
                "- **Already has solar**: 'खूप छान! तुमच्या अनुभवाबद्दल ऐकून आनंद झाला. धन्यवाद आणि शुभ दिवस!'\n"
                "- **Caller is busy**: 'काही हरकत नाही! मी तुम्हाला नंतर कधी फोन करू, किंवा व्हॉट्सॲपवर माहिती पाठवून देऊ?'\n"
                "- **Cost / Price inquiry**: '२ kW सिस्टीमचा खर्च साधारण ₹१,२०,००० येतो, पण ₹७८,००० थेट सरकारी सबसिडी वजा जाता तुम्हाला फक्त ₹४२,००० भरावे लागतात.'"
            ),
        },
        "slot_definitions": [
            {"key": "monthly_bill", "label": "Monthly electricity bill", "required": True},
            {"key": "roof_type", "label": "Rooftop space / shade", "required": True},
            {"key": "home_ownership", "label": "Owns home", "required": True},
        ],
    },
    {
        "slug": "real-estate",
        "name": "Real Estate Property Consultant (Kavya)",
        "category": "Lead qualification",
        "icon_color": "orange",
        "description": "An AI agent that turns property inquiries into qualified, booked site visits.",
        "configuration": {
            "agent_name": "Kavya",
            "primary_language": "en-IN",
            "greeting": "Hello, thank you for connecting with {partnerName}! This is {salesRepName}. Are you looking to buy or rent {productCategory}?",
            "input_variables": {
                "partnerName": "Rishab Developers",
                "salesRepName": "Kavya",
                "userName": "",
                "productCategory": "Luxury 2 & 3 BHK Apartments",
            },
            "output_variables": ["disposition", "budget_indication", "timeline_to_decide", "chosen_next_step"],
            "system_prompt": (
                "# Role & Persona\n"
                "- **Agent Name**: {salesRepName}\n"
                "- **Role**: Warm property consultation specialist at {partnerName}.\n"
                "- **Tone**: Helpful, enthusiastic, polite, attentive.\n"
                "- **Language**: Natural conversational English / Hinglish.\n\n"
                "## Conversational Rules\n"
                "1. **Under 25 Words Per Turn**: Keep responses concise and engaging.\n"
                "2. **Strictly One Question Per Turn**: Focus on one detail at a time.\n"
                "3. **Acknowledge Enthusiastically**: React warmly to user choices before asking.\n\n"
                "## Conversation Flow\n"
                "- **Phase 1 (Discovery)**: Learn buyer vs investor preference and {productCategory} config.\n"
                "- **Phase 2 (Budget & Timeline)**: Clarify budget bracket and move-in timeline.\n"
                "- **Phase 3 (Site Visit Booking)**: Propose a weekend site visit or virtual tour."
            ),
        },
        "slot_definitions": [
            {"key": "budget", "label": "Budget", "required": True},
            {"key": "timeline", "label": "Move-in timeline", "required": True},
            {"key": "city", "label": "Preferred city", "required": True},
            {"key": "property_type", "label": "Property type", "required": True},
        ],
    },
    {
        "slug": "insurance",
        "name": "Health Insurance & Policy Renewal (Riya)",
        "category": "Recovery",
        "icon_color": "blue",
        "description": "An AI voice agent that calls policyholders to confirm health insurance renewals and answer benefits questions.",
        "configuration": {
            "agent_name": "Riya",
            "primary_language": "hi-IN",
            "greeting": "नमस्कार {userName} जी, मैं {partnerName} से {salesRepName} बोल रही हूँ। आपकी हेल्थ इन्शुरन्स पॉलिसी की रिन्यूअल डेट नज़दीक है, क्या आप इसे आज रिन्यू करना चाहेंगे?",
            "input_variables": {
                "partnerName": "Star Protect Insurance",
                "salesRepName": "Riya",
                "userName": "",
                "productCategory": "स्वास्थ्य बीमा",
            },
            "output_variables": ["disposition", "timeline_to_decide", "chosen_next_step"],
            "system_prompt": (
                "Persona: {salesRepName}, trusted insurance advisor at {partnerName}. "
                "Goal: Remind policyholders of no-claim bonus, seamless renewal, and send instant payment link."
            ),
        },
        "slot_definitions": [
            {"key": "policy_status", "label": "Renewal intent", "required": True},
        ],
    },
    {
        "slug": "education",
        "name": "Course Admissions & Career Counselor (Aarav)",
        "category": "Lead qualification",
        "icon_color": "gold",
        "description": "Educational admissions counselor that engages applicants, qualifies career goals, and schedules counseling sessions.",
        "configuration": {
            "agent_name": "Aarav",
            "primary_language": "en-IN",
            "greeting": "Hi {userName}, this is {salesRepName} calling from {partnerName} admissions office. I saw your inquiry for our upcoming course. Are you looking to upskill this semester?",
            "input_variables": {
                "partnerName": "EdTech Institute",
                "salesRepName": "Aarav",
                "userName": "",
                "productCategory": "Data Science & AI Certification",
            },
            "output_variables": ["disposition", "timeline_to_decide", "chosen_next_step"],
            "system_prompt": (
                "Persona: {salesRepName}, supportive academic counselor at {partnerName}. "
                "Goal: Understand student's current qualification, career aims, and offer a scholarship counseling session."
            ),
        },
        "slot_definitions": [
            {"key": "course_interest", "label": "Course interest", "required": True},
            {"key": "start_timeline", "label": "Preferred start date", "required": False},
        ],
    },
    {
        "slug": "home-services",
        "name": "Home Services & Maintenance Booking",
        "category": "Reminder",
        "icon_color": "green",
        "description": "Turn home service inquiries into instant scheduled technician appointments.",
        "configuration": {
            "agent_name": "Rohan",
            "primary_language": "en-IN",
            "greeting": "Hello, thank you for calling {partnerName}! My name is {salesRepName}. What service or repair can we schedule for your home today?",
            "input_variables": {
                "partnerName": "FixIt Home Pros",
                "salesRepName": "Rohan",
                "userName": "",
                "productCategory": "AC Repair & Servicing",
            },
            "output_variables": ["disposition", "chosen_next_step", "next_step_date_time"],
            "system_prompt": (
                "Persona: {salesRepName}, coordinator at {partnerName}. "
                "Goal: Identify appliance problem, service address, and book technician visit time."
            ),
        },
        "slot_definitions": [
            {"key": "service_type", "label": "Service requested", "required": True},
            {"key": "preferred_time", "label": "Preferred time slot", "required": True},
        ],
    },
    {
        "slug": "automotive",
        "name": "Automotive Service & Test Drive",
        "category": "Collections",
        "icon_color": "red",
        "description": "Schedule periodic vehicle maintenance, recall checkups, and test-drive bookings.",
        "configuration": {
            "agent_name": "Karan",
            "primary_language": "hi-IN",
            "greeting": "नमस्ते {userName} जी, मैं {partnerName} ऑटोमोटिव से {salesRepName} बात कर रहा हूँ। आपकी गाड़ी की सर्विसिंग ड्यू है, क्या हम इस वीकेंड पिकअप शेड्यूल करें?",
            "input_variables": {
                "partnerName": "Speed Motors",
                "salesRepName": "Karan",
                "userName": "",
                "productCategory": "कार सर्विसिंग",
            },
            "output_variables": ["disposition", "timeline_to_decide", "chosen_next_step"],
            "system_prompt": (
                "Persona: {salesRepName}, automotive advisor at {partnerName}. "
                "Goal: Schedule car servicing slot or new model test drive."
            ),
        },
        "slot_definitions": [
            {"key": "vehicle_model", "label": "Vehicle model", "required": True},
            {"key": "service_date", "label": "Service date", "required": True},
        ],
    },
    {
        "slug": "generic",
        "name": "Custom Voice Agent",
        "category": "Lead qualification",
        "icon_color": "blue",
        "description": "Blank canvas agent ready to be configured with custom persona, speaking style, input-output variables, and tools.",
        "configuration": {
            "agent_name": "Alex",
            "primary_language": "en-IN",
            "greeting": "Hello, thank you for connecting with {partnerName}. My name is {salesRepName}. How can I assist you today?",
            "input_variables": {
                "partnerName": "Our Company",
                "salesRepName": "Alex",
                "userName": "",
                "productCategory": "Services",
            },
            "output_variables": ["disposition", "chosen_next_step"],
            "system_prompt": "You are a warm, helpful AI phone assistant for {partnerName}.",
        },
        "slot_definitions": [],
    },
]


async def seed_templates(db: AsyncIOMotorDatabase) -> list[BusinessTemplate]:
    """Seed default business templates. Idempotent."""
    repo = BusinessTemplateRepository(db)
    created = []
    for tmpl in DEFAULT_TEMPLATES:
        existing = await repo.find_by_slug(tmpl["slug"])
        if existing is None:
            result = await repo.upsert(**tmpl)
            created.append(result)
            log.info("seeded template: %s", tmpl["slug"])
    return created


class AgentService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.templates = BusinessTemplateRepository(db)
        self.agents = AgentRepository(db)
        self.versions = AgentVersionRepository(db)

    async def list_templates(self) -> list[BusinessTemplate]:
        templates = await self.templates.list_active()
        if not templates or len(templates) < len(DEFAULT_TEMPLATES):
            await seed_templates(self.db)
            templates = await self.templates.list_active()
        return templates

    async def create_agent(
        self,
        organization_id: str,
        name: str,
        template_slug: str,
        voice_profile_id: str,
        voice_profile_version: int,
        description: str = "",
    ) -> Agent:
        # Validate template exists
        tmpl = await self.templates.find_by_slug(template_slug)
        if tmpl is None or not tmpl.is_active:
            raise ValueError(
                f"Business template '{template_slug}' not found. "
                f"Valid templates: {', '.join(TEMPLATE_SLUGS)}"
            )
        return await self.agents.create(
            organization_id=organization_id,
            name=name,
            template_slug=template_slug,
            voice_profile_id=voice_profile_id,
            voice_profile_version=voice_profile_version,
            description=description,
        )

    async def list_agents(self, organization_id: str) -> list[Agent]:
        return await self.agents.list_for_org(organization_id)

    async def get_agent(
        self, agent_id: str, organization_id: str
    ) -> Optional[Agent]:
        """Returns agent only if it belongs to this org (tenant isolation)."""
        return await self.agents.get_for_org(agent_id, organization_id)

    async def create_version(
        self,
        agent_id: str,
        organization_id: str,
        configuration: dict[str, Any],
        description: str = "",
        auto_activate: bool = False,
    ) -> AgentVersion:
        """Create a new draft version. Optionally publish and activate it."""
        agent = await self.agents.get_for_org(agent_id, organization_id)
        if agent is None:
            raise ValueError("Agent not found or does not belong to your organization")
        version = await self.versions.create_version(
            agent_id=agent_id,
            configuration=configuration,
            description=description,
        )
        if auto_activate:
            await self._publish_and_activate(agent_id, version)
        return version

    async def _publish_and_activate(
        self, agent_id: str, version: AgentVersion
    ) -> None:
        await self.versions.publish_version(version.id)
        await self.agents.set_active_version(agent_id, version.version, version.id)

    async def publish_version(
        self, agent_id: str, version_id: str, organization_id: str
    ) -> AgentVersion:
        """Publish a draft version and set it as active. Immutable after this."""
        agent = await self.agents.get_for_org(agent_id, organization_id)
        if agent is None:
            raise ValueError("Agent not found")
        version = await self.versions.find_by_id(version_id)
        if version is None or version.agent_id != agent_id:
            raise ValueError("Version not found")
        if version.status == "published":
            await self._publish_and_activate(agent_id, version)
            return version
        await self._publish_and_activate(agent_id, version)
        return await self.versions.find_by_id(version_id)

    async def update_draft_version(
        self,
        version_id: str,
        organization_id: str,
        configuration: dict[str, Any],
    ) -> AgentVersion:
        """Update a draft version's configuration. Fails if already published."""
        version = await self.versions.find_by_id(version_id)
        if version is None:
            raise ValueError("Version not found")
        # Verify ownership via agent
        agent = await self.agents.get_for_org(version.agent_id, organization_id)
        if agent is None:
            raise ValueError("Agent not found or does not belong to your organization")
        return await self.versions.update_draft(version_id, configuration)

    async def list_versions(
        self, agent_id: str, organization_id: str
    ) -> list[AgentVersion]:
        agent = await self.agents.get_for_org(agent_id, organization_id)
        if agent is None:
            raise ValueError("Agent not found")
        return await self.versions.list_for_agent(agent_id)

    async def delete_agent(
        self, agent_id: str, organization_id: str
    ) -> bool:
        agent = await self.agents.get_for_org(agent_id, organization_id)
        if agent is None:
            raise ValueError("Agent not found")
        return await self.agents.deactivate(agent_id)

    async def export_agent(
        self, agent_id: str, organization_id: str
    ) -> dict[str, Any]:
        """Export agent configuration scrubbed of all tenant-specific IDs.
        Conforms to format: sarvam_agent_export_v1.
        """
        from datetime import datetime, timezone

        agent = await self.agents.get_for_org(agent_id, organization_id)
        if agent is None:
            raise ValueError("Agent not found")

        version = None
        if agent.active_version_id:
            version = await self.versions.find_by_id(agent.active_version_id)
        if version is None:
            versions = await self.versions.list_for_agent(agent_id)
            if versions:
                version = versions[0]

        raw_config = version.configuration if version else {}

        # Sanitize configuration: remove tenant and DB identifiers
        clean_config = dict(raw_config)
        clean_config.pop("id", None)
        clean_config.pop("_id", None)
        clean_config.pop("organization_id", None)
        # Decouple knowledge bases: not bundled in agent file
        clean_config.pop("knowledge_base_ids", None)

        primary_lang = clean_config.get("primary_language", "en-IN")

        return {
            "format": "sarvam_agent_export_v1",
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "agent": {
                "name": agent.name,
                "description": agent.description or "",
                "template_slug": agent.template_slug,
                "primary_language": primary_lang,
                "configuration": clean_config,
            },
        }

    async def import_agent(
        self,
        organization_id: str,
        name: str,
        template_slug: str,
        configuration: dict[str, Any],
        description: str = "",
        voice_profile_id: Optional[str] = None,
    ) -> Agent:
        """Import an agent configuration into target organization, checking subscription limits."""
        from backend.services.subscription_service import SubscriptionService
        from backend.repositories.voice_profile_repo import VoiceProfileRepository

        # 1. Enforce max_agents subscription limit
        sub_svc = SubscriptionService(self.db)
        current_agents = await self.agents.list_for_org(organization_id)
        check = await sub_svc.check_can_add_agent(organization_id, len(current_agents))
        if not check.allowed:
            raise ValueError(check.reason or "Agent limit reached")

        # 2. Resolve voice profile if not explicitly provided
        vp_repo = VoiceProfileRepository(self.db)
        if not voice_profile_id:
            primary_lang = configuration.get("primary_language", "en-IN")
            available_vps = await vp_repo.list_for_customer(organization_id)
            matching = [v for v in available_vps if v.language == primary_lang]
            if matching:
                voice_profile_id = matching[0].id
            elif available_vps:
                voice_profile_id = available_vps[0].id
            else:
                voice_profile_id = "default"

        vp = await vp_repo.find_by_id(voice_profile_id)
        vp_version = vp.active_version if (vp and vp.active_version) else 1

        # 3. Validate template exists (fallback to 'generic' if template_slug unknown)
        tmpl = await self.templates.find_by_slug(template_slug)
        if tmpl is None or not tmpl.is_active:
            template_slug = "generic"

        # 4. Create agent record
        agent = await self.agents.create(
            organization_id=organization_id,
            name=name,
            template_slug=template_slug,
            voice_profile_id=voice_profile_id,
            voice_profile_version=vp_version,
            description=description,
        )

        # 5. Create initial published & active configuration version
        clean_config = dict(configuration)
        clean_config.pop("knowledge_base_ids", None)

        await self.create_version(
            agent_id=agent.id,
            organization_id=organization_id,
            configuration=clean_config,
            description="Imported agent configuration",
            auto_activate=True,
        )

        return await self.agents.find_by_id(agent.id)
