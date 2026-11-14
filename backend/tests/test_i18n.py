"""İngilizce dil desteği: hata mesajları, uyarılar, katalog adları/açıklamaları, dışa aktarım, tercih."""
import uuid

from sample_reports import family_practice_report
from test_acceptance import bearer, post_report

EN = {"X-Rimetra-Lang": "en"}


def test_error_messages_follow_language(client, family):
    anon = client.__class__(client.app)
    assert anon.get("/api/app/dashboard").json()["error"]["message"] == "Giriş yapmanız gerekiyor."
    assert anon.get("/api/app/dashboard", headers=EN).json()["error"]["message"] == "You need to sign in."
    r = anon.get("/api/app/dashboard", headers={"Accept-Language": "en-US,en;q=0.9"})
    assert r.json()["error"]["message"] == "You need to sign in."
    r = anon.get("/api/app/dashboard", headers={"Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5"})
    assert r.json()["error"]["message"] == "Giriş yapmanız gerekiyor."
    # dinamik (f-string) mesajlar ve iç içe "fields" mesajları
    r = client.get("/api/v1/members/mbr_yok/summary", headers={**bearer(family["key"]), **EN})
    assert r.status_code == 404 and r.json()["error"]["message"] == "Member not found."
    body = family_practice_report(family["ayse_id"])  # belgede BURAK yazıyor
    r = client.post("/api/v1/reports", json=body, headers={**bearer(family["key"]), **EN, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 422
    assert r.json()["error"]["message"].startswith("The name on the document ('BURAK YILMAZ')")
    only_dot = {**body, "member_id": family["burak_id"], "panels": [{**body["panels"][1], "results": [body["panels"][1]["results"][-1]]}]}
    r = client.post("/api/v1/reports", json=only_dot,
                    headers={**bearer(family["key"]), **EN, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 400 and r.json()["error"]["message"] == "The report has no results to save."
    assert r.json()["error"]["fields"][0]["message"] == "Empty"


def test_warnings_and_catalog_in_english(client, family):
    body = family_practice_report(family["burak_id"])
    r = client.post("/api/v1/reports?dry_run=true", json=body,
                    headers={**bearer(family["key"]), **EN, "Idempotency-Key": str(uuid.uuid4())})
    assert r.status_code == 200, r.text
    msgs = {w["code"]: w["message"] for w in r.json()["warnings"]}
    assert msgs["SKIPPED_PLACEHOLDER"] == "Row skipped because the value is '.' (placeholder)."
    assert post_report(client, family["key"], body).status_code == 201

    s = client.get(f"/api/app/members/{family['burak_id']}/summary", headers=EN).json()
    names = {i["test_key"]: i for i in s["items"]}
    assert names["blood.wbc"]["display_name"] == "White Blood Cells (WBC)"
    assert names["blood.wbc"]["category"] == "Hemogram"  # kategori anahtarı değişmez; arayüz çevirir
    s_tr = client.get(f"/api/app/members/{family['burak_id']}/summary").json()
    assert {i["test_key"]: i for i in s_tr["items"]}["blood.wbc"]["display_name"] == "Lökosit (WBC)"

    h = client.get(f"/api/app/members/{family['burak_id']}/tests/serum.uric_acid/history", headers=EN).json()
    assert h["test"]["display_name"] == "Uric Acid" and h["test"]["display_name_raw"] == "Ürik Asit"
    assert h["test"]["info_what"].startswith("A waste product") and h["test"]["info_what_raw"].startswith("Vücutta")


def test_edited_catalog_text_is_kept(client, family):
    H = {"x-rimetra": "1"}
    cat = client.get("/api/app/catalog").json()["items"]
    crp = next(i for i in cat if i["key"] == "serum.crp")
    r = client.patch(f"/api/app/catalog/tests/{crp['key']}", headers=H, json={"display_name": "CRP (benim adım)", "info_what": "Kendi notum."})
    assert r.status_code == 200, r.text
    cat_en = client.get("/api/app/catalog", headers=EN).json()["items"]
    crp_en = next(i for i in cat_en if i["key"] == "serum.crp")
    assert crp_en["display_name"] == "CRP (benim adım)" and crp_en["info_what"] == "Kendi notum."
    assert crp_en["info_low"].startswith("A low value is normal")  # düzenlenmeyen alan yine çevrilir


def test_exports_in_english(client, family):
    post_report(client, family["key"], family_practice_report(family["burak_id"]))
    csv = client.get(f"/api/app/members/{family['burak_id']}/export.csv?lang=en").content.decode("utf-8-sig")
    head, first = csv.splitlines()[:2]
    assert head.startswith("Person;Category;Test;Test key")
    assert "Complete Blood Count" in csv and "White Blood Cells (WBC)" in csv and "12 Mar 2025" in csv
    assert "8.6" in csv and "8,6" not in csv
    pdf = client.get(f"/api/app/members/{family['burak_id']}/export.pdf?lang=en")
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_language_preference_saved(client, family):
    r = client.patch("/api/auth/prefs", headers={"x-rimetra": "1"}, json={"lang": "en"})
    assert r.status_code == 200 and r.json()["lang"] == "en"
    assert client.get("/api/auth/me").json()["lang"] == "en"
    r = client.patch("/api/auth/prefs", headers={"x-rimetra": "1"}, json={"lang": "xx"})
    assert r.json()["lang"] is None


# ---------------------------------------------------------------- Telegram
from test_telegram import FakeClient, buttons, cb, link_master, msg, send, tg  # noqa: E402,F401


def _msg_en(chat_id, text):
    m = msg(chat_id, text)
    m["message"]["from"]["language_code"] = "en"
    return m


def test_telegram_follows_language(client, family, tg):
    # bağlı olmayan, Telegram dili İngilizce olan kullanıcı
    send(tg, _msg_en(778, "hello"))
    assert "not linked yet" in tg.texts(778)[-1] and "778" in tg.texts(778)[-1]

    post_report(client, family["key"], family_practice_report(family["burak_id"]))
    chat = link_master(client, tg)
    send(tg, msg(chat, "/menu"))
    assert "Kimin" in tg.last(chat)["text"]  # tercih yok, Telegram dili yok → Türkçe

    # Ayarlar → English
    send(tg, cb(chat, "lg:en"))
    assert client.get("/api/auth/me").json()["lang"] == "en"
    assert any("Language changed: English" in (c.get("text") or "") for c in tg.calls)
    send(tg, msg(chat, "/out"))
    out = tg.last(chat)["text"]
    assert "latest out-of-range values" in out and "Uric Acid" in out and "8.6" in out
    send(tg, msg(chat, "⚠️ Out of range"))  # İngilizce kalıcı buton
    assert "latest out-of-range values" in tg.last(chat)["text"]
    send(tg, msg(chat, "⚠️ Referans dışı"))  # eski (Türkçe) klavye de çalışır
    assert "latest out-of-range values" in tg.last(chat)["text"]
    send(tg, msg(chat, "uric acid"))  # İngilizce adla arama
    assert "Uric Acid" in tg.last(chat)["text"]

    send(tg, cb(chat, "lg:tr"))
    send(tg, msg(chat, "/disi"))
    assert "referans dışı son değerler" in tg.last(chat)["text"]
