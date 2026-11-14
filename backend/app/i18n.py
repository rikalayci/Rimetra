"""Dil desteği (Türkçe varsayılan, İngilizce).

Kaynak metinler Türkçedir ve aynı zamanda çeviri anahtarıdır (gettext tarzı).
- t("Metin {x}", x=1): o anki dile göre çevirip biçimlendirir.
- translate("hazır metin"): önceden biçimlendirilmiş bir metni (ör. f-string ile üretilmiş hata
  mesajı) şablonlarla eşleştirerek çevirir; eşleşme yoksa olduğu gibi döner.
Dil, istek başına (ara katman) ya da Telegram'da kullanıcının tercihiyle belirlenir.
"""
from __future__ import annotations

import contextvars
import re
from contextlib import contextmanager
from typing import Any

from .locales.en import MESSAGES_EN

LANGS = ("tr", "en")
DEFAULT_LANG = "tr"
_lang: contextvars.ContextVar[str] = contextvars.ContextVar("rimetra_lang", default=DEFAULT_LANG)


def normalize_lang(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip().lower()[:2]
    return v if v in LANGS else None


def lang_from_accept(header: str | None) -> str | None:
    """Accept-Language başlığından desteklenen ilk dili seçer (ör. "en-US,en;q=0.9,tr;q=0.8")."""
    if not header:
        return None
    best: list[tuple[float, str]] = []
    for part in header.split(","):
        bits = part.strip().split(";")
        code = normalize_lang(bits[0])
        if not code:
            continue
        q = 1.0
        for b in bits[1:]:
            b = b.strip()
            if b.startswith("q="):
                try:
                    q = float(b[2:])
                except ValueError:
                    q = 0.0
        best.append((q, code))
    if not best:
        return None
    best.sort(key=lambda x: -x[0])
    return best[0][1]


def get_lang() -> str:
    return _lang.get()


def set_lang(lang: str | None) -> contextvars.Token:
    return _lang.set(normalize_lang(lang) or DEFAULT_LANG)


@contextmanager
def use_lang(lang: str | None):
    tok = set_lang(lang)
    try:
        yield
    finally:
        _lang.reset(tok)


def is_en() -> bool:
    return get_lang() == "en"


def _fmt(s: str, kw: dict[str, Any]) -> str:
    if not kw:
        return s
    try:
        return s.format(**kw)
    except (KeyError, IndexError, ValueError):
        return s


def t(msg: str, **kw: Any) -> str:
    """Türkçe kaynak metni o anki dile çevirip biçimlendirir."""
    if is_en():
        return _fmt(MESSAGES_EN.get(msg, msg), kw)
    return _fmt(msg, kw)


# ---------------------------------------------------------------- hazır metinleri çevirme

_PLACEHOLDER = re.compile(r"\{(\w+)\}")
_TEMPLATES: list[tuple[re.Pattern, str]] | None = None


def _templates() -> list[tuple[re.Pattern, str]]:
    global _TEMPLATES
    if _TEMPLATES is None:
        out = []
        for tr, en in MESSAGES_EN.items():
            if "{" not in tr:
                continue
            pos = 0
            pat = ""
            for m in _PLACEHOLDER.finditer(tr):
                pat += re.escape(tr[pos:m.start()]) + f"(?P<{m.group(1)}>.+?)"
                pos = m.end()
            pat += re.escape(tr[pos:])
            out.append((re.compile("^" + pat + "$", re.DOTALL), en))
        # daha uzun (daha özgül) şablonlar önce denensin
        out.sort(key=lambda x: -len(x[0].pattern))
        _TEMPLATES = out
    return _TEMPLATES


def translate(text: str | None) -> str | None:
    """Önceden üretilmiş Türkçe bir metni İngilizceye çevirir (dil en ise)."""
    if not text or not is_en():
        return text
    exact = MESSAGES_EN.get(text)
    if exact is not None:
        return exact
    for pat, en in _templates():
        m = pat.match(text)
        if m:
            vals = {k: MESSAGES_EN.get(v, v) for k, v in m.groupdict().items()}
            return _fmt(en, vals)
    return text


def translate_payload(obj: Any) -> Any:
    """Hata gövdelerindeki iç içe "message" alanlarını çevirir."""
    if not is_en():
        return obj
    if isinstance(obj, dict):
        return {k: (translate(v) if k == "message" and isinstance(v, str) else translate_payload(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [translate_payload(x) for x in obj]
    return obj


# ---------------------------------------------------------------- katalog

def tname(td) -> str:
    """Test adı: yerleşik ve düzenlenmemişse İngilizcesi, değilse kayıtlı ad."""
    if td is None:
        return ""
    if is_en() and td.key:
        from .catalog_en import NAMES_EN
        from .catalog_seed import BUILTIN_NAMES
        en = NAMES_EN.get(td.key)
        if en and td.display_name == BUILTIN_NAMES.get(td.key):
            return en
    return td.display_name


def tcat(category: str | None) -> str | None:
    if category and is_en():
        from .catalog_en import CATEGORY_EN
        return CATEGORY_EN.get(category, category)
    return category


def tunit(unit: str | None) -> str | None:
    if unit and is_en():
        from .catalog_en import UNIT_EN
        return UNIT_EN.get(unit, unit)
    return unit


def tinfo(td) -> tuple[str | None, str | None, str | None]:
    """Açıklamalar: düzenlenmemiş yerleşik metinler İngilizceye çevrilir."""
    vals = (td.info_what, td.info_low, td.info_high)
    if not is_en() or not td.key:
        return vals
    from .catalog_en import INFO_EN
    from .catalog_info import CATALOG_INFO
    en, tr = INFO_EN.get(td.key), CATALOG_INFO.get(td.key)
    if not en or not tr:
        return vals
    return tuple(e if (v is not None and v == o) else v for v, e, o in zip(vals, en, tr))  # type: ignore[return-value]


# ---------------------------------------------------------------- sayı / tarih biçimi

_MONTHS_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def fnum(x: float | None) -> str:
    """Kısa sayı: Türkçede ondalık virgül, İngilizcede nokta."""
    if x is None:
        return ""
    s = f"{x:g}"
    return s if is_en() else s.replace(".", ",")


def fdate(d) -> str:
    """Tarih: 12.03.2025 (tr) / 12 Mar 2025 (en)."""
    if d is None:
        return ""
    if is_en():
        return f"{d.day} {_MONTHS_EN[d.month - 1]} {d.year}"
    return d.strftime("%d.%m.%Y")


def fdatetime(dt) -> str:
    if dt is None:
        return ""
    return f"{fdate(dt)} {dt.strftime('%H:%M')}"
