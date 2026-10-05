"""Agrégats du dashboard et planning de renouvellement (calculés depuis la base)."""

from collections import Counter
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import lifecycle
from app.models import CATEGORIES, Asset, Contract, Vendor

CATEGORY_LABELS = {"LICENCE": "Licences", "CERTIFICAT": "Certificats", "MATERIEL": "Matériels", "APPLICATION": "Applications"}
RENEWAL_BUDGET_HORIZON_DAYS = 365


async def load_all(db: AsyncSession) -> tuple[list[Asset], list[Contract]]:
    assets = list((await db.execute(select(Asset))).unique().scalars())
    contracts = list((await db.execute(select(Contract))).unique().scalars())
    return assets, contracts


def renewal_items(assets: list[Asset], contracts: list[Contract]) -> list[dict]:
    items = []
    for a in assets:
        end = a.effective_end_date
        status = lifecycle.compute_status(end)
        items.append(
            {
                "kind": "ASSET",
                "id": a.id,
                "type": a.category,
                "reference": a.reference,
                "name": a.name,
                "vendor_name": a.vendor_name,
                "end_date": end,
                "renewal_start_date": end,
                "days_remaining": lifecycle.days_remaining(end),
                "status": status,
                "priority": lifecycle.priority(status, a.criticality),
                "criticality": a.criticality,
                "owner": a.internal_owner,
                "department": a.user_department,
                "budget": float(a.budget_estimated or a.annual_cost or 0) or None,
                "action_plan": a.action_plan,
            }
        )
    for c in contracts:
        status = lifecycle.compute_status(c.end_date)
        items.append(
            {
                "kind": "CONTRACT",
                "id": c.id,
                "type": "CONTRAT",
                "reference": c.reference,
                "name": c.scope or c.type or c.reference,
                "vendor_name": c.vendor_name,
                "end_date": c.end_date,
                "renewal_start_date": c.renewal_start_date,
                "days_remaining": c.days_remaining,
                "status": status,
                "priority": lifecycle.priority(status, None),
                "criticality": None,
                "owner": c.internal_owner,
                "department": None,
                "budget": float(c.annual_amount or 0) or None,
                "action_plan": None,
                "notice_period_days": c.notice_period_days,
                "notice_reached": bool(c.renewal_start_date and c.renewal_start_date <= lifecycle.today()),
            }
        )
    return items


def filter_renewals(items: list[dict], horizon_days: int | None, include_expired: bool = True) -> list[dict]:
    today = lifecycle.today()
    limit = today + timedelta(days=horizon_days) if horizon_days is not None else None
    out = []
    for it in items:
        end: date | None = it["end_date"]
        if end is None:
            continue
        if end <= today and not include_expired:
            continue
        if limit and end > limit:
            continue
        out.append(it)
    out.sort(key=lambda x: (x["end_date"], x["kind"]))
    return out


async def build_dashboard(db: AsyncSession) -> dict:
    assets, contracts = await load_all(db)
    vendors_count = len(list((await db.execute(select(Vendor.id))).scalars()))
    by_cat = Counter(a.category for a in assets)
    statuses = Counter(a.status for a in assets)
    contract_statuses = Counter(c.lifecycle_status for c in contracts)

    lic = [a for a in assets if a.category == "LICENCE"]
    lic_total = sum(a.total_quantity or 0 for a in lic)
    lic_used = sum(a.assigned_quantity for a in lic)

    items = renewal_items(assets, contracts)
    horizon = lifecycle.today() + timedelta(days=RENEWAL_BUDGET_HORIZON_DAYS)
    # Un contrat dont les actifs portent déjà un budget n'est pas recompté.
    covered = {a.contract_id for a in assets if a.contract_id}
    renewal_budget = sum(
        i["budget"] or 0
        for i in items
        if i["end_date"] and i["end_date"] <= horizon and not (i["kind"] == "CONTRACT" and i["id"] in covered)
    )

    status_by_category = []
    for cat in CATEGORIES:
        c = Counter(a.status for a in assets if a.category == cat)
        status_by_category.append(
            {"category": cat, "label": CATEGORY_LABELS[cat], **{s: c.get(s, 0) for s in lifecycle.STATUSES}}
        )

    upcoming = filter_renewals(items, horizon_days=180)[:12]
    return {
        "thresholds": {"critical_days": lifecycle.config.critical_days, "alert_days": lifecycle.config.alert_days},
        "kpis": {
            "total_assets": len(assets),
            "licences": by_cat.get("LICENCE", 0),
            "certificats": by_cat.get("CERTIFICAT", 0),
            "materiels": by_cat.get("MATERIEL", 0),
            "applications": by_cat.get("APPLICATION", 0),
            "contracts": len(contracts),
            "vendors": vendors_count,
        },
        "deadlines": {
            "expired": statuses.get(lifecycle.EXPIRE, 0),
            "critical": statuses.get(lifecycle.CRITIQUE, 0),
            "warning": statuses.get(lifecycle.ALERTE, 0),
            "ok": statuses.get(lifecycle.OK, 0),
            "unknown": statuses.get(lifecycle.INCONNU, 0),
        },
        "contract_deadlines": {
            "expired": contract_statuses.get(lifecycle.EXPIRE, 0),
            "critical": contract_statuses.get(lifecycle.CRITIQUE, 0),
            "warning": contract_statuses.get(lifecycle.ALERTE, 0),
            "ok": contract_statuses.get(lifecycle.OK, 0),
            "unknown": contract_statuses.get(lifecycle.INCONNU, 0),
        },
        "licenses": {
            "total": lic_total,
            "used": lic_used,
            "available": lic_total - lic_used,
            "usage_rate": round(lic_used / lic_total * 100, 1) if lic_total else 0,
        },
        "finance": {
            "annual_cost_total": round(sum(float(a.annual_cost or 0) for a in assets), 2),
            "contracts_annual_total": round(sum(float(c.annual_amount or 0) for c in contracts), 2),
            "budget_estimated_total": round(sum(float(a.budget_estimated or 0) for a in assets), 2),
            "renewal_budget_12m": round(renewal_budget, 2),
        },
        "by_category": [{"category": c, "label": CATEGORY_LABELS[c], "count": by_cat.get(c, 0)} for c in CATEGORIES],
        "status_by_category": status_by_category,
        "upcoming_renewals": upcoming,
    }
