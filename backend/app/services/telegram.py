"""Telegram botu: Bot API istemcisi, uzun yoklama (long polling) döngüsü, bağlama kodları ve bildirimler.

Webhook yerine long polling kullanılır: sunucunun dışarıdan erişilebilir olması ya da HTTPS gerekmez,
evdeki Ubuntu makinesi Telegram'a kendisi bağlanır. Bot yalnızca TELEGRAM_BOT_TOKEN doluysa çalışır.
"""
from __future__ import annotations

import logging
import queue
import secrets
import threading
from datetime import timedelta

import httpx
from sqlalchemy import delete, select

from ..config import get_settings
from ..models import TelegramLinkCode, User, utcnow
from ..security import sha256_hex

log = logging.getLogger("rimetra.telegram")

LINK_CODE_MINUTES = 15


class TelegramError(Exception):
    def __init__(self, description: str, code: int | None = None, retry_after: int | None = None):
        super().__init__(description)
        self.description = description or ""
        self.code = code
        self.retry_after = retry_after


class TelegramClient:
    """Bot API'nin ihtiyaç duyulan küçük bir kısmı. Testlerde sahte bir istemciyle değiştirilir."""

    def __init__(self, token: str):
        self.base = f"https://api.telegram.org/bot{token}/"
        self.http = httpx.Client(timeout=httpx.Timeout(75.0, connect=15.0))

    def call(self, method: str, **params):
        params = {k: v for k, v in params.items() if v is not None}
        r = self.http.post(self.base + method, json=params)
        return self._result(r)

    def _result(self, r: httpx.Response):
        try:
            data = r.json()
        except ValueError:
            raise TelegramError(f"HTTP {r.status_code}", r.status_code) from None
        if not data.get("ok"):
            ra = (data.get("parameters") or {}).get("retry_after")
            raise TelegramError(data.get("description", "bilinmeyen hata"), data.get("error_code"), ra)
        return data["result"]

    def send_file(self, method: str, field: str, chat_id: int, filename: str, content: bytes, mime: str, **params):
        import json
        form = {"chat_id": str(chat_id)}
        for k, v in params.items():
            if v is None:
                continue
            form[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
        r = self.http.post(self.base + method, data=form, files={field: (filename, content, mime)})
        return self._result(r)

    # kısayollar
    def send_message(self, chat_id: int, text: str, reply_markup=None):
        return self.call("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML",
                         link_preview_options={"is_disabled": True}, reply_markup=reply_markup)

    def edit_message(self, chat_id: int, message_id: int, text: str, reply_markup=None):
        return self.call("editMessageText", chat_id=chat_id, message_id=message_id, text=text, parse_mode="HTML",
                         link_preview_options={"is_disabled": True}, reply_markup=reply_markup)

    def answer_callback(self, callback_id: str, text: str | None = None):
        return self.call("answerCallbackQuery", callback_query_id=callback_id, text=text)

    def send_document(self, chat_id: int, filename: str, content: bytes, caption: str | None = None, reply_markup=None):
        return self.send_file("sendDocument", "document", chat_id, filename, content, "application/pdf",
                              caption=caption, parse_mode="HTML" if caption else None, reply_markup=reply_markup)

    def send_photo(self, chat_id: int, content: bytes, caption: str | None = None, reply_markup=None):
        return self.send_file("sendPhoto", "photo", chat_id, "grafik.png", content, "image/png",
                              caption=caption, parse_mode="HTML" if caption else None, reply_markup=reply_markup)

    def send_chat_action(self, chat_id: int, action: str = "typing"):
        try:
            self.call("sendChatAction", chat_id=chat_id, action=action)
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------- durum (web arayüzünde gösterilir)

class _Status:
    def __init__(self) -> None:
        self.running = False
        self.bot_username: str | None = None
        self.bot_name: str | None = None
        self.last_error: str | None = None
        self.last_ok_at = None


status = _Status()
_client: TelegramClient | None = None
_outbox: queue.Queue = queue.Queue(maxsize=500)


def client() -> TelegramClient | None:
    global _client
    s = get_settings()
    if not s.telegram_enabled:
        return None
    if _client is None:
        _client = TelegramClient(s.telegram_bot_token.strip())
    return _client


def bot_username() -> str | None:
    if status.bot_username:
        return status.bot_username
    c = client()
    if c is None:
        return None
    try:
        me = c.call("getMe")
        status.bot_username, status.bot_name = me.get("username"), me.get("first_name")
        status.last_error = None
    except Exception as e:  # noqa: BLE001
        status.last_error = _describe(e)
    return status.bot_username


def _describe(e: Exception) -> str:
    if isinstance(e, TelegramError):
        if e.code == 401:
            return "Bot anahtarı (TELEGRAM_BOT_TOKEN) geçersiz."
        return f"Telegram: {e.description}"
    if isinstance(e, httpx.HTTPError):
        return "Telegram sunucusuna bağlanılamadı (internet bağlantısını kontrol edin)."
    return str(e)[:200]


def public_status() -> dict:
    s = get_settings()
    return {
        "enabled": s.telegram_enabled,
        "running": status.running,
        "bot_username": status.bot_username if s.telegram_enabled else None,
        "bot_name": status.bot_name if s.telegram_enabled else None,
        "last_error": status.last_error if s.telegram_enabled else None,
        "notify_enabled": s.telegram_notify,
    }


# ---------------------------------------------------------------- bağlama kodları

def create_link_code(db, user: User) -> tuple[str, int]:
    db.execute(delete(TelegramLinkCode).where(
        (TelegramLinkCode.user_id == user.id) | (TelegramLinkCode.expires_at < utcnow())))
    code = secrets.token_urlsafe(18).replace("-", "x").replace("_", "y")
    db.add(TelegramLinkCode(id=sha256_hex(code), user_id=user.id,
                            expires_at=utcnow() + timedelta(minutes=LINK_CODE_MINUTES)))
    db.commit()
    return code, LINK_CODE_MINUTES * 60


def consume_link_code(db, code: str) -> User | None:
    row = db.get(TelegramLinkCode, sha256_hex(code.strip()))
    if row is None:
        return None
    db.delete(row)
    if row.expires_at < utcnow():
        db.commit()
        return None
    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        db.commit()
        return None
    return user


def link_chat(db, user: User, chat_id: int, username: str | None) -> None:
    """Sohbeti kullanıcıya bağlar. Aynı sohbet başka bir hesaba bağlıysa oradan ayrılır."""
    for other in db.scalars(select(User).where(User.telegram_chat_id == chat_id, User.id != user.id)):
        other.telegram_chat_id = None
        other.telegram_username = None
        other.telegram_linked_at = None
    db.flush()
    user.telegram_chat_id = chat_id
    user.telegram_username = (username or None) and username[:64]
    user.telegram_linked_at = utcnow()
    user.telegram_member_id = None


def unlink_user(user: User) -> None:
    user.telegram_chat_id = None
    user.telegram_username = None
    user.telegram_linked_at = None
    user.telegram_member_id = None


# ---------------------------------------------------------------- bildirimler

def notify_new_report(report_id: str, actor_user_id: str | None = None) -> None:
    """Yeni rapor kaydedildikten sonra çağrılır; gönderim arka planda yapılır, isteği bekletmez."""
    s = get_settings()
    if not s.telegram_enabled or not s.telegram_notify:
        return
    if s.disable_scheduler and not _test_hook:  # testlerde gönderici iş parçacığı yok
        return
    try:
        _outbox.put_nowait(("report", report_id, actor_user_id))
    except queue.Full:
        log.warning("Telegram bildirim kuyruğu dolu; bildirim atlandı.")


_test_hook = False  # testler bildirimleri kuyruktan elle işlemek için açar


def _process(c: TelegramClient | None, item: tuple) -> None:
    from .telegram_bot import send_report_notification
    kind, ref, actor_user_id = item
    if c is None:
        return
    try:
        if kind == "report":
            send_report_notification(c, ref, actor_user_id)
    except Exception as e:  # noqa: BLE001
        log.warning("Telegram bildirimi gönderilemedi: %s", _describe(e))


def drain_outbox(c: TelegramClient | None = None) -> int:
    """Kuyruktaki bildirimleri hemen gönderir (testler kullanır)."""
    c = c or client()
    n = 0
    while True:
        try:
            item = _outbox.get_nowait()
        except queue.Empty:
            return n
        _process(c, item)
        n += 1


def _sender_loop(stop: threading.Event) -> None:
    while not stop.is_set():
        try:
            item = _outbox.get(timeout=2)
        except queue.Empty:
            continue
        _process(client(), item)


# ---------------------------------------------------------------- yoklama döngüsü

COMMANDS = [
    ("menu", "Ana menü"),
    ("kisi", "Kişi seç"),
    ("disi", "Referans dışı değerler"),
    ("son", "Son rapor"),
    ("raporlar", "Tüm raporlar"),
    ("degerler", "Tüm değerler (kategoriye göre)"),
    ("kontrol", "Kontrol hatırlatıcıları"),
    ("pdf", "Doktor için PDF özeti"),
    ("ayarlar", "Bildirimler ve bağlantı"),
    ("yardim", "Nasıl kullanılır?"),
]

# Telegram, kullanıcının uygulama dili İngilizceyse bu listeyi gösterir (komutların ikisi de çalışır).
COMMANDS_EN = [
    ("menu", "Main menu"),
    ("people", "Choose a person"),
    ("out", "Out-of-range values"),
    ("last", "Latest report"),
    ("reports", "All reports"),
    ("values", "All values (by category)"),
    ("checkups", "Check-up reminders"),
    ("pdf", "PDF summary for the doctor"),
    ("settings", "Notifications, language and link"),
    ("help", "How to use"),
]


def _poll_loop(stop: threading.Event) -> None:
    from .telegram_bot import handle_update
    c = client()
    if c is None:
        return
    status.running = True
    offset = None
    backoff = 2
    prepared = False
    while not stop.is_set():
        try:
            if not prepared:
                me = c.call("getMe")
                status.bot_username, status.bot_name = me.get("username"), me.get("first_name")
                c.call("deleteWebhook", drop_pending_updates=False)
                c.call("setMyCommands", commands=[{"command": k, "description": d} for k, d in COMMANDS])
                c.call("setMyCommands", commands=[{"command": k, "description": d} for k, d in COMMANDS_EN],
                       language_code="en")
                prepared = True
                log.info("Telegram botu çalışıyor: @%s", status.bot_username)
            updates = c.call("getUpdates", offset=offset, timeout=50, allowed_updates=["message", "callback_query"])
            status.last_error = None
            status.last_ok_at = utcnow()
            backoff = 2
            for u in updates:
                offset = u["update_id"] + 1
                try:
                    handle_update(c, u)
                except Exception:  # noqa: BLE001
                    log.exception("Telegram mesajı işlenemedi")
        except Exception as e:  # noqa: BLE001
            status.last_error = _describe(e)
            wait = backoff
            if isinstance(e, TelegramError):
                if e.retry_after:
                    wait = e.retry_after
                elif e.code == 401:
                    wait = 600
                elif e.code == 409:  # başka bir yerde aynı bot çalışıyor
                    status.last_error = "Bu bot başka bir yerde de çalışıyor (aynı token iki sunucuda kullanılamaz)."
                    wait = 30
            log.warning("Telegram: %s — %d sn sonra tekrar denenecek", status.last_error, wait)
            stop.wait(wait)
            backoff = min(backoff * 2, 60)
    status.running = False


def start(stop: threading.Event) -> None:
    if not get_settings().telegram_enabled:
        return
    threading.Thread(target=_poll_loop, args=(stop,), daemon=True, name="rimetra-telegram").start()
    threading.Thread(target=_sender_loop, args=(stop,), daemon=True, name="rimetra-telegram-send").start()


def reset_for_tests(c: TelegramClient | None = None) -> None:
    global _client, _test_hook
    _client = c
    _test_hook = c is not None
    status.bot_username = "RimetraTestBot" if c is not None else None
    while not _outbox.empty():
        _outbox.get_nowait()
