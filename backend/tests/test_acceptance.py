"""RIMETRA.md §15 kabul kriterleri."""
import copy
import uuid

from sample_reports import family_practice_report, private_hospital_report


def bearer(k):
    return {"Authorization": f"Bearer {k}"}


def post_report(client, key, body, **params):
    q = "&".join(f"{k}={v}" for k, v in params.items())
    return client.post(f"/api/v1/reports{'?' + q if q else ''}", json=body,
                       headers={**bearer(key), "Idempotency-Key": str(uuid.uuid4())})


def by_name(results, raw_name):
    return next(r for r in results if r["raw_name"] == raw_name)


# 1) Girişsiz hiçbir veri sayfası veya API ucu açılmıyor
def test_no_unauthenticated_access(client, family):
    anon = client.__class__(client.app)
    for path in ["/api/app/dashboard", "/api/app/members", f"/api/app/members/{family['burak_id']}/summary",
                 "/api/v1/me", "/api/v1/members", f"/api/v1/members/{family['burak_id']}/summary"]:
        r = anon.get(path)
        assert r.status_code == 401, (path, r.status_code)
        assert "error" in r.json()
    r = anon.post("/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    assert r.status_code == 401
    r = client.get("/api/v1/me", headers=bearer("rmt_live_yanlisanahtar1234567890"))
    assert r.status_code == 401 and r.json()["error"]["code"] == "INVALID_API_KEY"


# 2) ve 3) Aynı rapor iki kez → 409, tek kayıt; farklı PDF baytları da 409
def test_duplicate_report(client, family):
    body = family_practice_report(family["burak_id"])
    r1 = post_report(client, family["key"], body)
    assert r1.status_code == 201, r1.text
    rid = r1.json()["report_id"]
    r2 = post_report(client, family["key"], body)
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "DUPLICATE_REPORT"
    assert r2.json()["error"]["existing_report_id"] == rid

    # Yeniden indirilmiş PDF: bayt farklı, metin biçimi biraz farklı (sıra, boşluk, virgül) — içerik aynı
    again = copy.deepcopy(body)
    again["pdf_sha256"] = "a" * 64
    again["facility"] = "  Örnek 12 Nolu Aile Hekimliği Birimi "
    again["panels"].reverse()
    again["panels"][0]["results"].reverse()
    for p in again["panels"]:
        for res in p["results"]:
            if res["raw_value"] == "3.9":
                res["raw_value"] = "3,9"
    r3 = post_report(client, family["key"], again)
    assert r3.status_code == 409, r3.text
    assert r3.json()["error"]["code"] == "DUPLICATE_REPORT"

    lst = client.get(f"/api/v1/members/{family['burak_id']}/reports", headers=bearer(family["key"])).json()
    assert lst["total"] == 1


def test_overlap_and_skip_existing(client, family):
    body = family_practice_report(family["burak_id"])
    assert post_report(client, family["key"], body).status_code == 201
    partial = copy.deepcopy(body)
    partial["panels"] = [partial["panels"][0]]  # aynı hemogram + yeni bir test
    partial["panels"][0]["results"].append({"raw_name": "Trombosit (PLT)", "raw_value": "250", "raw_reference": "150 - 400"})
    r = post_report(client, family["key"], partial)
    assert r.status_code == 409 and r.json()["error"]["code"] == "OVERLAPPING_RESULTS"
    assert len(r.json()["error"]["conflicts"]) == 4
    r = post_report(client, family["key"], partial, on_overlap="skip_existing")
    assert r.status_code == 201, r.text
    assert r.json()["summary"]["results_total"] == 1


def test_idempotency_key(client, family):
    body = family_practice_report(family["burak_id"])
    h = {**bearer(family["key"]), "Idempotency-Key": "abc-123"}
    r1 = client.post("/api/v1/reports", json=body, headers=h)
    r2 = client.post("/api/v1/reports", json=body, headers=h)
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["report_id"] == r2.json()["report_id"]


def test_dry_run_does_not_store(client, family):
    body = family_practice_report(family["burak_id"])
    r = post_report(client, family["key"], body, dry_run="true")
    assert r.status_code == 200 and r.json()["dry_run"] is True and r.json()["report_id"] is None
    s = r.json()["summary"]
    assert s["results_total"] == 15 and s["skipped"] == 1
    lst = client.get(f"/api/v1/members/{family['burak_id']}/reports", headers=bearer(family["key"])).json()
    assert lst["total"] == 0


# 4) Hemogram Lökosit ile idrar Lökosit ayrı trendlerde
def test_wbc_blood_vs_urine_separate(client, family):
    r = post_report(client, family["key"], family_practice_report(family["burak_id"]))
    res = r.json()["results"]
    assert by_name(res, "Lökosit (WBC)")["test_key"] == "blood.wbc"
    assert by_name(res, "Lökosit")["test_key"] == "urine.leukocyte_esterase"
    glucose = [x for x in res if x["raw_name"] == "Glukoz"]
    assert {g["test_key"] for g in glucose} == {"urine.glucose", "serum.glucose"}
    summ = client.get(f"/api/v1/members/{family['burak_id']}/summary", headers=bearer(family["key"])).json()
    keys = {i["test_key"] for i in summ["items"]}
    assert {"blood.wbc", "urine.leukocyte_esterase"} <= keys


# 5) &lt;41 → ALT 19 normal
def test_alt_lt_reference(client, family):
    res = post_report(client, family["key"], family_practice_report(family["burak_id"])).json()["results"]
    alt = by_name(res, "ALT")
    assert alt["ref_high"] == 41 and alt["ref_low"] is None
    assert alt["flag_computed"] == "normal"
    glu = [x for x in res if x["test_key"] == "serum.glucose"][0]
    assert glu["ref_low"] == 74 and glu["ref_high"] == 106 and "Diyabet" in glu["ref_note"]
    lok = by_name(res, "Lökosit (WBC)")
    assert lok["flag_computed"] == "low"
    assert by_name(res, "# Lenfosit # Lenfosit")["test_key"] == "blood.lym_abs"


# 6) Sayfa bölünmesi birleşmiş kaydediliyor
def test_page_split_merged(client, family):
    r = post_report(client, family["key"], private_hospital_report(family["burak_id"]))
    assert r.status_code == 201, r.text
    kultur = by_name(r.json()["results"], "Kültür")
    assert kultur["value_text"] == "Bakteri izole edilmedi."
    assert kultur["test_key"] == "urine.culture"


# 7) Eritrosit POZİTİF (++++): computed abnormal, source ok, uyuşmazlık
def test_flag_mismatch(client, family):
    r = post_report(client, family["key"], family_practice_report(family["burak_id"]))
    res = r.json()["results"]
    eri = by_name(res, "Eritrosit.")
    assert eri["flag_computed"] == "abnormal" and eri["flag_source"] == "ok" and eri["flag_mismatch"] is True
    ket = by_name(res, "Keton")
    assert ket["flag_computed"] == "abnormal" and ket["flag_mismatch"] is True
    assert r.json()["summary"]["flag_mismatches"] >= 2
    detail = client.get(f"/api/app/reports/{r.json()['report_id']}").json()
    flat = [x for p in detail["panels"] for x in p["results"]]
    assert any(x["raw_name"] == "Eritrosit." and x["flag_mismatch"] for x in flat)
    assert any(p["name"] == "Adsız panel" for p in detail["panels"])


# 8) Dansite 1.012 ve 1005 aynı ölçekte
def test_density_scale(client, family):
    post_report(client, family["key"], family_practice_report(family["burak_id"]))
    post_report(client, family["key"], private_hospital_report(family["burak_id"]))
    h = client.get(f"/api/v1/members/{family['burak_id']}/tests/urine.density/history", headers=bearer(family["key"])).json()
    vals = [m["value_numeric"] for m in h["measurements"]]
    assert vals == [1.012, 1.005]
    assert h["measurements"][1]["ref_low"] == 1.005 and h["measurements"][1]["ref_high"] == 1.03
    assert all(m["flag_computed"] == "normal" for m in h["measurements"])


# 9) Üye kısıtlı anahtar başka üyeye yazamaz
def test_member_scoped_key(client, family):
    r = post_report(client, family["limited_key"], family_practice_report(family["burak_id"]))
    assert r.status_code == 403 and r.json()["error"]["code"] == "MEMBER_DENIED"
    r = client.get("/api/v1/members", headers=bearer(family["limited_key"]))
    assert [m["id"] for m in r.json()["items"]] == [family["ayse_id"]]
    r = client.post("/api/v1/members", json={"display_name": "X"}, headers=bearer(family["limited_key"]))
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "SCOPE_DENIED"


def test_name_mismatch(client, family):
    body = family_practice_report(family["ayse_id"])  # belgede BURAK yazıyor
    r = post_report(client, family["key"], body)
    assert r.status_code == 422 and r.json()["error"]["code"] == "NAME_MISMATCH"


# 10) Değerler/raporlar ve orijinal PDF
def test_pdf_attach_and_open(client, family):
    r = post_report(client, family["key"], family_practice_report(family["burak_id"]))
    rid = r.json()["report_id"]
    pdf = b"%PDF-1.4\n% test\n1 0 obj<<>>endobj\ntrailer<<>>\n%%EOF"
    up = client.post(f"/api/v1/reports/{rid}/pdf", files={"file": ("rapor.pdf", pdf, "application/pdf")}, headers=bearer(family["key"]))
    assert up.status_code == 200, up.text
    got = client.get(f"/api/app/reports/{rid}/pdf")
    assert got.status_code == 200 and got.content == pdf
    reps = client.get(f"/api/app/members/{family['burak_id']}/reports").json()
    assert reps["items"][0]["has_pdf"] is True
    # aynı PDF başka rapora eklenemez
    r2 = post_report(client, family["key"], private_hospital_report(family["burak_id"]))
    dup = client.post(f"/api/v1/reports/{r2.json()['report_id']}/pdf", files={"file": ("x.pdf", pdf, "application/pdf")},
                      headers=bearer(family["key"]))
    assert dup.status_code == 409


def test_delete_and_restore(client, family):
    body = family_practice_report(family["burak_id"])
    rid = post_report(client, family["key"], body).json()["report_id"]
    assert client.delete(f"/api/v1/reports/{rid}", headers=bearer(family["key"])).status_code == 200
    assert client.get(f"/api/v1/reports/{rid}", headers=bearer(family["key"])).status_code == 404
    r = client.post(f"/api/app/reports/{rid}/restore", headers=family["H"])
    assert r.status_code == 200
    assert post_report(client, family["key"], body).status_code == 409


def test_unmapped_and_link(client, family):
    body = family_practice_report(family["burak_id"])
    body["panels"][2]["results"].append({"raw_name": "Homosistein", "raw_value": "12", "raw_unit": "µmol/L", "raw_reference": "5 - 15"})
    r = post_report(client, family["key"], body)
    assert r.json()["summary"]["unmapped"] == 1
    um = client.get("/api/app/unmapped").json()["items"]
    assert um[0]["raw_name"] == "Homosistein"
    r = client.post("/api/app/catalog/tests?link_raw_name=Homosistein", headers=family["H"], json={
        "key": "serum.homocysteine", "display_name": "Homosistein", "specimen": "serum", "category": "Biyokimya",
        "canonical_unit": "µmol/L", "value_type": "numeric"})
    assert r.status_code == 201, r.text
    assert r.json()["linked"]["linked_results"] == 1
    assert client.get("/api/app/unmapped").json()["items"] == []


def test_member_user_sees_only_own(client, family):
    H = family["H"]
    client.post("/api/app/admin/users", headers=H, json={"username": "ayse", "password": "ayse12345", "member_id": family["ayse_id"]})
    post_report(client, family["key"], family_practice_report(family["burak_id"]))
    client.post("/api/auth/logout", headers=H)
    assert client.post("/api/auth/login", json={"username": "ayse", "password": "ayse12345"}).status_code == 200
    d = client.get("/api/app/dashboard").json()
    assert [m["id"] for m in d["members"]] == [family["ayse_id"]]
    assert client.get(f"/api/app/members/{family['burak_id']}/summary").status_code == 403
    assert client.post(f"/api/app/members/{family['ayse_id']}/notes", headers=H, json={"date": "2025-01-01", "text": "ilaç başladı"}).status_code == 201
    assert client.get("/api/app/admin/users").status_code == 403


def test_mcp_flow(client, family):
    h = bearer(family["key"])
    init = client.post("/mcp", headers=h, json={"jsonrpc": "2.0", "id": 1, "method": "initialize",
                                                  "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t", "version": "1"}}})
    assert init.json()["result"]["serverInfo"]["name"] == "rimetra"
    tools = client.post("/mcp", headers=h, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}).json()["result"]["tools"]
    assert {t["name"] for t in tools} >= {"list_members", "preview_report", "submit_report", "get_member_summary", "get_test_history", "list_reports"}
    body = family_practice_report(family["burak_id"])
    # önizlemesiz gönderim reddedilir
    r = client.post("/mcp", headers=h, json={"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                                              "params": {"name": "submit_report", "arguments": {"report": body, "preview_token": "x"}}}).json()
    assert r["result"]["isError"] is True
    pv = client.post("/mcp", headers=h, json={"jsonrpc": "2.0", "id": 4, "method": "tools/call",
                                               "params": {"name": "preview_report", "arguments": {"report": body}}}).json()
    token = pv["result"]["structuredContent"]["preview_token"]
    # değiştirilmiş gövde reddedilir
    changed = copy.deepcopy(body)
    changed["panels"][0]["results"][0]["raw_value"] = "5.0"
    r = client.post("/mcp", headers=h, json={"jsonrpc": "2.0", "id": 5, "method": "tools/call",
                                              "params": {"name": "submit_report", "arguments": {"report": changed, "preview_token": token}}}).json()
    assert r["result"]["isError"] is True
    r = client.post("/mcp", headers=h, json={"jsonrpc": "2.0", "id": 6, "method": "tools/call",
                                              "params": {"name": "submit_report", "arguments": {"report": body, "preview_token": token}}}).json()
    assert r["result"]["isError"] is False
    assert r["result"]["structuredContent"]["report_id"]


def test_rate_limit(client, family):
    from app.config import get_settings
    lim = get_settings().api_rate_limit_per_minute
    codes = [client.get("/api/v1/me", headers=bearer(family["key"])).status_code for _ in range(lim + 2)]
    assert codes[-1] == 429


def test_exports_and_manual(client, family):
    H = family["H"]
    post_report(client, family["key"], family_practice_report(family["burak_id"]))
    r = client.post(f"/api/app/members/{family['burak_id']}/manual", headers=H, json={
        "date": "2025-09-01", "time": "08:30", "items": [{"test_key": "vital.weight", "value": "78,5"},
                                                          {"test_key": "vital.bp_sys", "value": "125", "reference": "90 - 130"}]})
    assert r.status_code == 201, r.text
    csv = client.get(f"/api/app/members/{family['burak_id']}/export.csv?tests=serum.uric_acid,vital.weight")
    assert csv.status_code == 200 and "Ürik Asit" in csv.content.decode("utf-8")
    pdf = client.get(f"/api/app/members/{family['burak_id']}/export.pdf?tests=serum.uric_acid,blood.wbc,urine.protein")
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"
    cmp_ids = [x["id"] for x in client.get(f"/api/app/members/{family['burak_id']}/reports").json()["items"]]
    c = client.get(f"/api/app/compare?a={cmp_ids[0]}&b={cmp_ids[1]}")
    assert c.status_code == 200


def test_login_throttle(client, family):
    client.post("/api/auth/logout", headers=family["H"])
    codes = [client.post("/api/auth/login", json={"username": "burak", "password": "yanlis"}).status_code for _ in range(5)]
    assert 429 in codes
