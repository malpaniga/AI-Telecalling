"""SQLAlchemy models: leads, calls, turns, bookings.

Slots (budget/timeline/city/property_type) are stored as free-text strings to
match what the extraction engine produces (e.g. "90 lakhs", "3 months").
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid_col() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[uuid.UUID] = _uuid_col()
    name: Mapped[str | None] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(160))

    # Qualification slots (free text).
    budget: Mapped[str | None] = mapped_column(String(120))
    timeline: Mapped[str | None] = mapped_column(String(120))
    city: Mapped[str | None] = mapped_column(String(120))
    property_type: Mapped[str | None] = mapped_column(String(120))

    score: Mapped[int] = mapped_column(Integer, default=0)
    # new | qualifying | qualified | booked | lost
    status: Mapped[str] = mapped_column(String(20), default="new", index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    calls: Mapped[list["Call"]] = relationship(back_populates="lead")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="lead")


class Call(Base):
    __tablename__ = "calls"

    id: Mapped[uuid.UUID] = _uuid_col()
    lead_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"))

    direction: Mapped[str] = mapped_column(String(10), default="inbound")  # inbound|outbound
    status: Mapped[str] = mapped_column(String(12), default="active")  # active|completed|failed
    outcome: Mapped[str | None] = mapped_column(String(20))  # booked|callback|not_interested|no_answer

    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_s: Mapped[int | None] = mapped_column(Integer)
    avg_latency_ms: Mapped[int | None] = mapped_column(Integer)
    recording_url: Mapped[str | None] = mapped_column(String(400))

    lead: Mapped["Lead"] = relationship(back_populates="calls")
    turns: Mapped[list["Turn"]] = relationship(
        back_populates="call", order_by="Turn.ts", cascade="all, delete-orphan"
    )


class Turn(Base):
    __tablename__ = "turns"

    id: Mapped[uuid.UUID] = _uuid_col()
    call_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("calls.id", ondelete="CASCADE"), index=True)

    role: Mapped[str] = mapped_column(String(10))  # user | agent
    text: Mapped[str] = mapped_column(Text)
    stage: Mapped[str | None] = mapped_column(String(20))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    call: Mapped["Call"] = relationship(back_populates="turns")


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = _uuid_col()
    lead_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("leads.id", ondelete="SET NULL"))
    call_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("calls.id", ondelete="SET NULL"))

    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    property_ref: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(12), default="proposed")  # proposed|confirmed|cancelled
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    lead: Mapped["Lead"] = relationship(back_populates="bookings")
