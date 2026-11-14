"""Telegram botu: bağlama, yetki, butonlar, arama ve bildirim."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from sample_reports import family_practice_report


class FakeClient:
    def __init__(self):
        self.calls = []
        self._mid = 100

    def _rec(self, kind, chat_id, **kw):
        self._mid += 1
        self.calls.append({"kind": kind, "chat_id": chat_id, **kw})
        return {"message_id": self._mid}

    def call(self, method, **params):
        if method == "getMe":
            return {"username": "RimetraTestBot", "first_name": "Rimetra"}
        return True

    def send_message(self, chat_id, text, reply_markup=None):
        return self._rec("message", chat_id, text=text, markup=reply_markup)

    def edit_message(self, chat_id, message_id, text, reply_markup=None):
        return self._rec("edit", chat_id, text=text, markup=reply_markup)

    def answer_callback(self, callback_id, text=None):
        return self._rec("answer", None, text=text)

    def send_document(self, chat_id, filename, content, caption=None, reply_markup=None):
        return self._rec("document", chat_id, filename=filename, content=content, caption=caption)

    def send_photo(self, chat_id, content, caption=None, reply_markup=None):
        return self._rec("photo", chat_id, content=content, text=caption, markup=reply_markup)

    def send_chat_action(self, chat_id, action="typing"):
        pass

    def texts(self, chat_id=None):
        return [c.get("text") or "" for c in self.calls if chat_id is None or c["chat_id"] == chat_id]

    def last(self, chat_id=None):
        return [c for c in self.calls if c["kind"] != "answer" and (chat_id is None or c["chat_id"] == chat_id)][-1]


@pytest.fixture()
def tg(client, monkeypatch):
    from app.config import get_settings
    from app.services import telegram
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:TEST")
    get_settings.cache_clear()
    fake = FakeClient()
    telegram.reset_for_tests(fake)
    yield fake
    telegram.reset_for_tests(None)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN")
    get_settings.cache_clear()


def msg(chat_id, text, username="burak_tg"):
    return {"update_id": 1, "message": {"message_id": 5, "chat": {"id": chat_id, "type": "private"},
                                         "from": {"id": chat_id, "username": username}, "text": text}}


def cb(chat_id, data, message_id=55):
    return {"update_id": 2, "callback_query": {"id": "cb1", "data": data, "from": {"id": chat_id},
                                               "message": {"message_id": message_id, "chat": {"id": chat_id, "type": "private"}}}}


def send(fake, update):
    from app.services.telegram_bot import handle_update
    handle_update(fake, update)


def buttons(call):
    mk = call.get("markup") or {}
    return [b for row in mk.get("inline_keyboard", []) for b in row]


def post_report(client, key, body):
    return client.post("/api/v1/reports", json=body,
                       headers={"Authorization": f"Bearer {key}", "Idempotency-Key": str(uuid.uuid4())})


def link_master(client, fake, chat_id=1001):
    r = client.post("/api/app/telegram/link", headers={"x-rimetra": "1"})
    assert r.status_code == 200, r.text
    url = r.json()["url"]
    assert url.startswith("https://t.me/RimetraTestBot?start=")
    send(fake, msg(chat_id, "/start " + url.split("start=")[1]))
    return chat_id


def test_unknown_chat_gets_its_id(client, family, tg):
    send(tg, msg(777, "merhaba"))
    assert "777" in tg.texts(777)[-1]
    assert "bağlı değil" in tg.texts(777)[-1]
    # grup sohbetleri yok sayılır
    send(tg, {"update_id": 3, "message": {"chat": {"id": -5, "type": "group"}, "text": "hi"}})
    assert not tg.texts(-5)


def test_link_with_deep_link_and_status(client, family, tg):
    st = client.get("/api/app/telegram").json()
    assert st["enabled"] and not st["linked"] and st["bot_url"] == "https://t.me/RimetraTestBot"
    chat = link_master(client, tg)
    assert any("Bağlandı" in t for t in tg.texts(chat))
    me = client.get("/api/auth/me").json()
    assert me["telegram"]["linked"] and me["telegram"]["username"] == "burak_tg"
    # kod tek kullanımlık
    r = client.post("/api/app/telegram/link", headers={"x-rimetra": "1"}).json()
    code = r["code"]
    send(tg, msg(2002, "/start " + code))
    send(tg, msg(3003, "/start " + code))
    assert "geçersiz" in tg.texts(3003)[-1]
    # aynı hesap artık yeni sohbete taşındı; eski sohbet bağlı değil
    send(tg, msg(chat, "/menu"))
    assert "bağlı değil" in tg.texts(chat)[-1]
    # web'den bağlantıyı kaldır
    r = client.delete("/api/app/telegram", headers={"x-rimetra": "1"})
    assert r.json()["linked"] is False


def test_expired_code(client, family, tg):
    from app.db import SessionLocal
    from app.models import TelegramLinkCode
    code = client.post("/api/app/telegram/link", headers={"x-rimetra": "1"}).json()["code"]
    with SessionLocal() as db:
        for row in db.query(TelegramLinkCode):
            row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    send(tg, msg(4004, "/start " + code))
    assert "süresi dolmuş" in tg.texts(4004)[-1]


def test_member_sees_only_own_profile(client, family, tg):
    H = family["H"]
    u = client.post("/api/app/admin/users", headers=H, json={
        "username": "ayse", "password": "ayseninsifresi", "member_id": family["ayse_id"], "role": "member"}).json()
    r = client.patch(f"/api/app/admin/users/{u['id']}", headers=H, json={"telegram_chat_id": 5005})
    assert r.status_code == 200 and r.json()["telegram"]["linked"]
    post_report(client, family["key"], family_practice_report(family["burak_id"]))
    send(tg, msg(5005, "/menu"))
    assert "Ayşe" in tg.texts(5005)[-1]
    send(tg, cb(5005, f"m:{family['burak_id']}"))
    assert tg.calls[-1]["kind"] == "answer" and "yetki" in tg.calls[-1]["text"]
    send(tg, msg(5005, "burak crp"))  # Burak'ı göremez: Ayşe'nin verisinde arar
    assert "Ayşe" in tg.last(5005)["text"] and "24,6" not in tg.last(5005)["text"]
    # pasif kullanıcı artık bota erişemez
    client.patch(f"/api/app/admin/users/{u['id']}", headers=H, json={"is_active": False})
    send(tg, msg(5005, "/menu"))
    assert "bağlı değil" in tg.texts(5005)[-1]


def test_browse_search_and_pdf(client, family, tg):
    assert post_report(client, family["key"], family_practice_report(family["burak_id"])).status_code == 201
    chat = link_master(client, tg)
    # iki üye var: önce kişi seçimi
    assert "Kimin" in tg.last(chat)["text"]
    send(tg, cb(chat, f"m:{family['burak_id']}"))
    card = tg.last(chat)
    assert card["kind"] == "edit" and "Burak" in card["text"] and "referans dışı" in card["text"]

    send(tg, msg(chat, "⚠️ Referans dışı"))
    out = tg.last(chat)
    assert "Ürik Asit" in out["text"] and "CRP" in out["text"]
    assert "Hemoglobin" not in out["text"]

    send(tg, msg(chat, "🧾 Son rapor"))
    rep = tg.last(chat)
    assert "12.03.2025" in rep["text"] and "Hemoglobin" in rep["text"]

    send(tg, msg(chat, "ürik"))
    t = tg.last(chat)
    assert "Ürik Asit" in t["text"] and "8,6" in t["text"]
    assert any(b["callback_data"].startswith("ti:") for b in buttons(t))
    send(tg, cb(chat, next(b["callback_data"] for b in buttons(t) if b["callback_data"].startswith("ti:"))))
    assert "Yüksekse" in tg.last(chat)["text"]

    send(tg, msg(chat, "ayşe"))
    assert "Ayşe" in tg.last(chat)["text"] and "Henüz kayıtlı tahlil yok" in tg.last(chat)["text"]
    send(tg, msg(chat, "burak"))  # geri dön

    send(tg, msg(chat, "/pdf"))
    doc = [c for c in tg.calls if c["kind"] == "document"][-1]
    assert doc["content"][:5] == b"%PDF-"

    send(tg, msg(chat, "/degerler"))
    cats = tg.last(chat)
    assert buttons(cats)
    send(tg, cb(chat, buttons(cats)[0]["callback_data"]))
    assert "Son ölçülen" in tg.last(chat)["text"]

    send(tg, msg(chat, "xyzabc"))
    assert "bulamadım" in tg.last(chat)["text"]


def test_trend_chart_with_two_points(client, family, tg):
    body = family_practice_report(family["burak_id"])
    assert post_report(client, family["key"], body).status_code == 201
    body2 = family_practice_report(family["burak_id"])
    body2["report_date"] = "2026-02-10"
    for p in body2["panels"]:
        p["sample_datetime"] = "2026-02-10T09:00:00+03:00"
        for r in p["results"]:
            if r["raw_name"] == "CRP":
                r["raw_value"] = "3,1"
                r["source_flag"] = "ok"
    assert post_report(client, family["key"], body2).status_code == 201
    chat = link_master(client, tg)
    send(tg, msg(chat, "crp"))
    photo = tg.last(chat)
    assert photo["kind"] == "photo" and photo["content"][:8] == b"\x89PNG\r\n\x1a\n"
    assert "CRP" in photo["text"] and "3,1" in photo["text"] and "24,6" in photo["text"]
    # grafiğin altındaki "geri" butonu: fotoğraf düzenlenemez → yeni mesaj gelir (sahte istemci her zaman düzenler)
    send(tg, cb(chat, "s"))
    assert "Ayarlar" in tg.last(chat)["text"]
    send(tg, cb(chat, "sn"))
    assert client.get("/api/auth/me").json()["telegram"]["notify"] is False


def test_new_report_notification(client, family, tg):
    from app.services import telegram
    chat = link_master(client, tg)
    telegram.drain_outbox(tg)
    n = len(tg.calls)
    assert post_report(client, family["key"], family_practice_report(family["burak_id"])).status_code == 201
    assert telegram.drain_outbox(tg) == 1
    new = [c for c in tg.calls[n:] if c["kind"] == "message"]
    assert len(new) == 1 and new[0]["chat_id"] == chat
    assert "yeni tahlil" in new[0]["text"] and "referans dışı" in new[0]["text"]
    assert buttons(new[0])[0]["callback_data"].startswith("r:")
    # bildirimi kapatınca gelmez
    client.patch("/api/app/telegram", json={"notify": False}, headers={"x-rimetra": "1"})
    body = family_practice_report(family["ayse_id"])
    body["patient_name_on_document"] = "AYŞE YILMAZ"
    post_report(client, family["key"], body)
    n = len(tg.calls)
    telegram.drain_outbox(tg)
    assert not [c for c in tg.calls[n:] if c["kind"] == "message"]


def test_disabled_without_token(client, family):
    r = client.get("/api/app/telegram").json()
    assert r["enabled"] is False
    r = client.post("/api/app/telegram/link", headers={"x-rimetra": "1"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "TELEGRAM_DISABLED"


def test_chart_png():
    from app.services.telegram_chart import trend_png
    pts = [(datetime(2025, m, 1, tzinfo=timezone.utc), v, f) for m, v, f in
           [(1, 4.0, "normal"), (4, 6.5, "high"), (8, 5.1, "normal"), (11, 2.0, "low")]]
    png = trend_png("Ürik Asit", "mg/dL", pts, 3.4, 7.0)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    assert trend_png("x", None, pts[:1], None, None) is None


def test_doctor_pdf_contains_all_tests(client, family):
    import re
    from sample_reports import private_hospital_report
    post_report(client, family["key"], family_practice_report(family["burak_id"]))
    post_report(client, family["key"], private_hospital_report(family["burak_id"]))
    summary = client.get(f"/api/app/members/{family['burak_id']}/summary").json()
    assert summary["total_tests"] > 8
    pdf = client.get(f"/api/app/members/{family['burak_id']}/export.pdf")
    assert pdf.status_code == 200 and pdf.content[:5] == b"%PDF-"
    pages = len(re.findall(rb"/Type /Page\b(?!s)", pdf.content))
    rows = sum((n + 1) // 2 for n in _cat_counts(summary).values())
    assert pages >= 2 and rows * 168 > 700  # 8 testten fazlası tek sayfaya sığmaz, hepsi çizildi


def _cat_counts(summary):
    out = {}
    for i in summary["items"]:
        out[i["category"]] = out.get(i["category"], 0) + 1
    return out
