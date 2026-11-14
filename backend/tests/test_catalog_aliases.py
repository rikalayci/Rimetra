"""e-Nabız'ın gerçek raporlarda kullandığı ad varyantları kataloğa eşleşmeli."""
from sqlalchemy import delete, select

from app.db import SessionLocal
from app.models import Result
from app.models import TestAlias as AliasRow
from app.parsing import normalize_alias
from test_acceptance import by_name, post_report

T = "2025-03-12T09:12:00+03:00"

CASES = [
    # (numune, ham ad, değer, birim, beklenen test)
    ("serum", "Bilirubin Direkt", "0,25", "mg/dL", "serum.bili_direct"),
    ("serum", "Bilirubin Total", "0,70", "mg/dL", "serum.bili_total"),
    ("serum", "Demir BK Total", "275", "µg/dL", "serum.tibc"),
    ("urine", "Eritrosit (hemoglobin) Eritrosit (hemoglobin)", "Pozitif (+++)", None, "urine.blood"),
    ("blood", "Eritrosit sedimentasyon hızı (ESR)", "4", "mm/saat", "blood.esr"),
    ("blood", "HbA1c (NGSP)", "5.0", "%", "blood.hba1c"),
    ("urine", "Lökosit (esteraz) Lökosit (esteraz)", "Pozitif (+)", None, "urine.leukocyte_esterase"),
    ("blood", "Mentzer İndeksi", "15", None, "blood.mentzer"),
    ("serum", "PSA Serbest", "0.21", "µg/L", "serum.psa_free"),
    ("serum", "PSA Total", "0.67", "µg/L", "serum.psa_total"),
    ("serum", "tGFH", ">90", "mL/dk/1.73", "serum.egfr"),
    ("serum", "Üre Azotu", "13", "mg/dL", "serum.bun"),
]


def _report(member_id):
    panels = {}
    for sp, name, val, unit, _ in CASES:
        panels.setdefault(sp, []).append({"raw_name": name, "raw_value": val, "raw_unit": unit, "raw_reference": ""})
    return {
        "member_id": member_id, "source": "enabiz", "report_date": "2025-03-12", "facility": "TEST LAB",
        "patient_name_on_document": "BURAK YILMAZ",
        "panels": [{"name": None, "sample_datetime": T, "specimen": sp, "results": rs} for sp, rs in panels.items()],
    }


def test_enabiz_name_variants_match(client, family):
    r = post_report(client, family["key"], _report(family["burak_id"]))
    assert r.status_code in (200, 201), r.text
    res = r.json()["results"]
    for _, name, _, _, key in CASES:
        assert by_name(res, name)["test_key"] == key, name
    assert client.get("/api/app/unmapped").json()["items"] == []


def test_pending_results_relinked_on_startup(client, family):
    # Eski katalog durumunu taklit et: "Üre Azotu" alias'ı yokken gelen sonuç eşleşmemiş kalır
    with SessionLocal() as db:
        db.execute(delete(AliasRow).where(AliasRow.alias_normalized == normalize_alias("Üre Azotu")))
        db.commit()
    post_report(client, family["key"], _report(family["burak_id"]))
    um = client.get("/api/app/unmapped").json()["items"]
    assert [g["raw_name"] for g in um] == ["Üre Azotu"]
    # Öneri, ilk kelimesi tutan "Üre"yi değil BUN'u önce getirmeli (arayüzde ilk öneri seçili gelir)
    assert um[0]["suggestions"][0]["key"] == "serum.bun"

    from app.bootstrap import bootstrap
    bootstrap()  # seed eksik alias'ı geri ekler ve bekleyenleri bağlar
    assert client.get("/api/app/unmapped").json()["items"] == []
    with SessionLocal() as db:
        r = db.scalar(select(Result).where(Result.raw_name == "Üre Azotu"))
        assert r.test_definition_id is not None and r.value_numeric == 13


def test_suggestions_prefer_alias_over_first_word(client, family):
    body = _report(family["burak_id"])
    body["panels"] = [{"name": None, "sample_datetime": T, "specimen": "serum", "results": [
        {"raw_name": "Demir Bağlama Kapasitesi Toplam", "raw_value": "300", "raw_unit": "µg/dL", "raw_reference": ""}]}]
    post_report(client, family["key"], body)
    um = client.get("/api/app/unmapped").json()["items"]
    assert um[0]["suggestions"][0]["key"] in ("serum.tibc", "serum.uibc")


def test_rename_custom_test_key_and_specimen(client, family):
    """Yeni test penceresinde numune değişip anahtar 'serum.' kalırsa sonradan düzeltilebilmeli."""
    body = _report(family["burak_id"])
    body["panels"] = [{"name": None, "sample_datetime": T, "specimen": "serum", "results": [
        {"raw_name": "Homosistein", "raw_value": "12", "raw_unit": "µmol/L", "raw_reference": "5 - 15"}]}]
    post_report(client, family["key"], body)
    H = family["H"]
    # Numune "Kan" seçildi ama anahtar serum. kaldı; serum sonucu yine de bağlanmalı
    r = client.post("/api/app/catalog/tests?link_raw_name=Homosistein", headers=H, json={
        "key": "serum.homosistein", "display_name": "Homosistein", "specimen": "blood", "category": "Biyokimya",
        "canonical_unit": "µmol/L", "value_type": "numeric"})
    assert r.status_code == 201, r.text
    assert r.json()["linked"]["linked_results"] == 1

    r = client.patch("/api/app/catalog/tests/serum.homosistein", headers=H, json={"key": "blood.homosistein", "specimen": "blood"})
    assert r.status_code == 200, r.text
    assert r.json()["key"] == "blood.homosistein"
    hist = client.get(f"/api/app/members/{family['burak_id']}/tests/blood.homosistein/history")
    assert hist.status_code == 200 and "12" in hist.text

    # Yerleşik testin anahtarı değişmez; geçersiz/çakışan anahtar reddedilir
    client.patch("/api/app/catalog/tests/serum.bun", headers=H, json={"key": "serum.xyz"})
    assert client.get("/api/app/catalog").json()["items"] and any(t["key"] == "serum.bun" for t in client.get("/api/app/catalog").json()["items"])
    assert client.patch("/api/app/catalog/tests/blood.homosistein", headers=H, json={"key": "Kötü Anahtar"}).status_code == 400
    assert client.patch("/api/app/catalog/tests/blood.homosistein", headers=H, json={"key": "serum.bun"}).status_code == 409
