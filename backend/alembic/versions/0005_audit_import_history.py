"""Journal d'audit ; taille et statut des imports

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("user_email", sa.String(length=255), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("entity_type", sa.String(length=30), nullable=True),
        sa.Column("entity_id", sa.String(length=50), nullable=True),
        sa.Column("entity_label", sa.String(length=255), nullable=True),
        sa.Column("result", sa.String(length=10), nullable=False, server_default="SUCCESS"),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
    )
    for col in ("created_at", "user_email", "action", "entity_type"):
        op.create_index(f"ix_audit_logs_{col}", "audit_logs", [col])
    op.add_column("import_logs", sa.Column("file_size", sa.Integer(), nullable=True))
    op.add_column("import_logs", sa.Column("status", sa.String(length=20), nullable=False, server_default="SUCCESS"))
    # Imports existants : statut déduit des compteurs
    op.execute(
        "UPDATE import_logs SET status = CASE WHEN errors_count > 0 THEN 'ERRORS' WHEN warnings_count > 0 THEN 'WARNINGS' ELSE 'SUCCESS' END"
    )


def downgrade() -> None:
    op.drop_column("import_logs", "status")
    op.drop_column("import_logs", "file_size")
    op.drop_table("audit_logs")
