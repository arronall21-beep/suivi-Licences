from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Asset, LicenseAssignment


class AllocationError(ValueError):
    pass


async def check_allocation(db: AsyncSession, asset_id: int, quantity: int, exclude_assignment_id: int | None = None) -> Asset:
    """Garantit SUM(assignments.quantity) <= total_quantity. Lève AllocationError sinon."""
    # Verrou de ligne pour sérialiser les affectations concurrentes sur la même licence
    await db.execute(select(Asset.id).where(Asset.id == asset_id).with_for_update())
    asset = await db.get(Asset, asset_id)
    if asset is None:
        raise AllocationError("Actif introuvable")
    if asset.category != "LICENCE":
        raise AllocationError("Seules les licences peuvent être affectées")
    stmt = select(func.coalesce(func.sum(LicenseAssignment.quantity), 0)).where(LicenseAssignment.asset_id == asset_id)
    if exclude_assignment_id is not None:
        stmt = stmt.where(LicenseAssignment.id != exclude_assignment_id)
    already = (await db.execute(stmt)).scalar_one()
    total = asset.total_quantity or 0
    if already + quantity > total:
        raise AllocationError(
            f"Sur-allocation refusée : {already} déjà affectée(s) + {quantity} demandée(s) "
            f"> {total} disponible(s) au total (reste {max(total - already, 0)})"
        )
    return asset
