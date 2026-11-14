"""POST /reports/{id}/result-mappings — rapor bazında sonuç eşleştirmesi düzeltme.

Senaryo: 2021 raporunda çıplak "Bazofil" adı mutlak sayım (0,05) için kullanılmış ve genel alias
yüzünden yüzde testine bağlanmış; gerçek yüzde satırı ("Bazofil %", 0,9) çakışma nedeniyle eşleşmemiş.
2024 raporunda ise "Bazofil" gerçekten yüzde. Düzeltme yalnızca 2021 raporunu etkilemeli.
"""
import uuid

from sqlalchemy import func, select

from app.db import SessionLocal
from app.models import AuditLog
from app.models import TestAlias as AliasRow
from test_acceptance import bearer

CELLS = [  # (çıplak ad, sayım, yüzde, test kökü)
    ("Bazofil", "0,05", "0,9", "baso"),
    ("Eozinofil", "0,11", "2,1", "eos"),
    ("Lenfosit", "1,79", "33,4", "lym"),
    ("Monosit", "0,38", "7,1", "mono"),
    ("Nötrofil", "3,03", "56,5", "neu"),
]


def report_2021(member_id):
    rows = [{"raw_name": "Lökosit (WBC)", "raw_value": "5,36", "raw_unit": "10^3/µL", "raw_reference": "4 - 10"}]
    for name, cnt, pct, _ in CELLS:
        rows.append({"raw_name": name, "raw_value": cnt, "raw_unit": "10^3/µL", "raw_reference": ""})
        rows.append({"raw_name": f"{name} %", "raw_value": pct, "raw_unit": "%", "raw_reference": ""})
    return {"member_id": member_id, "source": "enabiz", "report_date": "2021-01-12", "facility": "TEST HASTANESİ",
            "patient_name_on_document": "AYŞE YILMAZ",
            "panels": [{"name": "Hemogram", "sample_datetime": "2021-01-12T09:00:00+03:00", "specimen": "blood", "results": rows}]}


def report_2024(member_id):
    rows = [{"raw_name": n, "raw_value": p, "raw_unit": "%", "raw_reference": ""} for n, _, p, _ in CELLS]
    return {"member_id": member_id, "source": "enabiz", "report_date": "2024-03-01", "facility": "TEST HASTANESİ",
            "patient_name_on_document": "AYŞE YILMAZ",
            "panels": [{"name": "Hemogram", "sample_datetime": "2024-03-01T09:00:00+03:00", "specimen": "blood", "results": rows}]}


def _post(client, key, body):
    r = client.post("/api/v1/reports", json=body, headers={**bearer(key), "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 201, r.text
    return r.json()["report_id"]


def _results(client, key, report_id):
    d = client.get(f"/api/v1/reports/{report_id}", headers=bearer(key)).json()
    return [r for p in d["panels"] for r in p["results"]]


def _remap(client, key, report_id, body, dry_run=False, idem=None):
    url = f"/api/v1/reports/{report_id}/result-mappings" + ("?dry_run=true" if dry_run else "")
    return client.post(url, json=body, headers={**bearer(key), "Idempotency-Key": idem or str(uuid.uuid4())})


def _setup(client, family):
    key = family["limited_key"]  # yalnızca Ayşe; reports:write var, catalog:write YOK
    rid = _post(client, key, report_2021(family["ayse_id"]))
    rid24 = _post(client, key, report_2024(family["ayse_id"]))
    return key, rid, rid24


def _fix_body(results):
    by = {r["raw_name"]: r for r in results}
    changes = []
    for name, _, _, k in CELLS:
        cnt, pct = by[name], by[f"{name} %"]
        changes.append({"result_id": cnt["id"], "expected_current_test_key": cnt["test_key"], "target_test_key": f"blood.{k}_abs"})
        changes.append({"result_id": pct["id"], "expected_current_test_key": pct["test_key"], "target_test_key": f"blood.{k}_pct"})
    return {"reason": "2021 raporunda mutlak hücre sayımları yanlışlıkla yüzde testlerine bağlanmış.", "changes": changes}


def test_remap_full_flow(client, family):
    key, rid, rid24 = _setup(client, family)
    before = _results(client, key, rid)
    by = {r["raw_name"]: r for r in before}
    # Başlangıç durumu Codex'in tarif ettiği gibi
    assert by["Bazofil"]["test_key"] == "blood.baso_pct"
    assert by["Bazofil %"]["test_key"] is None
    before24 = _results(client, key, rid24)
    with SessionLocal() as db:
        alias_count = db.scalar(select(func.count()).select_from(AliasRow))

    body = _fix_body(before)

    # Önizleme: hiçbir şey değişmez
    pv = _remap(client, key, rid, body, dry_run=True)
    assert pv.status_code == 200, pv.text
    pj = pv.json()
    assert pj["ok"] is True and pj["dry_run"] is True and pj["changed_count"] == 10 and pj["conflicts"] == []
    baso = next(c for c in pj["changes"] if c["raw_name"] == "Bazofil")
    assert baso["from_test_key"] == "blood.baso_pct" and baso["to_test_key"] == "blood.baso_abs"
    assert baso["after"]["unit"] == "10³/µL" and baso["after"]["value_numeric"] == 0.05
    assert _results(client, key, rid) == before

    # Uygula (önizleme jetonuyla)
    idem = str(uuid.uuid4())
    r = _remap(client, key, rid, {**body, "preview_token": pj["preview_token"]}, idem=idem)
    assert r.status_code == 200, r.text
    assert r.json()["changed_count"] == 10 and r.json()["dry_run"] is False

    after = _results(client, key, rid)
    assert len(after) == len(before) == 11
    a = {x["raw_name"]: x for x in after}
    for name, cnt, pct, k in CELLS:
        assert a[name]["test_key"] == f"blood.{k}_abs"
        assert a[f"{name} %"]["test_key"] == f"blood.{k}_pct"
        assert a[name]["raw_value"] == cnt and a[f"{name} %"]["raw_value"] == pct  # ham veri korunur
        assert a[name]["id"] == by[name]["id"] and a[name]["sample_datetime"] == by[name]["sample_datetime"]
    # WBC × % / 100 ≈ sayım (Codex'in tutarlılık kontrolü)
    for name, _, _, _ in CELLS:
        assert round(5.36 * a[f"{name} %"]["value_numeric"] / 100, 2) == a[name]["value_numeric"]

    # Diğer rapor ve genel alias'lar değişmedi
    assert _results(client, key, rid24) == before24
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AliasRow)) == alias_count
        logs = db.scalars(select(AuditLog).where(AuditLog.action == "result.remap")).all()
        assert len(logs) == 10
        assert all(log.actor_type == "api_key" and log.payload_diff["reason"].startswith("2021") for log in logs)
        assert {(log.payload_diff["from"], log.payload_diff["to"]) for log in logs} >= {("blood.baso_pct", "blood.baso_abs"), (None, "blood.baso_pct")}

    # Aynı Idempotency-Key → aynı yanıt, ikinci kez işlem/denetim kaydı yok
    r2 = _remap(client, key, rid, {**body, "preview_token": pj["preview_token"]}, idem=idem)
    assert r2.status_code == 200 and r2.json() == r.json()
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == "result.remap")) == 10

    # Artık beklenen bağlantı eski → yeni anahtarla tekrar göndermek 409
    r3 = _remap(client, key, rid, body)
    assert r3.status_code == 409 and r3.json()["error"]["code"] == "MAPPING_CHANGED"

    # Geçmiş grafikleri: 2021 sayımı _abs geçmişinde, 2024 yüzdesi _pct geçmişinde
    h = client.get(f"/api/v1/members/{family['ayse_id']}/tests/blood.baso_abs/history", headers=bearer(key)).json()
    assert "0.05" in str(h)


def test_partial_change_conflicts_on_final_state(client, family):
    key, rid, _ = _setup(client, family)
    by = {r["raw_name"]: r for r in _results(client, key, rid)}
    # Sayımı taşımadan yüzdeyi bağlamaya çalışmak gerçek bir çakışmadır
    body = {"reason": "deneme", "changes": [
        {"result_id": by["Bazofil %"]["id"], "expected_current_test_key": None, "target_test_key": "blood.baso_pct"}]}
    pv = _remap(client, key, rid, body, dry_run=True)
    assert pv.status_code == 200 and pv.json()["ok"] is False
    c = pv.json()["conflicts"][0]
    assert c["conflicting_result_id"] == by["Bazofil"]["id"]
    r = _remap(client, key, rid, body)
    assert r.status_code == 409 and r.json()["error"]["code"] == "MAPPING_CONFLICT"
    # İki satır aynı hedefe
    body["changes"].append({"result_id": by["Bazofil"]["id"], "expected_current_test_key": "blood.baso_pct",
                            "target_test_key": "blood.baso_pct"})
    r = _remap(client, key, rid, body)
    assert r.status_code == 409 and r.json()["error"]["code"] == "MAPPING_CONFLICT"
    assert _results(client, key, rid)[1]["test_key"] == "blood.baso_pct"  # hiçbir şey değişmedi


def test_validation_errors(client, family):
    key, rid, rid24 = _setup(client, family)
    by = {r["raw_name"]: r for r in _results(client, key, rid)}
    other = _results(client, key, rid24)[0]

    def call(changes, k=key, report=rid):
        return _remap(client, k, report, {"reason": "deneme", "changes": changes})

    # Sonuç başka rapora ait
    r = call([{"result_id": other["id"], "expected_current_test_key": other["test_key"], "target_test_key": "blood.baso_abs"}])
    assert r.status_code == 422 and r.json()["error"]["code"] == "RESULT_NOT_IN_REPORT"
    # Bilinmeyen hedef
    r = call([{"result_id": by["Bazofil"]["id"], "expected_current_test_key": "blood.baso_pct", "target_test_key": "blood.yok"}])
    assert r.status_code == 400 and r.json()["error"]["code"] == "UNKNOWN_TEST_KEY"
    # Ölçüm biçimi: % birimli satır sayım testine bağlanamaz
    r = call([{"result_id": by["Bazofil %"]["id"], "expected_current_test_key": None, "target_test_key": "blood.baso_abs"}])
    assert r.status_code == 422 and r.json()["error"]["code"] == "INCOMPATIBLE_TEST"
    # Numune: kan satırı idrar testine bağlanamaz
    r = call([{"result_id": by["Bazofil"]["id"], "expected_current_test_key": "blood.baso_pct", "target_test_key": "urine.ph"}])
    assert r.status_code == 422 and r.json()["error"]["code"] == "INCOMPATIBLE_TEST"
    # Tekrarlanan result_id
    ch = {"result_id": by["Bazofil"]["id"], "expected_current_test_key": "blood.baso_pct", "target_test_key": "blood.baso_abs"}
    assert call([ch, ch]).status_code == 400
    # Üyeye erişimi olmayan anahtar (Ayşe'yle sınırlı anahtar, Burak'ın raporu)
    rid_r = _post(client, family["key"], {**report_2021(family["burak_id"]), "patient_name_on_document": "BURAK YILMAZ"})
    rb = {x["raw_name"]: x for x in _results(client, family["key"], rid_r)}
    r = call([{"result_id": rb["Bazofil"]["id"], "expected_current_test_key": "blood.baso_pct", "target_test_key": "blood.baso_abs"}],
             report=rid_r)
    assert r.status_code == 403 and r.json()["error"]["code"] == "MEMBER_DENIED"
    # Önizleme jetonu başka gövdeye ait
    body = {"reason": "deneme", "changes": [ch]}
    tok = _remap(client, key, rid, body, dry_run=True).json()["preview_token"]
    r = _remap(client, key, rid, {"reason": "başka gerekçe", "changes": [ch], "preview_token": tok})
    assert r.status_code == 400 and r.json()["error"]["code"] == "PREVIEW_MISMATCH"
    # Silinmiş rapor
    client.delete(f"/api/v1/reports/{rid}", headers=bearer(key))
    assert call([ch]).status_code == 404


def test_mcp_preview_and_apply(client, family):
    key, rid, _ = _setup(client, family)

    def tool(name, args):
        r = client.post("/mcp", headers=bearer(key), json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                                           "params": {"name": name, "arguments": args}})
        return r.json()["result"]

    rep = tool("get_report", {"report_id": rid})["structuredContent"]
    body = _fix_body([x for p in rep["panels"] for x in p["results"]])
    res = tool("apply_result_mappings", {"report_id": rid, **body})
    assert res["isError"] and res["structuredContent"]["error"]["code"] == "PREVIEW_REQUIRED"
    pv = tool("preview_result_mappings", {"report_id": rid, **body})["structuredContent"]
    assert pv["ok"] and pv["changed_count"] == 10
    res = tool("apply_result_mappings", {"report_id": rid, **body, "preview_token": pv["preview_token"]})
    assert not res["isError"], res
    a = {x["raw_name"]: x for x in _results(client, key, rid)}
    assert a["Bazofil"]["test_key"] == "blood.baso_abs" and a["Bazofil %"]["test_key"] == "blood.baso_pct"
