from datetime import date, timedelta


async def test_health(anon):
    r = await anon.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["database"] == "ok"


async def test_auth_required(anon):
    assert (await anon.get("/api/v1/assets")).status_code == 401
    r = await anon.post("/api/v1/auth/login", json={"email": "admin@example.com", "password": "wrong"})
    assert r.status_code == 401


async def test_viewer_read_only(viewer):
    assert (await viewer.get("/api/v1/assets")).status_code == 200
    r = await viewer.post("/api/v1/vendors", json={"name": "X"})
    assert r.status_code == 403


async def license(admin, total=100, **kw):
    r = await admin.post(
        "/api/v1/assets",
        json={"reference": kw.pop("reference", "LIC-T1"), "category": "LICENCE", "name": "Office", "total_quantity": total, **kw},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_crud_vendor_contract_asset(admin):
    v = (await admin.post("/api/v1/vendors", json={"name": "Microsoft", "email_support": "s@ms.com"})).json()
    assert (await admin.post("/api/v1/vendors", json={"name": "Microsoft"})).status_code == 409
    end = (date.today() + timedelta(days=100)).isoformat()
    c = await admin.post(
        "/api/v1/contracts", json={"reference": "C1", "vendor_id": v["id"], "end_date": end, "notice_period_days": 90}
    )
    assert c.status_code == 201
    c = c.json()
    assert c["vendor_name"] == "Microsoft" and c["lifecycle_status"] == "OK"
    assert c["renewal_start_date"] == (date.today() + timedelta(days=10)).isoformat()

    a = await license(admin, vendor_id=v["id"], contract_id=c["id"], end_date=(date.today() + timedelta(days=20)).isoformat())
    assert a["status"] == "CRITIQUE" and a["days_remaining"] == 20 and a["vendor_name"] == "Microsoft"

    upd = {
        **{k: a[k] for k in ("reference", "category", "name", "total_quantity", "vendor_id", "contract_id")},
        "criticality": "Haute",
        "end_date": (date.today() + timedelta(days=200)).isoformat(),
    }
    r = await admin.put(f"/api/v1/assets/{a['id']}", json=upd)
    assert r.status_code == 200 and r.json()["status"] == "OK" and r.json()["criticality"] == "Haute"

    lst = (await admin.get("/api/v1/assets", params={"category": "LICENCE", "status": "OK", "q": "off"})).json()
    assert lst["total"] == 1
    assert (await admin.get("/api/v1/assets", params={"status": "CRITIQUE"})).json()["total"] == 0

    assert (await admin.delete(f"/api/v1/vendors/{v['id']}")).status_code == 409
    assert (await admin.delete(f"/api/v1/assets/{a['id']}")).status_code == 204
    assert (await admin.get(f"/api/v1/assets/{a['id']}")).status_code == 404
    assert (await admin.delete(f"/api/v1/contracts/{c['id']}")).status_code == 204
    assert (await admin.delete(f"/api/v1/vendors/{v['id']}")).status_code == 204


async def test_validation_errors(admin):
    r = await admin.post("/api/v1/assets", json={"reference": "", "category": "AUTRE", "name": "x"})
    assert r.status_code == 422 and r.json()["errors"]


async def test_assignment_usage_and_overallocation(admin):
    lic = await license(admin, total=100)
    r = await admin.post("/api/v1/assignments", json={"asset_id": lic["id"], "assigned_to_department": "DSI", "quantity": 60})
    assert r.status_code == 201
    a = (await admin.get(f"/api/v1/assets/{lic['id']}")).json()
    assert (a["assigned_quantity"], a["available_quantity"], a["usage_rate"]) == (60, 40, 60.0)
    assert len(a["assignments"]) == 1

    r = await admin.post("/api/v1/assignments", json={"asset_id": lic["id"], "assigned_to_user": "bob", "quantity": 41})
    assert r.status_code == 422 and "Sur-allocation" in r.json()["detail"]
    r = await admin.post("/api/v1/assignments", json={"asset_id": lic["id"], "assigned_to_user": "bob", "quantity": 40})
    assert r.status_code == 201
    second = r.json()

    # Modification : on exclut la ligne modifiée du calcul
    r = await admin.put(
        f"/api/v1/assignments/{second['id']}", json={"asset_id": lic["id"], "assigned_to_user": "bob", "quantity": 41}
    )
    assert r.status_code == 422
    r = await admin.put(
        f"/api/v1/assignments/{second['id']}", json={"asset_id": lic["id"], "assigned_to_user": "bob", "quantity": 10}
    )
    assert r.status_code == 200

    # Baisse de la quantité totale sous le nombre affecté refusée
    body = {"reference": "LIC-T1", "category": "LICENCE", "name": "Office", "total_quantity": 50}
    assert (await admin.put(f"/api/v1/assets/{lic['id']}", json=body)).status_code == 422

    assert (await admin.delete(f"/api/v1/assignments/{second['id']}")).status_code == 204
    a = (await admin.get(f"/api/v1/assets/{lic['id']}")).json()
    assert a["available_quantity"] == 40


async def test_assignment_only_on_licences(admin):
    r = await admin.post("/api/v1/assets", json={"reference": "M1", "category": "MATERIEL", "name": "Serveur"})
    r = await admin.post("/api/v1/assignments", json={"asset_id": r.json()["id"], "assigned_to_user": "x", "quantity": 1})
    assert r.status_code == 422


async def test_dashboard_and_renewals(admin):
    await license(admin, total=100, end_date=(date.today() + timedelta(days=10)).isoformat(), annual_cost=1000, reference="L1")
    await license(admin, total=50, end_date=(date.today() - timedelta(days=1)).isoformat(), reference="L2")
    await admin.post(
        "/api/v1/assets",
        json={
            "reference": "C1",
            "category": "CERTIFICAT",
            "name": "*.x.fr",
            "end_date": (date.today() + timedelta(days=60)).isoformat(),
        },
    )
    lic = (await admin.get("/api/v1/assets", params={"reference": "L1"})).json()["items"][0]
    await admin.post("/api/v1/assignments", json={"asset_id": lic["id"], "assigned_to_department": "DSI", "quantity": 75})
    d = (await admin.get("/api/v1/dashboard")).json()
    assert d["kpis"]["total_assets"] == 3 and d["kpis"]["licences"] == 2 and d["kpis"]["certificats"] == 1
    assert d["deadlines"] == {"expired": 1, "critical": 1, "warning": 1, "ok": 0, "unknown": 0}
    assert d["licenses"] == {"total": 150, "used": 75, "available": 75, "usage_rate": 50.0}
    assert d["finance"]["annual_cost_total"] == 1000
    assert len(d["upcoming_renewals"]) == 3

    ren = (await admin.get("/api/v1/renewals", params={"horizon_days": 30})).json()
    assert [r["reference"] for r in ren] == ["L2", "L1"]

    alerts = (await admin.get("/api/v1/alerts")).json()
    assert {a["threshold"] for a in alerts["items"]} == {0, 30, 60}
    run1 = (await admin.post("/api/v1/alerts/run")).json()
    run2 = (await admin.post("/api/v1/alerts/run")).json()
    assert run1["new"] == 3 and run2["new"] == 0  # pas de doublon
    assert len((await admin.get("/api/v1/notifications")).json()) == 3
