"""Utilisateurs : identité complète, dernière connexion, version de jeton ; notifications internes

Revision ID: 0003
Revises: 0002
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("first_name", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("last_name", sa.String(length=120), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(length=50), nullable=True))
    op.add_column("users", sa.Column("department", sa.String(length=255), nullable=True))
    op.add_column("users", sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    # Comptes v1.0 : prénom/nom déduits de full_name
    op.execute(
        """
        UPDATE users SET
          first_name = NULLIF(split_part(trim(coalesce(full_name, '')), ' ', 1), ''),
          last_name = NULLIF(trim(substr(trim(coalesce(full_name, '')), length(split_part(trim(coalesce(full_name, '')), ' ', 1)) + 1)), '')
        WHERE first_name IS NULL
        """
    )

    op.create_table(
        "app_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("priority", sa.String(length=10), nullable=False, server_default="MEDIUM"),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("link", sa.String(length=500), nullable=True),
        sa.Column("entity_type", sa.String(length=20), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("audience", sa.String(length=10), nullable=False, server_default="ALL"),
        sa.Column("dedupe_key", sa.String(length=200), nullable=True, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_app_notifications_kind", "app_notifications", ["kind"])
    op.create_index("ix_app_notifications_created_at", "app_notifications", ["created_at"])
    op.create_table(
        "app_notification_reads",
        sa.Column("notification_id", sa.Integer(), sa.ForeignKey("app_notifications.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("read_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_notification_reads")
    op.drop_table("app_notifications")
    for col in ("last_login_at", "token_version", "department", "phone", "last_name", "first_name"):
        op.drop_column("users", col)
