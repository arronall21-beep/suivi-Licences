import asyncio
import io

from openpyxl import Workbook

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


async def create(admin, category, **kw):
    r = await admin.post("/api/v1/assets", json={"category": category, "name": kw.pop("name", "Item"), **kw})
    assert r.status_code == 201, r.text
    return r.json()


async def test_reference_generated_per_category(admin):
    expected = {"LICENCE": "LIC", "CERTIFICAT": "CERT", "MATERIEL": "MAT", "APPLICATION": "APP"}
    for category, prefix in expected.items():
        assert (await create(admin, category))["reference"] == f"{prefix}-001"
        assert (await create(admin, category))["reference"] == f"{prefix}-002"


async def test_contract_and_vendor_references(admin):
    v1 = (await admin.post("/api/v1/vendors", json={"name": "A"})).json()
    v2 = (await admin.post("/api/v1/vendors", json={"name": "B"})).json()
    assert (v1["reference"], v2["reference"]) == ("VEN-001", "VEN-002")
    c1 = (await admin.post("/api/v1/contracts", json={"scope": "x"})).json()
    c2 = (await admin.post("/api/v1/contracts", json={"scope": "y"})).json()
    assert (c1["reference"], c2["reference"]) == ("CTR-001", "CTR-002")


async def test_reference_never_reused_after_delete(admin):
    a1 = await create(admin, "LICENCE")
    a2 = await create(admin, "LICENCE")
    assert (await admin.delete(f"/api/v1/assets/{a2['id']}")).status_code == 204
    a3 = await create(admin, "LICENCE")
    assert (a1["reference"], a3["reference"]) == ("LIC-001", "LIC-003")  # count()+1 aurait redonné LIC-002


async def test_explicit_reference_is_kept_and_skipped_by_generator(admin):
    a = await create(admin, "LICENCE", reference="LIC-001")
    assert a["reference"] == "LIC-001"
    b = await create(admin, "LICENCE")  # LIC-001 existe déjà : on passe à la suivante libre
    assert b["reference"] == "LIC-002"
    dup = await admin.post("/api/v1/assets", json={"category": "LICENCE", "name": "x", "reference": "LIC-001"})
    assert dup.status_code == 409


async def test_update_keeps_reference(admin):
    a = await create(admin, "CERTIFICAT")
    r = await admin.put(f"/api/v1/assets/{a['id']}", json={"category": "CERTIFICAT", "name": "Renamed"})
    assert r.status_code == 200 and r.json()["reference"] == a["reference"] and r.json()["name"] == "Renamed"


async def test_concurrent_creations_are_unique(admin):
    results = await asyncio.gather(
        *[admin.post("/api/v1/assets", json={"category": "LICENCE", "name": f"L{i}"}) for i in range(20)]
    )
    assert all(r.status_code == 201 for r in results), [r.text for r in results if r.status_code != 201]
    refs = [r.json()["reference"] for r in results]
    assert len(set(refs)) == 20
    assert sorted(refs) == [f"LIC-{i:03d}" for i in range(1, 21)]


def workbook(rows):
    wb = Workbook()
    ws = wb.active
    ws.title = "Licences_Logicielles"
    ws.append(["ID", "Logiciel", "Nb licences"])
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


async def upload(admin, content):
    r = await admin.post("/api/v1/import/excel", files={"file": ("f.xlsx", content, XLSX)})
    assert r.status_code == 200, r.text
    return r.json()


async def test_import_keeps_generates_and_ignores_invalid(admin):
    content = workbook(
        [["LIC-010", "Explicite", 5], [None, "Sans référence", 3], [None, None, 9], ["LIC-001", "Autre explicite", 1]]
    )
    rep = await upload(admin, content)
    assert rep["rows_imported"] == 3 and rep["errors_count"] == 1
    refs = {a["name"]: a["reference"] for a in (await admin.get("/api/v1/assets", params={"size": 50})).json()["items"]}
    assert refs["Explicite"] == "LIC-010" and refs["Autre explicite"] == "LIC-001"
    assert refs["Sans référence"] == "LIC-002"  # LIC-001 est réservée par une ligne explicite du même fichier
    # La ligne invalide n'a consommé aucun numéro : la prochaine création reste dans la suite.
    assert (await create(admin, "LICENCE"))["reference"] == "LIC-011"  # séquence alignée après import de LIC-010


async def test_reimport_of_rows_without_reference_is_idempotent(admin):
    content = workbook([[None, "Sans référence", 3]])
    first = await upload(admin, content)
    second = await upload(admin, content)
    assert first["created"] == 1 and second["created"] == 0 and second["updated"] == 1
    assert (await admin.get("/api/v1/assets")).json()["total"] == 1


async def test_sync_never_wastes_a_free_number(admin, db):
    """Après une migration, la séquence « prochaine valeur = 6 » ne doit pas devenir « 6 consommée » à l'import."""
    from sqlalchemy import text

    for ref in ("CERT-001", "CERT-002", "CERT-003", "CERT-004", "CERT-005"):
        await admin.post("/api/v1/assets", json={"category": "CERTIFICAT", "name": ref, "reference": ref})
    await db.execute(text("ALTER SEQUENCE ref_cert_seq RESTART WITH 6"))  # état laissé par la migration 0002
    await db.commit()
    content = workbook([["LIC-001", "Office", 5]])
    await upload(admin, content)  # déclenche la synchronisation des séquences
    assert (await create(admin, "CERTIFICAT"))["reference"] == "CERT-006"
    # une référence explicite plus haute fait bien avancer la séquence
    await admin.post("/api/v1/assets", json={"category": "CERTIFICAT", "name": "x", "reference": "CERT-020"})
    await upload(admin, workbook([["LIC-001", "Office", 5]]))
    assert (await create(admin, "CERTIFICAT"))["reference"] == "CERT-021"
