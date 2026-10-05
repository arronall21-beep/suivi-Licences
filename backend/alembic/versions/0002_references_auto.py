"""Références automatiques : séquences PostgreSQL et référence fournisseur

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

SEQUENCES = [
    ("lic", "LIC", "assets", "LICENCE"),
    ("cert", "CERT", "assets", "CERTIFICAT"),
    ("mat", "MAT", "assets", "MATERIEL"),
    ("app", "APP", "assets", "APPLICATION"),
    ("ctr", "CTR", "contracts", None),
    ("ven", "VEN", "vendors", None),
]


def upgrade() -> None:
    op.add_column("vendors", sa.Column("reference", sa.String(length=100), nullable=True))
    # Fournisseurs existants : VEN-001… dans l'ordre de création
    op.execute(
        """
        UPDATE vendors v SET reference = 'VEN-' || LPAD(n.rn::text, 3, '0')
        FROM (SELECT id, ROW_NUMBER() OVER (ORDER BY id) AS rn FROM vendors) n
        WHERE v.id = n.id AND v.reference IS NULL
        """
    )
    op.create_index("ix_vendors_reference", "vendors", ["reference"], unique=True)

    for seq, prefix, table, category in SEQUENCES:
        where = f"AND category = '{category}'" if category else ""
        op.execute(f"CREATE SEQUENCE IF NOT EXISTS ref_{seq}_seq")
        # asyncpg n'accepte qu'une commande par instruction : setval dans un second execute
        op.execute(
            f"""
            SELECT setval('ref_{seq}_seq', COALESCE(
                (SELECT MAX(CAST(substring(reference from '^{prefix}-([0-9]+)$') AS INTEGER)) FROM {table}
                 WHERE reference ~ '^{prefix}-[0-9]+$' {where}), 0) + 1, false)
            """
        )


def downgrade() -> None:
    for seq, *_ in SEQUENCES:
        op.execute(f"DROP SEQUENCE IF EXISTS ref_{seq}_seq")
    op.drop_index("ix_vendors_reference", table_name="vendors")
    op.drop_column("vendors", "reference")
