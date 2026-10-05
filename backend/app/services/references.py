"""Génération des références métier (LIC-001, CERT-001, MAT-001, APP-001, CTR-001, VEN-001).

Les numéros viennent de séquences PostgreSQL : atomiques, sans réutilisation après suppression.
Une référence saisie à la main (import Excel, API) peut déjà exister : on avance alors à la
suivante libre, sans jamais réutiliser ni écraser une référence existante.
"""

from sqlalchemy import Integer, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import REFERENCE_PREFIXES, REFERENCE_SEQUENCES, Asset, Contract, Vendor

MAX_ATTEMPTS = 1000


def format_reference(kind: str, number: int) -> str:
    return f"{REFERENCE_PREFIXES[kind]}-{number:03d}"


def _exists_stmt(kind: str, ref: str):
    if kind == "CONTRACT":
        return select(Contract.id).where(func.upper(Contract.reference) == ref.upper()).limit(1)
    if kind == "VENDOR":
        return select(Vendor.id).where(func.upper(Vendor.reference) == ref.upper()).limit(1)
    return select(Asset.id).where(Asset.category == kind, func.upper(Asset.reference) == ref.upper()).limit(1)


async def next_reference(db: AsyncSession, kind: str, reserved: set[str] | None = None) -> str:
    """Prochaine référence libre pour `kind` (LICENCE, CERTIFICAT, MATERIEL, APPLICATION, CONTRACT, VENDOR).

    `reserved` : références (en majuscules) à ne pas attribuer, par ex. celles saisies plus bas dans un fichier importé.
    """
    seq = REFERENCE_SEQUENCES[kind]
    for _ in range(MAX_ATTEMPTS):
        number = (await db.execute(select(seq.next_value()))).scalar_one()
        ref = format_reference(kind, number)
        if (reserved is None or ref.upper() not in reserved) and (await db.execute(_exists_stmt(kind, ref))).first() is None:
            return ref
    raise RuntimeError(f"Impossible de générer une référence {kind} libre")


async def sync_sequence(db: AsyncSession, kind: str) -> None:
    """Aligne la séquence sur le plus grand numéro existant (après un import de références explicites)."""
    prefix = REFERENCE_PREFIXES[kind]
    seq = REFERENCE_SEQUENCES[kind]
    pattern = f"^{prefix}-([0-9]+)$"
    if kind == "CONTRACT":
        col, where = Contract.reference, None
    elif kind == "VENDOR":
        col, where = Vendor.reference, None
    else:
        col, where = Asset.reference, Asset.category == kind
    number = func.cast(func.substring(col, pattern), Integer)
    stmt = select(func.coalesce(func.max(number), 0))
    if where is not None:
        stmt = stmt.where(where)
    highest = (await db.execute(stmt)).scalar_one()
    if highest:
        # GREATEST : ne jamais faire reculer la séquence
        await db.execute(
            select(func.setval(seq.name, func.greatest(highest, text(f"(SELECT last_value FROM {seq.name})")), True))
        )
