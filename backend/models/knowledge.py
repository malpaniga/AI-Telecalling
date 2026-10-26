"""Knowledge base models — minimal, tenant-safe.

Per spec: "Do NOT over-engineer RAG in MVP."

KnowledgeBase: a named collection of documents owned by an org.
  - An org can have multiple KBs (e.g. "Product FAQ", "Objection Handlers")
  - Each KB can be associated with one or more agents

KnowledgeDocument: a single piece of knowledge (Q&A pair, policy, script snippet).
  - Has content (markdown/plain text)
  - Versioned: each edit creates a new version; active_version points to current
  - No vector embeddings in MVP — simple keyword/text search

Document types (free-form field, no special logic):
  faq            — question/answer pair
  objection      — objection and suggested response
  product_info   — product/service information
  script         — conversation script snippet
  policy         — compliance or policy text
  general        — anything else
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import Field

from backend.models.base import TimestampedModel


class KnowledgeBase(TimestampedModel):
    """A named collection of knowledge documents."""
    organization_id: str
    name: str
    description: str = ""
    document_count: int = 0
    is_active: bool = True
    tags: list[str] = Field(default_factory=list)


class KnowledgeDocument(TimestampedModel):
    """A single knowledge document with versioning."""
    organization_id: str
    knowledge_base_id: str

    title: str
    content: str                    # markdown or plain text
    document_type: str = "general"  # faq, objection, product_info, script, policy, general

    # Versioning
    version: int = 1
    is_active: bool = True
    previous_version_id: Optional[str] = None  # linked list of versions

    # Search helpers (MVP: simple keyword matching)
    keywords: list[str] = Field(default_factory=list)  # extracted or manual

    # Metadata
    source: str = "manual"          # manual | import | api
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)

    # Timestamps
    last_edited_at: Optional[datetime] = None
    last_edited_by: Optional[str] = None


class KnowledgeBaseAgent(TimestampedModel):
    """Association between a KnowledgeBase and an Agent."""
    organization_id: str
    knowledge_base_id: str
    agent_id: str
    priority: int = 0               # lower = checked first
