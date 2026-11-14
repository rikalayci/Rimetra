"""'Sonuç değil' — eşleşmemiş, sonuç olmayan satırları gizleme ve geri alma."""
import uuid

from sqlalchemy import select

from app.db import SessionLocal
from app.models import AuditLog, Result
from test_acceptance import bearer

ISTEM = "Kan Sayımı Otomatik Hemogram (geniş panel)"


def _report(member_id, name_on_doc, day="03", extra=None):
    rows = [
        {"raw_name": ISTEM, "raw_value": "1", "raw_unit": None, "raw_reference": None},
        {"raw_name": "Hemoglobin", "raw_value": "13,6", "raw_unit": "g/dL", "raw_reference": "12 - 16"},
        {"raw_name": "Garip Test", "raw_value": "5", "raw_unit": None, "raw_reference": None},
        *(extra or []),
    ]
    return {"member_id": member_id, "source": "enabiz", "report_date": f"2023-06-{day}", "facility": "TEST LAB",
            "patient_name_on_document": name_on_doc,
            "panels": [{"name": "Hemogram", "sample_datetime": f"2023-06-{day}T09:00:00+03:00", "specimen": "blood", "results": rows}]}


def _post(client, key, body):
    r = client.post("/api/v1/reports", json=body, headers={**bearer(key), "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 201, r.text
    return r.json()["report_id"]


def _unmapped_names(client):
    return {g["raw_name"]: g for g in client.get("/api/app/unmapped").json()["items"]}


def _detail(client, rid):
    d = client.get(f"/api/app/reports/{rid}").json()
    return d, [r["raw_name"] for p in d["panels"] for r in p["results"]]


def test_dismiss_group_from_ui_and_undo(client, family):
    H, key = family["H"], family["key"]
    r1 = _post(client, key, _report(family["burak_id"], "BURAK YILMAZ", "03"))
    r2 = _post(client, key, _report(family["burak_id"], "BURAK YILMAZ", "10"))
    g = _unmapped_names(client)[ISTEM]
    assert g["count"] == 2 and len(g["result_ids"]) == 2

    body = {"raw_name": ISTEM, "specimen": "blood", "reason": "e-Nabız istem satırı, sonuç değil"}
    pv = client.post("/api/app/unmapped/dismiss?dry_run=true", json=body, headers=H)
    assert pv.status_code == 200 and pv.json()["dismissed_count"] == 2
    assert ISTEM in _unmapped_names(client)  # önizleme hiçbir şeyi değiştirmez

    r = client.post("/api/app/unmapped/dismiss", json=body, headers=H)
    assert r.status_code == 200, r.text
    ids = [x["result_id"] for x in r.json()["results"]]
    assert sorted(ids) == sorted(g["result_ids"])
    names = _unmapped_names(client)
    assert ISTEM not in names and "Garip Test" in names  # başka satırlara dokunulmadı

    d, rows = _detail(client, r1)
    assert ISTEM not in rows and "Hemoglobin" in rows
    assert d["result_count"] == len(rows) == 2
    with SessionLocal() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.action == "result.dismiss")).payload_diff["reason"].startswith("e-Nabız")
        # Kayıt silinmedi, yalnızca gizlendi
        assert db.scalar(select(Result).where(Result.id == ids[0])).raw_value == "1"

    # Geri al
    r = client.post("/api/app/results/restore", json={"result_ids": ids}, headers=H)
    assert r.status_code == 200 and r.json()["restored_count"] == 2
    assert _unmapped_names(client)[ISTEM]["count"] == 2
    assert ISTEM in _detail(client, r2)[1]


def test_report_counts_exclude_dismissed(client, family):
    key = family["key"]
    rid = _post(client, key, _report(family["burak_id"], "BURAK YILMAZ"))
    before = client.get(f"/api/v1/reports/{rid}", headers=bearer(key)).json()
    client.post("/api/v1/results/dismiss", json={"raw_name": ISTEM, "specimen": "blood"}, headers=bearer(key))
    after = client.get(f"/api/v1/reports/{rid}", headers=bearer(key)).json()
    n = lambda d: sum(len(p["results"]) for p in d["panels"])  # noqa: E731
    assert n(after) == n(before) - 1
    assert after["result_count"] == n(after) == before["result_count"] - 1
    items = client.get(f"/api/v1/members/{family['burak_id']}/reports", headers=bearer(key)).json()["items"]
    assert items[0]["result_count"] == n(after)


def test_report_restore_keeps_dismissed_hidden(client, family):
    H, key = family["H"], family["key"]
    rid = _post(client, key, _report(family["burak_id"], "BURAK YILMAZ"))
    client.post("/api/app/unmapped/dismiss", json={"raw_name": ISTEM, "specimen": "blood"}, headers=H)
    assert client.delete(f"/api/app/reports/{rid}", headers=H).status_code == 200
    assert client.post(f"/api/app/reports/{rid}/restore", headers=H).status_code == 200
    rows = _detail(client, rid)[1]
    assert "Hemoglobin" in rows and ISTEM not in rows
    assert ISTEM not in _unmapped_names(client)


def test_dismissed_rows_not_relinked_by_alias(client, family):
    H, key = family["H"], family["key"]
    _post(client, key, _report(family["burak_id"], "BURAK YILMAZ"))
    client.post("/api/app/unmapped/dismiss", json={"raw_name": "Garip Test", "specimen": "blood"}, headers=H)
    r = client.post("/api/app/catalog/aliases", json={"raw_name": "Garip Test", "specimen": "blood", "test_key": "blood.mpv"},
                    headers=H)
    assert r.status_code == 201 and r.json()["linked_results"] == 0


def test_api_rules(client, family):
    key, limited = family["key"], family["limited_key"]
    rid = _post(client, key, _report(family["burak_id"], "BURAK YILMAZ"))
    _post(client, limited, _report(family["ayse_id"], "AYŞE YILMAZ"))
    det = client.get(f"/api/v1/reports/{rid}", headers=bearer(key)).json()
    by = {r["raw_name"]: r for p in det["panels"] for r in p["results"]}

    # GET /unmapped: üye kısıtına göre
    um = client.get("/api/v1/unmapped", headers=bearer(limited)).json()["items"]
    assert {g["raw_name"]: g["count"] for g in um}[ISTEM] == 1

    # Bağlı sonuç gizlenemez
    r = client.post("/api/v1/results/dismiss", json={"result_ids": [by["Hemoglobin"]["id"]]}, headers=bearer(key))
    assert r.status_code == 409 and r.json()["error"]["code"] == "RESULT_MAPPED"
    # Ya result_ids ya raw_name
    assert client.post("/api/v1/results/dismiss", json={"reason": "x yz"}, headers=bearer(key)).status_code == 400
    # Kısıtlı anahtar başka üyenin satırını gizleyemez
    r = client.post("/api/v1/results/dismiss", json={"result_ids": [by[ISTEM]["id"]]}, headers=bearer(limited))
    assert r.status_code == 403
    # Kısıtlı anahtarla ad bazında gizleme yalnızca kendi üyesini etkiler
    r = client.post("/api/v1/results/dismiss", json={"raw_name": ISTEM, "specimen": "blood"}, headers=bearer(limited))
    assert r.status_code == 200 and r.json()["dismissed_count"] == 1
    um = {g["raw_name"]: g for g in client.get("/api/v1/unmapped", headers=bearer(key)).json()["items"]}
    assert um[ISTEM]["result_ids"] == [by[ISTEM]["id"]]
    # Kimlikle gizle → tekrar gizlemek 409, geri al → tekrar geri almak 404
    r = client.post("/api/v1/results/dismiss", json={"result_ids": [by[ISTEM]["id"]], "reason": "istem satırı"}, headers=bearer(key))
    assert r.status_code == 200
    assert client.post("/api/v1/results/dismiss", json={"result_ids": [by[ISTEM]["id"]]}, headers=bearer(key)).status_code == 409
    assert client.post("/api/v1/results/restore", json={"result_ids": [by[ISTEM]["id"]]}, headers=bearer(key)).status_code == 200
    assert client.post("/api/v1/results/restore", json={"result_ids": [by[ISTEM]["id"]]}, headers=bearer(key)).status_code == 404


def test_mcp_dismiss_defaults_to_dry_run(client, family):
    key = family["key"]
    _post(client, key, _report(family["burak_id"], "BURAK YILMAZ"))

    def tool(name, args):
        r = client.post("/mcp", headers=bearer(key), json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                                           "params": {"name": name, "arguments": args}})
        return r.json()["result"]

    um = tool("list_unmapped", {})["structuredContent"]["items"]
    ids = next(g for g in um if g["raw_name"] == ISTEM)["result_ids"]
    pv = tool("dismiss_results", {"reason": "istem satırı", "result_ids": ids})["structuredContent"]
    assert pv["dry_run"] is True and pv["dismissed_count"] == 1
    assert any(g["raw_name"] == ISTEM for g in tool("list_unmapped", {})["structuredContent"]["items"])
    res = tool("dismiss_results", {"reason": "istem satırı", "result_ids": ids, "dry_run": False})
    assert not res["isError"], res
    assert not any(g["raw_name"] == ISTEM for g in tool("list_unmapped", {})["structuredContent"]["items"])
    assert not tool("restore_results", {"result_ids": ids})["isError"]
