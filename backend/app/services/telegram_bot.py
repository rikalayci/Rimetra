"""Telegram botunun konuşma mantığı: komutlar, butonlar, serbest metinle test arama ve bildirim metinleri.

Bot yalnızca OKUR: hiçbir veri değiştirmez (bağlantı ve dil ayarları hariç). Her mesaj, sohbetin bağlı olduğu
Rimetra kullanıcısının yetkileriyle yanıtlanır — master herkesi, üye yalnızca kendi profilini görür.
Dil: kullanıcının Rimetra'daki tercihi; yoksa Telegram uygulamasının dili; yoksa Türkçe.
"""
from __future__ import annotations

import html
import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..db import SessionLocal
from ..deps import Actor, actor_for_user
from ..i18n import fdate as _fdate
from ..i18n import is_en, lang_from_accept, normalize_lang, t, tcat, tinfo, tname, tunit, use_lang
from ..models import Member, Report, Result, TestAlias, TestDefinition, User
from ..parsing import fold
from ..security import rate_limiter
from . import queries, telegram
from .audit import audit
from .export import _ref, _val
from .ingest import local_tz

log = logging.getLogger("rimetra.telegram")

MAX_TEXT = 3900
OUT = ("low", "high", "abnormal")
FLAG_ICON = {"high": "🔺", "low": "🔻", "abnormal": "❗", "normal": "✅", "unknown": "▫️"}
_FLAG_WORD = {"high": "yüksek", "low": "düşük", "abnormal": "anormal", "normal": "normal"}

# alttaki kalıcı klavye — mesaj yazmadan her şeye bir dokunuşla ulaşılır
_BTN = {
    "out": "⚠️ Referans dışı", "last": "🧾 Son rapor", "reports": "📋 Raporlar",
    "all": "📈 Tüm değerler", "people": "👥 Kişi seç", "remind": "⏰ Kontroller",
}


def flag_word(flag: str | None) -> str:
    if flag == "unknown":
        return "—"
    return t(_FLAG_WORD[flag]) if flag in _FLAG_WORD else ""


def main_kb() -> dict:
    b = {k: t(v) for k, v in _BTN.items()}
    return {
        "keyboard": [[b["out"], b["last"]], [b["reports"], b["all"]], [b["people"], b["remind"]]],
        "resize_keyboard": True,
        "is_persistent": True,
        "input_field_placeholder": t("Test adı yazın: ferritin, şeker, tsh…"),
    }


def _button_ops() -> dict[str, str]:
    """Kalıcı klavye metni → işlem; her iki dildeki metinler de tanınır (dil değişince eski klavye kalabilir)."""
    out = {}
    for lang in ("tr", "en"):
        with use_lang(lang):
            out.update({t(v): k for k, v in _BTN.items()})
    return out


def help_text() -> str:
    if is_en():
        return (
            "<b>How to use the Rimetra bot</b>\n\n"
            "• The buttons below get you anywhere in one tap.\n"
            "• Type a <b>test name</b> and I'll show its history with a chart: <i>ferritin</i>, <i>hba1c</i>, <i>b12</i>, <i>tsh</i>…\n"
            "• You can put a <b>person's name</b> first: <i>ayşe ferritin</i>. Type just the name to switch to that person.\n"
            "• You get a message when a new lab result is added (can be turned off in /settings).\n\n"
            "Commands: /menu · /people · /out · /last · /reports · /values · /checkups · /pdf · /settings"
        )
    return (
        "<b>Rimetra botu nasıl kullanılır?</b>\n\n"
        "• Alttaki butonlarla her şeye tek dokunuşla ulaşırsınız.\n"
        "• Bir <b>test adı</b> yazın, geçmişini grafikle göstereyim: <i>ferritin</i>, <i>hba1c</i>, <i>b12</i>, <i>tsh</i>…\n"
        "• Başına <b>kişi adı</b> ekleyebilirsiniz: <i>ayşe ferritin</i>. Sadece adı yazarsanız o kişiye geçerim.\n"
        "• Yeni bir tahlil eklendiğinde size mesaj gelir (/ayarlar'dan kapatılabilir).\n\n"
        "Komutlar: /menu · /kisi · /disi · /son · /raporlar · /degerler · /kontrol · /pdf · /ayarlar"
    )


def esc(s) -> str:
    return html.escape(str(s or ""), quote=False)


def fdate(d) -> str:
    if d is None:
        return "—"
    if isinstance(d, str):
        d = datetime.fromisoformat(d)
    if isinstance(d, datetime):
        d = d.astimezone(local_tz()) if d.tzinfo else d
    return _fdate(d)


def pct(v: float) -> str:
    s = f"{v:+.0f}%"
    return s if is_en() else s.replace(".", ",")


def btn(text: str, data: str) -> dict:
    return {"text": text, "callback_data": data[:64]}


def kb(*rows) -> dict:
    return {"inline_keyboard": [list(r) for r in rows if r]}


def rows_of(buttons: list[dict], per_row: int = 2) -> list[list[dict]]:
    return [buttons[i:i + per_row] for i in range(0, len(buttons), per_row)]


def value_line(r: Result, td: TestDefinition | None = None, with_name: bool = True, with_ref: bool = True) -> str:
    td = td or r.test_definition
    name = tname(td) if td else r.raw_name
    unit = tunit(r.unit_canonical or r.unit_raw)
    val = _val(r) + (f" {unit}" if unit else "")
    ref = _ref(r) if with_ref else ""
    s = FLAG_ICON.get(r.flag_computed, "▫️") + " "
    if with_name:
        s += f"<b>{esc(name)}</b>: "
    s += esc(val)
    if ref:
        s += f"  <i>(ref {esc(ref)})</i>"
    return s


def user_lang(user: User | None, telegram_code: str | None = None) -> str:
    """Kullanıcının dili: Rimetra tercihi > Telegram uygulama dili > Türkçe."""
    return (user.lang if user and user.lang else None) or lang_from_accept(telegram_code) or "tr"


# ---------------------------------------------------------------- bağlam

@dataclass
class Ctx:
    c: telegram.TelegramClient
    db: Session
    chat_id: int
    user: User
    actor: Actor
    members: list[Member]
    message_id: int | None = None  # buton tıklamasında düzenlenecek mesaj
    sent: list = field(default_factory=list)

    def member(self, mid: str | None = None) -> Member | None:
        by_id = {m.id: m for m in self.members}
        for cand in (mid, self.user.telegram_member_id, self.user.member_id):
            if cand and cand in by_id:
                return by_id[cand]
        return self.members[0] if self.members else None

    def remember(self, m: Member) -> None:
        if self.user.telegram_member_id != m.id:
            self.user.telegram_member_id = m.id
            self.db.commit()

    def show(self, text: str, markup: dict | None = None, edit: bool = True) -> None:
        if edit and self.message_id and len(text) <= MAX_TEXT:
            try:
                self.c.edit_message(self.chat_id, self.message_id, text, markup)
                return
            except telegram.TelegramError as e:
                if "not modified" in e.description:
                    return
                # fotoğraf mesajı ya da çok eski mesaj: yenisini gönder
        chunks = split_text(text)
        for i, chunk in enumerate(chunks):
            self.c.send_message(self.chat_id, chunk, markup if i == len(chunks) - 1 else None)

    def send(self, text: str, markup: dict | None = None) -> None:
        self.message_id = None
        self.show(text, markup, edit=False)


def split_text(text: str) -> list[str]:
    if len(text) <= MAX_TEXT:
        return [text]
    out, cur = [], ""
    for line in text.split("\n"):
        if len(cur) + len(line) + 1 > MAX_TEXT and cur:
            out.append(cur.rstrip("\n"))
            cur = ""
        cur += line + "\n"
    if cur.strip():
        out.append(cur.rstrip("\n"))
    return out


# ---------------------------------------------------------------- giriş noktası

def handle_update(c: telegram.TelegramClient, u: dict) -> None:
    with SessionLocal() as db:
        if "callback_query" in u:
            cq = u["callback_query"]
            chat_id = ((cq.get("message") or {}).get("chat") or {}).get("id") or (cq.get("from") or {}).get("id")
            code = (cq.get("from") or {}).get("language_code")
            with use_lang(user_lang(_linked_user(db, chat_id) if chat_id else None, code)):
                _on_callback(c, db, cq)
        elif "message" in u:
            msg = u["message"]
            chat_id = (msg.get("chat") or {}).get("id")
            code = (msg.get("from") or {}).get("language_code")
            with use_lang(user_lang(_linked_user(db, chat_id) if chat_id else None, code)):
                _on_message(c, db, msg)


def _linked_user(db: Session, chat_id: int) -> User | None:
    user = db.scalar(select(User).where(User.telegram_chat_id == chat_id))
    if user is None or not user.is_active:
        return None
    return user


def _ctx(c, db, chat_id: int, user: User, message_id: int | None = None) -> Ctx:
    from .ops import visible_members
    actor = actor_for_user(user, "telegram")
    actor.label = f"{user.username} (Telegram)"
    return Ctx(c, db, chat_id, user, actor, visible_members(db, actor), message_id)


def _not_linked(c, chat_id: int) -> None:
    ok, _ = rate_limiter.allow(f"tg-unknown:{chat_id}", 3)
    if not ok:
        return
    c.send_message(chat_id, t(
        "Merhaba! 👋 Bu bot <b>Rimetra</b> aile tahlil sistemine bağlıdır ve hesabınız henüz bağlı değil.\n\n"
        "Telegram ID'niz: <code>{chat_id}</code>\n\n"
        "<b>Bağlamak için:</b> Rimetra'yı açın → sağ üstteki profil resminize dokunun → "
        "<b>Telegram'ı bağla</b>. Açılan bağlantıya dokunmanız yeterli.\n"
        "Ya da yukarıdaki ID'yi Rimetra yöneticisine verin, hesabınıza eklesin.", chat_id=chat_id,
    ), {"remove_keyboard": True})


_ROUTES = {
    # Türkçe komutlar
    "/menu": "home", "/kisi": "people", "/disi": "out", "/son": "last", "/raporlar": "reports",
    "/degerler": "all", "/kontrol": "remind", "/pdf": "pdf", "/ayarlar": "settings", "/yardim": "help",
    # İngilizce komutlar
    "/people": "people", "/out": "out", "/last": "last", "/reports": "reports", "/values": "all",
    "/checkups": "remind", "/settings": "settings", "/help": "help",
}


def _on_message(c, db: Session, msg: dict) -> None:
    chat = msg.get("chat") or {}
    if chat.get("type") != "private":
        return
    chat_id = chat["id"]
    text = (msg.get("text") or "").strip()
    sender = msg.get("from") or {}

    if text.startswith("/start "):
        code = text.split(maxsplit=1)[1].strip()
        user = telegram.consume_link_code(db, code)
        if user is None:
            db.commit()
            if _linked_user(db, chat_id):
                c.send_message(chat_id, t("Bu bağlantının süresi dolmuş, ama bu sohbet zaten bağlı. /menu"), main_kb())
            else:
                c.send_message(chat_id, t("Bu bağlantı geçersiz ya da süresi dolmuş (15 dk). Rimetra'dan yeni bir bağlantı alın."))
            return
        telegram.link_chat(db, user, chat_id, sender.get("username"))
        audit(db, actor_for_user(user, "telegram"), "telegram.link", "user", user.id,
              {"telegram_username": sender.get("username")})
        db.commit()
        with use_lang(user_lang(user, sender.get("language_code"))):
            ctx = _ctx(c, db, chat_id, user)
            name = user.member.display_name if user.member else user.username
            ctx.send(t("✅ Bağlandı! Hoş geldin <b>{name}</b>.", name=esc(name)) + "\n\n" + help_text(), main_kb())
            _home(ctx)
        return

    user = _linked_user(db, chat_id)
    if user is None:
        _not_linked(c, chat_id)
        return
    ok, _ = rate_limiter.allow(f"tg:{chat_id}", 40)
    if not ok:
        return
    if sender.get("username") and sender["username"] != user.telegram_username:
        user.telegram_username = sender["username"][:64]
        db.commit()
    ctx = _ctx(c, db, chat_id, user)
    if not ctx.members:
        ctx.send(t("Hesabınıza bağlı bir profil yok. Rimetra yöneticisinden profil bağlamasını isteyin."))
        return
    if not text:
        ctx.send(t("Bir test adı yazın (ör. <i>ferritin</i>) ya da alttaki butonları kullanın."), main_kb())
        return

    cmd = text.split()[0].split("@")[0].lower() if text.startswith("/") else None
    m = ctx.member()
    actions = {
        "start": lambda: (ctx.send(t("Hazırım! 👇"), main_kb()), _home(ctx)),
        "home": lambda: _home(ctx), "people": lambda: _people(ctx),
        "out": lambda: _out_of_range(ctx, m), "last": lambda: _last_report(ctx, m),
        "reports": lambda: _reports(ctx, m, 0), "all": lambda: _categories(ctx, m),
        "remind": lambda: _reminders(ctx, m), "pdf": lambda: _doctor_pdf(ctx, m),
        "settings": lambda: _settings(ctx), "help": lambda: ctx.send(help_text(), main_kb()),
    }
    buttons = _button_ops()
    if cmd:
        op = "start" if cmd == "/start" else _ROUTES.get(cmd)
        (actions.get(op) or (lambda: ctx.send(t("Bu komutu tanımıyorum. /yardim"), main_kb())))()
    elif text in buttons:
        actions[buttons[text]]()
    else:
        _free_text(ctx, text)


def _on_callback(c, db: Session, cq: dict) -> None:
    msg = cq.get("message") or {}
    chat_id = (msg.get("chat") or {}).get("id") or (cq.get("from") or {}).get("id")
    user = _linked_user(db, chat_id) if chat_id else None
    if user is None:
        c.answer_callback(cq["id"], t("Bu sohbet bir Rimetra hesabına bağlı değil."))
        return
    ok, _ = rate_limiter.allow(f"tg:{chat_id}", 40)
    if not ok:
        c.answer_callback(cq["id"], t("Biraz yavaş 🙂"))
        return
    ctx = _ctx(c, db, chat_id, user, msg.get("message_id"))
    data = cq.get("data") or ""
    toast = None
    try:
        toast = _dispatch(ctx, data)
    except PermissionError:
        toast = t("Buna erişim yetkiniz yok.")
    finally:
        try:
            c.answer_callback(cq["id"], toast)
        except Exception:  # noqa: BLE001
            pass


def _dispatch(ctx: Ctx, data: str) -> str | None:
    parts = data.split(":")
    op, args = parts[0], parts[1:]

    def mem(i: int = 0) -> Member:
        mid = args[i] if len(args) > i else None
        m = ctx.member(mid)
        if mid and (m is None or m.id != mid):
            raise PermissionError
        return m

    if op == "home":
        _home(ctx)
    elif op == "p":
        _people(ctx)
    elif op == "m":
        _member_card(ctx, mem())
    elif op == "o":
        _out_of_range(ctx, mem())
    elif op == "last":
        _last_report(ctx, mem())
    elif op == "r":
        _report(ctx, _report_obj(ctx, args[0]))
    elif op == "rp":
        _report_pdf(ctx, _report_obj(ctx, args[0]))
        return t("PDF gönderiliyor…")
    elif op == "l":
        _reports(ctx, mem(), int(args[1]) if len(args) > 1 else 0)
    elif op == "c":
        _categories(ctx, mem())
    elif op == "cc":
        _category(ctx, mem(), int(args[1]))
    elif op == "t":
        _test(ctx, mem(), args[1])
    elif op == "ti":
        _test_info(ctx, mem(), args[1])
    elif op == "k":
        _reminders(ctx, mem())
    elif op == "x":
        _doctor_pdf(ctx, mem())
        return t("PDF hazırlanıyor…")
    elif op == "s":
        _settings(ctx)
    elif op == "sn":
        ctx.user.telegram_notify = not ctx.user.telegram_notify
        audit(ctx.db, ctx.actor, "telegram.notify", "user", ctx.user.id, {"notify": ctx.user.telegram_notify})
        ctx.db.commit()
        _settings(ctx)
        return t("Bildirimler açıldı") if ctx.user.telegram_notify else t("Bildirimler kapatıldı")
    elif op == "lg":
        new = normalize_lang(args[0] if args else None) or ("tr" if is_en() else "en")
        ctx.user.lang = new
        ctx.db.commit()
        with use_lang(new):
            _settings(ctx)
            ctx.c.send_message(ctx.chat_id, t("Dil değiştirildi: Türkçe 🇹🇷"), main_kb())
            return t("Dil değiştirildi: Türkçe 🇹🇷")
    elif op == "su":
        ctx.show(t("Bu sohbetin Rimetra bağlantısı kaldırılsın mı? Tekrar bağlamak için web arayüzünden yeni bağlantı almanız gerekir."),
                 kb([btn(t("Evet, bağlantıyı kaldır"), "suy"), btn(t("Vazgeç"), "s")]))
    elif op == "suy":
        audit(ctx.db, ctx.actor, "telegram.unlink", "user", ctx.user.id, {"by": "telegram"})
        telegram.unlink_user(ctx.user)
        ctx.db.commit()
        ctx.show(t("Bağlantı kaldırıldı. Görüşmek üzere 👋"))
        ctx.c.send_message(ctx.chat_id, t("Klavye kaldırıldı."), {"remove_keyboard": True})
    else:
        return t("Bu buton artık geçerli değil.")
    return None


def _report_obj(ctx: Ctx, rid: str) -> Report:
    rep = ctx.db.scalar(select(Report).options(selectinload(Report.facility)).where(Report.id == rid))
    if rep is None or rep.deleted_at is not None or not ctx.actor.can_access_member(rep.member_id):
        raise PermissionError
    return rep


# ---------------------------------------------------------------- ekranlar

def _home(ctx: Ctx) -> None:
    if len(ctx.members) > 1 and not ctx.user.telegram_member_id:
        _people(ctx)
    else:
        _member_card(ctx, ctx.member())


def _people(ctx: Ctx) -> None:
    dash = queries.family_dashboard(ctx.db, ctx.members)
    if len(dash) == 1:
        _member_card(ctx, ctx.members[0])
        return
    lines = [t("👥 <b>Kimin sonuçlarına bakalım?</b>"), ""]
    buttons = []
    for d in dash:
        extra = []
        if d["last_report_date"]:
            extra.append(t("son tahlil {date}", date=fdate(d["last_report_date"])))
        if d["last_report_out_of_range"]:
            extra.append(t("⚠️ {n} referans dışı", n=d["last_report_out_of_range"]))
        if d["reminders_due"]:
            extra.append(t("⏰ {n} kontrol", n=d["reminders_due"]))
        lines.append(f"• <b>{esc(d['display_name'])}</b>" + (" — " + ", ".join(extra) if extra else " — " + t("henüz tahlil yok")))
        label = d["display_name"] + (f"  ⚠️{d['last_report_out_of_range']}" if d["last_report_out_of_range"] else "")
        buttons.append(btn(label, f"m:{d['id']}"))
    ctx.show("\n".join(lines), kb(*rows_of(buttons, 2)))


def _member_kb(ctx: Ctx, m: Member, out_count: int) -> dict:
    out_label = t("⚠️ Referans dışı")
    rows = [
        [btn(f"{out_label} ({out_count})" if out_count else out_label, f"o:{m.id}"),
         btn(t("🧾 Son rapor"), f"last:{m.id}")],
        [btn(t("📋 Raporlar"), f"l:{m.id}:0"), btn(t("📈 Tüm değerler"), f"c:{m.id}")],
        [btn(t("⏰ Kontroller"), f"k:{m.id}"), btn(t("📄 Doktor PDF'i"), f"x:{m.id}")],
    ]
    if len(ctx.members) > 1:
        rows.append([btn(t("👥 Kişi değiştir"), "p")])
    return kb(*rows)


def _member_card(ctx: Ctx, m: Member) -> None:
    ctx.remember(m)
    s = queries.member_summary(ctx.db, m.id)
    due = [r for r in queries.reminders_status(ctx.db, m.id) if r["status"] in ("due", "never")]
    lines = [f"👤 <b>{esc(m.display_name)}</b>", ""]
    if not s["report_count"]:
        lines.append(t("Henüz kayıtlı tahlil yok."))
    else:
        lines.append(t("🧾 Son tahlil: <b>{date}</b>  ·  {reports} rapor, {tests} test",
                       date=fdate(s["last_report_date"]), reports=s["report_count"], tests=s["total_tests"]))
        if s["out_of_range"]:
            lines.append(t("⚠️ Son değerlerde <b>{n}</b> referans dışı:", n=s["out_of_range"]))
            outs = [i for i in s["items"] if i["latest"]["flag_computed"] in OUT]
            for i in outs[:6]:
                lt = i["latest"]
                arrow = FLAG_ICON.get(lt["flag_computed"], "")
                lines.append(f"   {arrow} {esc(i['display_name'])}")
            if len(outs) > 6:
                lines.append("   " + t("… ve {n} tane daha", n=len(outs) - 6))
        else:
            lines.append(t("✅ Son değerlerin hepsi referans aralığında."))
    if due:
        lines.append(t("⏰ Zamanı gelen kontrol: ") + ", ".join(esc(d["display_name"]) for d in due[:4]))
    lines += ["", t("<i>Bir test adı yazarak da arayabilirsiniz (ör. ferritin).</i>")]
    ctx.show("\n".join(lines), _member_kb(ctx, m, s["out_of_range"]))


def _back(m: Member) -> list[dict]:
    return [btn("🔙 " + m.display_name, f"m:{m.id}")]


def _out_of_range(ctx: Ctx, m: Member) -> None:
    ctx.remember(m)
    s = queries.member_summary(ctx.db, m.id)
    outs = [i for i in s["items"] if i["latest"]["flag_computed"] in OUT]
    if not outs:
        ctx.show(t("✅ <b>{name}</b>: son ölçümlerin hepsi referans aralığında.", name=esc(m.display_name)), kb(_back(m)))
        return
    lines = [t("⚠️ <b>{name} — referans dışı son değerler</b>", name=esc(m.display_name)), ""]
    buttons = []
    for i in outs:
        lt = i["latest"]
        r = ctx.db.get(Result, lt["id"])
        line = value_line(r) + f"\n      <i>{fdate(lt['sample_datetime'])}</i>"
        if i["consecutive_out"]:
            line += " · " + t("<b>üst üste 2+ rapor</b>")
        if i["change_pct"] is not None:
            line += " · " + t("önceki: {pct}", pct=pct(i["change_pct"]))
        lines.append(line)
        buttons.append(btn(f"📈 {i['display_name']}", f"t:{m.id}:{lt_td_id(ctx, i)}"))
    lines += ["", t("<i>Grafik için bir teste dokunun.</i>")]
    ctx.show("\n".join(lines), kb(*rows_of(buttons[:16], 2), _back(m)))


def lt_td_id(ctx: Ctx, item: dict) -> str:
    td = ctx.db.scalar(select(TestDefinition.id).where(TestDefinition.key == item["test_key"]))
    return td or ""


def _member_report_ids(ctx: Ctx, m: Member) -> list[str]:
    return list(ctx.db.scalars(select(Report.id).where(Report.member_id == m.id, Report.deleted_at.is_(None))
                               .order_by(Report.report_date.desc(), Report.created_at.desc())))


def _no_reports(ctx: Ctx, m: Member) -> None:
    ctx.show(t("<b>{name}</b> için kayıtlı tahlil yok.", name=esc(m.display_name)), kb(_back(m)))


def _last_report(ctx: Ctx, m: Member) -> None:
    ctx.remember(m)
    ids = _member_report_ids(ctx, m)
    if not ids:
        _no_reports(ctx, m)
        return
    _report(ctx, _report_obj(ctx, ids[0]))


def _count_line(total: int, out: int) -> str:
    s = t("{n} sonuç", n=total)
    return s + (" · " + t("⚠️ <b>{n}</b> referans dışı", n=out) if out else " · " + t("✅ hepsi normal"))


def _report(ctx: Ctx, rep: Report) -> None:
    m = ctx.db.get(Member, rep.member_id)
    d = queries.report_detail(ctx.db, rep)
    lines = [f"🧾 <b>{esc(m.display_name)} · {fdate(rep.report_date)}</b>"]
    if d["facility"]:
        lines.append(f"🏥 {esc(d['facility'])}")
    lines.append(_count_line(d["result_count"], d["out_of_range"]))
    res_by_id = {r.id: r for r in ctx.db.scalars(select(Result).options(selectinload(Result.test_definition))
                                                 .where(Result.report_id == rep.id))}
    for p in d["panels"]:
        if not p["results"]:
            continue
        lines += ["", f"<b>▪️ {esc(p['name'])}</b>"]
        for rr in p["results"]:
            r = res_by_id.get(rr["id"])
            if r is not None:
                lines.append(value_line(r))
    ids = _member_report_ids(ctx, m)
    i = ids.index(rep.id) if rep.id in ids else -1
    nav = []
    if i >= 0 and i + 1 < len(ids):
        nav.append(btn(t("◀️ Önceki"), f"r:{ids[i + 1]}"))
    if i > 0:
        nav.append(btn(t("Sonraki ▶️"), f"r:{ids[i - 1]}"))
    extra = [btn(t("📎 Orijinal PDF"), f"rp:{rep.id}")] if rep.pdf_path else []
    ctx.show("\n".join(lines), kb(nav, extra + [btn(t("📋 Raporlar"), f"l:{m.id}:0")], _back(m)))


def _report_pdf(ctx: Ctx, rep: Report) -> None:
    from .files import load_pdf
    if not rep.pdf_path:
        ctx.send(t("Bu raporun PDF'i yüklenmemiş."))
        return
    ctx.c.send_chat_action(ctx.chat_id, "upload_document")
    m = ctx.db.get(Member, rep.member_id)
    data = load_pdf(rep.pdf_path)
    audit(ctx.db, ctx.actor, "telegram.report_pdf", "report", rep.id, commit=True)
    ctx.c.send_document(ctx.chat_id, f"{fold(m.display_name)}-{rep.report_date.isoformat()}.pdf", data,
                        caption=f"🧾 {esc(m.display_name)} · {fdate(rep.report_date)}")


PAGE = 8


def _reports(ctx: Ctx, m: Member, page: int) -> None:
    ctx.remember(m)
    lst = queries.list_reports(ctx.db, m.id, limit=PAGE, offset=page * PAGE)
    if not lst["total"]:
        _no_reports(ctx, m)
        return
    buttons = []
    for r in lst["items"]:
        fac = (r["facility"] or "").split(" ")
        short = " ".join(fac[:2])[:22]
        label = f"{fdate(r['report_date'])} · {short}" + (f" ⚠️{r['out_of_range']}" if r["out_of_range"] else " ✅")
        buttons.append([btn(label, f"r:{r['id']}")])
    nav = []
    if page > 0:
        nav.append(btn(t("◀️ Yeni"), f"l:{m.id}:{page - 1}"))
    if (page + 1) * PAGE < lst["total"]:
        nav.append(btn(t("Eski ▶️"), f"l:{m.id}:{page + 1}"))
    title = t("📋 <b>{name} — raporlar</b> ({n})\nAçmak için birine dokunun.", name=esc(m.display_name), n=lst["total"])
    ctx.show(title, kb(*buttons, nav, _back(m)))


def _cats(ctx: Ctx, m: Member) -> tuple[list[str], dict[str, list[dict]]]:
    s = queries.member_summary(ctx.db, m.id)
    by: dict[str, list[dict]] = {}
    for i in s["items"]:
        by.setdefault(i["category"], []).append(i)
    return list(by.keys()), by


def _categories(ctx: Ctx, m: Member) -> None:
    ctx.remember(m)
    cats, by = _cats(ctx, m)
    if not cats:
        ctx.show(t("<b>{name}</b> için kayıtlı değer yok.", name=esc(m.display_name)), kb(_back(m)))
        return
    buttons = []
    for idx, cname in enumerate(cats):
        outc = sum(1 for i in by[cname] if i["latest"]["flag_computed"] in OUT)
        buttons.append(btn(f"{tcat(cname)} ({len(by[cname])})" + (f" ⚠️{outc}" if outc else ""), f"cc:{m.id}:{idx}"))
    ctx.show(t("📈 <b>{name} — tüm değerler</b>\nBir kategori seçin:", name=esc(m.display_name)),
             kb(*rows_of(buttons, 2), _back(m)))


def _category(ctx: Ctx, m: Member, idx: int) -> None:
    cats, by = _cats(ctx, m)
    if idx >= len(cats):
        _categories(ctx, m)
        return
    cname = cats[idx]
    lines = [f"📈 <b>{esc(m.display_name)} · {esc(tcat(cname))}</b>", t("<i>Son ölçülen değerler</i>"), ""]
    buttons = []
    for i in by[cname]:
        r = ctx.db.get(Result, i["latest"]["id"])
        line = value_line(r) + f" · <i>{fdate(i['latest']['sample_datetime'])}</i>"
        lines.append(line)
        buttons.append(btn(i["display_name"], f"t:{m.id}:{lt_td_id(ctx, i)}"))
    ctx.show("\n".join(lines), kb(*rows_of(buttons[:30], 3), [btn(t("🔙 Kategoriler"), f"c:{m.id}")] + _back(m)))


def _sparkline(vals: list[float]) -> str:
    if len(vals) < 2:
        return ""
    bars = "▁▂▃▄▅▆▇█"
    lo, hi = min(vals), max(vals)
    if hi == lo:
        return bars[3] * len(vals)
    return "".join(bars[int((v - lo) / (hi - lo) * (len(bars) - 1))] for v in vals)


def _test(ctx: Ctx, m: Member, td_id: str) -> None:
    from .telegram_chart import trend_png
    td = ctx.db.get(TestDefinition, td_id)
    if td is None:
        ctx.send(t("Test bulunamadı."))
        return
    ctx.remember(m)
    rows = list(ctx.db.execute(
        select(Result, Report).join(Report, Result.report_id == Report.id)
        .where(Result.member_id == m.id, Result.test_definition_id == td.id, Result.deleted_at.is_(None))
        .order_by(Result.sample_datetime.asc())).all())
    if not rows:
        ctx.show(t("<b>{name}</b> için <b>{test}</b> ölçümü yok.", name=esc(m.display_name), test=esc(tname(td))), kb(_back(m)))
        return
    last = rows[-1][0]
    nums = [(r.sample_datetime, r.value_numeric, r.flag_computed) for r, _ in rows if r.value_numeric is not None and r.sample_datetime]
    lines = [f"📈 <b>{esc(tname(td))}</b> — {esc(m.display_name)}"]
    lines.append(t("Son: {line} · {word}", line=value_line(last, td, with_name=False), word=flag_word(last.flag_computed)))
    if len(nums) >= 2 and last.value_numeric is not None:
        prev = nums[-2][1]
        if prev:
            lines.append(t("Önceki ölçüme göre: <b>{pct}</b>", pct=pct((last.value_numeric - prev) / abs(prev) * 100)))
    lines.append("")
    shown = rows[-10:]
    for r, rep in reversed(shown):
        lines.append(f"{fdate(r.sample_datetime or rep.report_date)}  {FLAG_ICON.get(r.flag_computed, '▫️')} {esc(_val(r))}")
    if len(rows) > len(shown):
        lines.append(t("<i>… toplam {n} ölçüm</i>", n=len(rows)))
    markup_rows = []
    if any(tinfo(td)):
        markup_rows.append([btn(t("ℹ️ Bu test ne anlatır?"), f"ti:{m.id}:{td.id}")])
    markup_rows.append(_back(m))
    markup = kb(*markup_rows)
    png = None
    if len(nums) >= 2:
        try:
            png = trend_png(tname(td), tunit(last.unit_canonical or last.unit_raw), nums, last.ref_low, last.ref_high)
        except Exception:  # noqa: BLE001
            log.exception("Grafik çizilemedi")
    text = "\n".join(lines)
    if png and len(text) <= 1000:
        ctx.c.send_chat_action(ctx.chat_id, "upload_photo")
        ctx.c.send_photo(ctx.chat_id, png, caption=text, reply_markup=markup)
    else:
        if png:
            ctx.c.send_photo(ctx.chat_id, png)
        ctx.send(text, markup)


def _test_info(ctx: Ctx, m: Member, td_id: str) -> None:
    td = ctx.db.get(TestDefinition, td_id)
    if td is None:
        return
    what, low, high = tinfo(td)
    parts = [f"ℹ️ <b>{esc(tname(td))}</b>", ""]
    if what:
        parts += [esc(what), ""]
    if low:
        parts += [t("🔻 <b>Düşükse:</b> {text}", text=esc(low)), ""]
    if high:
        parts += [t("🔺 <b>Yüksekse:</b> {text}", text=esc(high)), ""]
    parts.append(t("<i>Genel bilgidir, teşhis yerine geçmez. Sonuçlarınızı doktorunuzla değerlendirin.</i>"))
    ctx.send("\n".join(parts), kb([btn(t("📈 Geçmişe dön"), f"t:{m.id}:{td.id}")], _back(m)))


_REM_WORD = {"due": "zamanı geldi", "never": "hiç yapılmadı", "soon": "yaklaşıyor", "ok": "zamanı var"}


def _reminders(ctx: Ctx, m: Member) -> None:
    ctx.remember(m)
    rems = queries.reminders_status(ctx.db, m.id)
    if not rems:
        ctx.show(t("⏰ <b>{name}</b> için tanımlı kontrol hatırlatıcısı yok.\n"
                   "<i>Web arayüzünden (üye sayfası) eklenebilir.</i>", name=esc(m.display_name)), kb(_back(m)))
        return
    icon = {"due": "🔴", "never": "🔴", "soon": "🟡", "ok": "🟢"}
    lines = [t("⏰ <b>{name} — kontroller</b>", name=esc(m.display_name)), ""]
    for r in rems:
        last = t("son: {date}", date=fdate(r["last_done"])) if r["last_done"] else t("henüz ölçülmedi")
        lines.append(f"{icon[r['status']]} <b>{esc(r['display_name'])}</b> — {t(_REM_WORD[r['status']])}\n"
                     "      " + t("{last} · her {n} ayda bir · hedef {due}", last=last, n=r["interval_months"], due=fdate(r["due_date"])))
    ctx.show("\n".join(lines), kb(_back(m)))


def _doctor_pdf(ctx: Ctx, m: Member) -> None:
    from .export import member_pdf
    ctx.remember(m)
    ctx.c.send_chat_action(ctx.chat_id, "upload_document")
    data = member_pdf(ctx.db, m, [])
    audit(ctx.db, ctx.actor, "telegram.export_pdf", "member", m.id, commit=True)
    ctx.c.send_document(ctx.chat_id, f"rimetra-{fold(m.display_name)}.pdf", data,
                        caption=t("📄 {name} — tüm testlerin trend özeti (doktor için)", name=esc(m.display_name)))


def _settings(ctx: Ctx) -> None:
    from ..config import get_settings
    on = ctx.user.telegram_notify
    lines = [
        t("⚙️ <b>Ayarlar</b>"), "",
        t("Hesap: <b>@{user}</b> ({role})", user=esc(ctx.user.username), role=t("yönetici") if ctx.actor.is_master else t("üye")),
        t("Görebildiğiniz kişiler: {names}", names=", ".join(esc(m.display_name) for m in ctx.members)),
        t("Yeni tahlil bildirimi: <b>{state}</b>", state=t("açık") if on else t("kapalı")),
        t("Dil: <b>Türkçe</b>"),
    ]
    if not get_settings().telegram_notify:
        lines.append(t("<i>(Bildirimler sunucu ayarından genel olarak kapalı.)</i>"))
    ctx.show("\n".join(lines), kb(
        [btn(t("🔕 Bildirimleri kapat") if on else t("🔔 Bildirimleri aç"), "sn")],
        [btn("🇹🇷 Türkçe" if is_en() else "🇬🇧 English", "lg:tr" if is_en() else "lg:en")],
        [btn(t("🔌 Bu sohbetin bağlantısını kaldır"), "su")],
        [btn(t("🏠 Menü"), "home")],
    ))


# ---------------------------------------------------------------- serbest metin: kişi ve test arama

def _free_text(ctx: Ctx, text: str) -> None:
    q = fold(text)
    words = q.split()
    # baştaki kelime(ler) bir kişi adıysa o kişiye geç
    target = None
    for m in ctx.members:
        n = fold(m.display_name)
        if q == n or q.startswith(n + " "):
            if target is None or len(n) > len(fold(target.display_name)):
                target = m
    if target is not None:
        rest = q[len(fold(target.display_name)):].strip()
        if not rest:
            _member_card(ctx, target)
            return
        q, m = rest, target
    else:
        m = ctx.member()
        if len(words) == 1 and len(q) < 2:
            ctx.send(t("Biraz daha yazın (ör. <i>ferritin</i>)."), main_kb())
            return
    _search_tests(ctx, m, q)


def _search_tests(ctx: Ctx, m: Member, q: str) -> None:
    ctx.remember(m)
    have = {tid for (tid,) in ctx.db.execute(
        select(Result.test_definition_id).where(Result.member_id == m.id, Result.deleted_at.is_(None),
                                                Result.test_definition_id.is_not(None)).distinct())}
    if not have:
        ctx.send(t("<b>{name}</b> için henüz kayıtlı değer yok.", name=esc(m.display_name)), main_kb())
        return
    tds = list(ctx.db.scalars(select(TestDefinition).where(TestDefinition.id.in_(have))))
    aliases: dict[str, list[str]] = {}
    for tid, a in ctx.db.execute(select(TestAlias.test_definition_id, TestAlias.alias_normalized)
                                 .where(TestAlias.test_definition_id.in_(have))):
        aliases.setdefault(tid, []).append(a)

    from ..catalog_en import NAMES_EN
    qc = q.replace(" ", "")
    scored = []
    for td in tds:
        names = [fold(td.display_name), fold(td.key.replace("_", " "))] + aliases.get(td.id, [])
        if td.key in NAMES_EN:  # İngilizce adla da aranabilsin
            names.append(fold(NAMES_EN[td.key]))
        best = 0
        for n in names:
            nc = n.replace(" ", "").replace("-", "")
            if n == q or nc == qc:
                best = max(best, 100)
            elif n.startswith(q) or nc.startswith(qc):
                best = max(best, 80)
            elif q in n or qc in nc:
                best = max(best, 60)
            elif all(w in n for w in q.split()):
                best = max(best, 40)
        if best:
            scored.append((best, td))
    scored.sort(key=lambda x: (-x[0], x[1].sort_order, x[1].display_name))
    if not scored:
        ctx.send(t("🔎 <b>{name}</b> sonuçlarında “{q}” diye bir test bulamadım.\n"
                   "Farklı bir yazım deneyin ya da <b>📈 Tüm değerler</b>'e bakın.", name=esc(m.display_name), q=esc(q)),
                 kb([btn(t("📈 Tüm değerler"), f"c:{m.id}")]))
        return
    top = scored[0][0]
    best = [td for s, td in scored if s == top]
    if len(best) == 1 and (top >= 80 or len(scored) == 1):
        _test(ctx, m, best[0].id)
        return
    buttons = [btn(tname(td), f"t:{m.id}:{td.id}") for _, td in scored[:12]]
    ctx.send(t("🔎 <b>{name}</b> — “{q}” için hangisi?", name=esc(m.display_name), q=esc(q)), kb(*rows_of(buttons, 2)))


# ---------------------------------------------------------------- bildirim

def send_report_notification(c: telegram.TelegramClient, report_id: str, actor_user_id: str | None) -> int:
    with SessionLocal() as db:
        rep = db.scalar(select(Report).options(selectinload(Report.facility)).where(Report.id == report_id))
        if rep is None or rep.deleted_at is not None:
            return 0
        m = db.get(Member, rep.member_id)
        users = db.scalars(select(User).where(User.telegram_chat_id.is_not(None), User.is_active.is_(True),
                                              User.telegram_notify.is_(True)))
        targets = [u for u in users if u.id != actor_user_id and actor_for_user(u).can_access_member(rep.member_id)]
        if not targets:
            return 0
        n = 0
        for u in targets:
            with use_lang(user_lang(u)):  # her alıcıya kendi dilinde
                d = queries.report_detail(db, rep)
                outs = [r for p in d["panels"] for r in p["results"] if r["flag_computed"] in OUT]
                lines = [t("🆕 <b>{name}</b> için yeni tahlil eklendi", name=esc(m.display_name)),
                         f"🧾 {fdate(rep.report_date)}" + (f" · {esc(d['facility'])}" if d["facility"] else ""),
                         _count_line(d["result_count"], len(outs))]
                if outs:
                    lines.append("")
                    for rr in outs[:8]:
                        r = db.get(Result, rr["id"])
                        lines.append(value_line(r))
                    if len(outs) > 8:
                        lines.append(t("… ve {n} tane daha", n=len(outs) - 8))
                text = "\n".join(lines)
                markup = kb([btn(t("🧾 Raporu aç"), f"r:{rep.id}"), btn(f"👤 {m.display_name}", f"m:{m.id}")])
            try:
                c.send_message(u.telegram_chat_id, text, markup)
                n += 1
            except telegram.TelegramError as e:
                if e.code == 403:  # kullanıcı botu engellemiş
                    log.info("Telegram: %s botu engellemiş, bildirim atlandı.", u.username)
                else:
                    raise
        return n
