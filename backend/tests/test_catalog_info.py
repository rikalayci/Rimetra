"""Katalogdaki herkesin anlayacağı açıklamalar: seed, gösterim ve düzenleme."""
from app.catalog_info import CATALOG_INFO
from app.catalog_seed import CATALOG, seed_catalog
from app.db import SessionLocal


def test_every_builtin_test_has_info():
    keys = {row[0] for row in CATALOG}
    assert keys == set(CATALOG_INFO)
    for key, (what, low, high) in CATALOG_INFO.items():
        assert what and what.strip(), key
        assert low or high or key == "blood.abo_rh", key


def test_catalog_and_history_expose_info(client, family):
    H = family["H"]
    cat = client.get("/api/app/catalog", headers=H).json()["items"]
    wbc = next(t for t in cat if t["key"] == "blood.wbc")
    assert wbc["info_what"].startswith("Kandaki beyaz kan")
    assert wbc["info_low"] and wbc["info_high"]
    # ajan kataloğu açıklamaları taşımaz (bağlamı şişirmesin)
    agent = client.get("/api/v1/catalog/tests", headers={"Authorization": f"Bearer {family['key']}"}).json()["items"]
    assert "info_what" not in next(t for t in agent if t["key"] == "blood.wbc")


def test_user_edits_survive_reseed(client, family):
    H = family["H"]
    r = client.patch("/api/app/catalog/tests/blood.wbc", headers=H,
                     json={"info_what": "  Benim açıklamam  ", "info_low": ""})
    assert r.status_code == 200, r.text
    assert r.json()["info_what"] == "Benim açıklamam"
    with SessionLocal() as db:
        seed_catalog(db)
    wbc = next(t for t in client.get("/api/app/catalog", headers=H).json()["items"] if t["key"] == "blood.wbc")
    assert wbc["info_what"] == "Benim açıklamam"
    assert wbc["info_low"] == ""  # kasıtlı boşaltılan alan geri yazılmaz
    assert wbc["info_high"] == CATALOG_INFO["blood.wbc"][2]
    r = client.patch("/api/app/catalog/tests/blood.wbc", headers=H, json={"info_high": "x" * 4001})
    assert r.status_code == 400
