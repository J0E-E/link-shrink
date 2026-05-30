"""initial schema: links, click_events, link_code_seq

Creates the source-of-truth schema (TDD §5.3): the link_code_seq sequence, the
links and click_events tables (with native device_type/source enum types), the
ON DELETE CASCADE foreign key, and the four indexes.

downgrade() drops everything back to an empty database. It is lossless by
definition for the first revision and exists only for local test teardown and
migration-authoring round-trips — downgrades are never run in deployed
environments (forward-only policy, TDD §5.11/§8).

Revision ID: 0001
Revises:
Create Date: 2026-05-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Enum types are created explicitly (create_type=False on the columns) so the
# order is deterministic and downgrade can drop them cleanly.
device_type_enum = postgresql.ENUM(
    "desktop", "mobile", "tablet", "unknown", name="device_type"
)
source_enum = postgresql.ENUM("direct", "qr", name="source")


def upgrade() -> None:
    bind = op.get_bind()

    device_type_enum.create(bind, checkfirst=True)
    source_enum.create(bind, checkfirst=True)

    # Standalone sequence feeding hashids short-code generation (Epic 3).
    op.execute("CREATE SEQUENCE link_code_seq START WITH 1 INCREMENT BY 1")

    op.create_table(
        "links",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("short_code", sa.Text(), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column("is_custom", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_links"),
    )

    op.create_table(
        "click_events",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("link_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "clicked_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("referrer_domain", sa.Text(), nullable=True),
        sa.Column(
            "device_type",
            postgresql.ENUM(name="device_type", create_type=False),
            nullable=False,
        ),
        sa.Column("browser_family", sa.Text(), nullable=True),
        sa.Column("os_family", sa.Text(), nullable=True),
        sa.Column(
            "source",
            postgresql.ENUM(name="source", create_type=False),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["link_id"],
            ["links.id"],
            name="fk_click_events_link_id_links",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_click_events"),
    )

    # Case-insensitive uniqueness guard on the short code (functional unique index).
    op.execute(
        "CREATE UNIQUE INDEX uq_links_lower_short_code ON links (lower(short_code))"
    )
    # Keyset pagination for the dashboard feed (newest first).
    op.execute(
        "CREATE INDEX ix_links_created_at_id_desc ON links "
        "(created_at DESC, id DESC)"
    )
    # Purge-job scans over expired links.
    op.create_index("ix_links_expires_at", "links", ["expires_at"])
    # Per-link analytics aggregation.
    op.create_index(
        "ix_click_events_link_id_clicked_at",
        "click_events",
        ["link_id", "clicked_at"],
    )


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_click_events_link_id_clicked_at", table_name="click_events")
    op.drop_index("ix_links_expires_at", table_name="links")
    op.drop_index("ix_links_created_at_id_desc", table_name="links")
    op.drop_index("uq_links_lower_short_code", table_name="links")

    op.drop_table("click_events")
    op.drop_table("links")

    op.execute("DROP SEQUENCE IF EXISTS link_code_seq")

    source_enum.drop(bind, checkfirst=True)
    device_type_enum.drop(bind, checkfirst=True)
