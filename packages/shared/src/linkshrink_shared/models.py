"""SQLAlchemy 2.0 models (Link, ClickEvent) and the link_code_seq sequence.

Source-of-truth schema shared by every service (api, redirect, worker). Alembic
owns the schema in deployed environments — services import these models but never
auto-create tables. See TDD §5.3.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    MetaData,
    Sequence,
    Text,
    func,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# Deterministic constraint/index names across the ORM and Alembic, so autogenerate
# and hand-authored migrations agree on names (avoids spurious diffs later).
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base carrying the shared MetaData (with naming convention)."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class DeviceType(enum.StrEnum):
    """Coarse device class derived from the User-Agent by the worker (PII-free)."""

    desktop = "desktop"
    mobile = "mobile"
    tablet = "tablet"
    unknown = "unknown"


class Source(enum.StrEnum):
    """How the click arrived: a direct click vs. a scanned QR code."""

    direct = "direct"
    qr = "qr"


# Standalone sequence that feeds hashids short-code generation (Epic 3). Not bound
# to a column — the API calls nextval('link_code_seq') and encodes the result.
# Attached to Base.metadata so Alembic and create_all know about it.
link_code_seq = Sequence("link_code_seq", start=1, increment=1, metadata=Base.metadata)


class Link(Base):
    """A shortened link: its code, target URL, and lifetime."""

    __tablename__ = "links"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    # Stored already-normalized to lowercase; the functional unique index below is
    # the case-insensitive uniqueness guard (chosen over citext to avoid the
    # CREATE EXTENSION privilege, TDD §5.3).
    short_code: Mapped[str] = mapped_column(Text, nullable=False)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    is_custom: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # TDD §5.3's "expires_at ≤ created_at + 30 days" invariant is enforced at the
    # application layer by the API's ttl_seconds clamp (Epic 6, max 2592000s), not by
    # a DB CHECK — deliberate, so the bound lives in one place alongside the lower
    # clamp. No constraint here is intentional, not an omission.
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    click_events: Mapped[list[ClickEvent]] = relationship(
        back_populates="link", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        # Case-insensitive uniqueness guard on the short code.
        Index("uq_links_lower_short_code", text("lower(short_code)"), unique=True),
        # Keyset pagination for the dashboard feed (newest first).
        Index("ix_links_created_at_id_desc", text("created_at DESC"), text("id DESC")),
        # Purge-job scans over expired links.
        Index("ix_links_expires_at", "expires_at"),
    )


class ClickEvent(Base):
    """A single PII-free click on a link, written by the analytics worker (Epic 12)."""

    __tablename__ = "click_events"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    link_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("links.id", ondelete="CASCADE"), nullable=False
    )
    clicked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    referrer_domain: Mapped[str | None] = mapped_column(Text, nullable=True)
    device_type: Mapped[DeviceType] = mapped_column(
        Enum(DeviceType, name="device_type"), nullable=False
    )
    browser_family: Mapped[str | None] = mapped_column(Text, nullable=True)
    os_family: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[Source] = mapped_column(Enum(Source, name="source"), nullable=False)

    link: Mapped[Link] = relationship(back_populates="click_events")

    __table_args__ = (
        # Per-link analytics aggregation (Epic 8).
        Index("ix_click_events_link_id_clicked_at", "link_id", "clicked_at"),
    )
