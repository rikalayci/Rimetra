"""e-Nabız ham metinlerinin ayrıştırılması ve işaretleme kuralları (RIMETRA.md §7–8).

Ajan ham metinleri olduğu gibi gönderir; karar her zaman buradaki kurallarındır.
"""
from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
#  Metin normalizasyonu
# --------------------------------------------------------------------------

_TR_LOWER = str.maketrans({"I": "ı", "İ": "i"})
_FOLD = str.maketrans({"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c", "â": "a", "î": "i", "û": "u"})


def tr_lower(s: str) -> str:
    return s.translate(_TR_LOWER).lower()


def tr_upper(s: str) -> str:
    return s.replace("i", "İ").replace("ı", "I").upper()


def clean_text(s: str | None) -> str:
    if s is None:
        return ""
    s = html.unescape(str(s))
    s = unicodedata.normalize("NFC", s)
    s = s.replace(" ", " ")
    return re.sub(r"\s+", " ", s).strip()


def fold(s: str) -> str:
    """Karşılaştırma için: Türkçe küçük harf + aksan katlama + boşluk sadeleştirme."""
    s = tr_lower(clean_text(s)).translate(_FOLD)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip()


def dedupe_repeated_name(name: str) -> str:
    """'Bakteri Bakteri' → 'Bakteri', '# Lenfosit # Lenfosit' → '# Lenfosit'."""
    n = clean_text(name)
    tokens = n.split(" ")
    if len(tokens) >= 2 and len(tokens) % 2 == 0:
        half = len(tokens) // 2
        if tokens[:half] == tokens[half:]:
            return " ".join(tokens[:half])
    # boşluksuz tam tekrar: "LDLLDL" gibi durumlar için (çok nadir)
    if len(n) >= 4 and len(n) % 2 == 0 and n[: len(n) // 2] == n[len(n) // 2 :] and " " not in n:
        return n[: len(n) // 2]
    return n


def normalize_alias(name: str) -> str:
    """Alias anahtarı: tekrarı at, katla, sondaki noktalamayı at."""
    n = fold(dedupe_repeated_name(name))
    n = n.rstrip(" .:;,")
    return n


def normalize_facility(name: str) -> str:
    return fold(name).upper()


# --------------------------------------------------------------------------
#  Değer ayrıştırma
# --------------------------------------------------------------------------

_NUM = r"[-+]?\d+(?:[.,]\d+)?"
_RE_NUMERIC = re.compile(rf"^(?P<q>[<>]=?|≤|≥)?\s*(?P<n>{_NUM})$")
_RE_TEXT_NUM = re.compile(rf"^(?P<t>.+?)\s+(?P<q>[<>]=?)?\s*(?P<n>{_NUM})$")
_RE_NUM_TEXT = re.compile(rf"^(?P<q>[<>]=?)?\s*(?P<n>{_NUM})\s+(?P<t>.+)$")
_QUAL_WORDS = ("negatif", "pozitif", "reaktif", "nonreaktif", "non-reaktif", "zayif pozitif", "eser")


def _is_qual_word(t: str) -> bool:
    f = fold(t)
    return any(f.startswith(w) for w in _QUAL_WORDS)


def to_float(s: str) -> float:
    return float(s.replace(",", ".").replace("+", ""))


@dataclass
class ParsedValue:
    skip: bool = False
    value_numeric: float | None = None
    value_text: str | None = None
    value_qualifier: str | None = None


def _norm_qualifier(q: str | None) -> str | None:
    if not q:
        return None
    return {"≤": "<", "≥": ">", "<=": "<", ">=": ">"}.get(q, q)


def parse_value(raw: str | None) -> ParsedValue:
    v = clean_text(raw)
    if v in ("", ".", "-", "..."):
        return ParsedValue(skip=True)
    m = _RE_NUMERIC.match(v)
    if m:
        return ParsedValue(value_numeric=to_float(m.group("n")), value_qualifier=_norm_qualifier(m.group("q")))
    m = _RE_TEXT_NUM.match(v)
    if m and _is_qual_word(m.group("t")):
        return ParsedValue(
            value_text=m.group("t").strip(),
            value_numeric=to_float(m.group("n")),
            value_qualifier=_norm_qualifier(m.group("q")),
        )
    m = _RE_NUM_TEXT.match(v)
    if m and _is_qual_word(m.group("t")):
        return ParsedValue(
            value_text=m.group("t").strip(),
            value_numeric=to_float(m.group("n")),
            value_qualifier=_norm_qualifier(m.group("q")),
        )
    return ParsedValue(value_text=v)


def positive_degree(text: str | None) -> int | None:
    """'Pozitif (++)' → 2. Pozitif değilse None."""
    if not text:
        return None
    f = fold(text)
    if not f.startswith("pozitif"):
        return None
    return text.count("+")


# --------------------------------------------------------------------------
#  Referans ayrıştırma
# --------------------------------------------------------------------------

_RE_RANGE = re.compile(rf"^\s*(?P<lo>{_NUM})\s*[-–—]\s*(?P<hi>{_NUM})\s*(?P<rest>.*)$")
_RE_UPPER = re.compile(rf"^\s*(?P<op><=?|≤)\s*(?P<n>{_NUM})\s*(?P<rest>.*)$")
_RE_LOWER = re.compile(rf"^\s*(?P<op>>=?|≥)\s*(?P<n>{_NUM})\s*(?P<rest>.*)$")
_RE_REF_DESC = re.compile(r"^-?\s*referans\s+a[cç][iı]klama\s*:\s*(?P<t>.+)$", re.IGNORECASE)


@dataclass
class ParsedReference:
    ref_low: float | None = None
    ref_high: float | None = None
    ref_low_exclusive: bool = False
    ref_high_exclusive: bool = False
    ref_text: str | None = None
    ref_note: str | None = None

    @property
    def has_numeric(self) -> bool:
        return self.ref_low is not None or self.ref_high is not None


def _clean_rest(rest: str) -> str | None:
    r = rest.strip()
    r = re.sub(r"^[-–—:\s]+", "", r).strip()
    return r or None


def parse_reference(raw: str | None) -> ParsedReference:
    r = clean_text(raw)
    if not r or r in ("-", "."):
        return ParsedReference()

    m = _RE_REF_DESC.match(r)
    if m:
        return ParsedReference(ref_text=tr_upper(m.group("t").strip(" -")))

    m = _RE_RANGE.match(r)
    if m:
        return ParsedReference(
            ref_low=to_float(m.group("lo")), ref_high=to_float(m.group("hi")), ref_note=_clean_rest(m.group("rest"))
        )
    m = _RE_UPPER.match(r)
    if m:
        return ParsedReference(
            ref_high=to_float(m.group("n")),
            ref_high_exclusive=m.group("op") == "<",
            ref_note=_clean_rest(m.group("rest")),
        )
    m = _RE_LOWER.match(r)
    if m:
        return ParsedReference(
            ref_low=to_float(m.group("n")),
            ref_low_exclusive=m.group("op") == ">",
            ref_note=_clean_rest(m.group("rest")),
        )

    # Metin referansı: "NEGATİF -", "Negatif", "Berrak"
    t = r.strip(" -–—")
    if t:
        return ParsedReference(ref_text=tr_upper(t))
    return ParsedReference()


# --------------------------------------------------------------------------
#  Ölçek kuralları
# --------------------------------------------------------------------------


def apply_unit_rules(value: float | None, rules: list | None) -> float | None:
    if value is None or not rules:
        return value
    for rule in rules:
        if "if_gt" in rule and value > rule["if_gt"]:
            return round(value * rule.get("factor", 1), 10)
        if "if_lt" in rule and value < rule["if_lt"]:
            return round(value * rule.get("factor", 1), 10)
    return value


# --------------------------------------------------------------------------
#  İşaretleme (flag_computed)
# --------------------------------------------------------------------------

NEG_WORDS = ("negatif", "nonreaktif", "non-reaktif", "non reaktif", "yok", "gorulmedi", "saptanmadi")


def _is_low(v: float, ref: ParsedReference) -> bool:
    if ref.ref_low is None:
        return False
    return v <= ref.ref_low if ref.ref_low_exclusive else v < ref.ref_low


def _is_high(v: float, ref: ParsedReference) -> bool:
    if ref.ref_high is None:
        return False
    return v >= ref.ref_high if ref.ref_high_exclusive else v > ref.ref_high


def compute_flag(val: ParsedValue, ref: ParsedReference) -> str:
    # 1) Sayısal değer + sayısal referans
    if val.value_numeric is not None and ref.has_numeric:
        v = val.value_numeric
        q = val.value_qualifier
        if q is None:
            if _is_low(v, ref):
                return "low"
            if _is_high(v, ref):
                return "high"
            return "normal"
        if q == "<":
            # gerçek değer < v  (alt sınır 0 ise pratikte alt sınır yoktur)
            low_bound = ref.ref_low if (ref.ref_low is not None and ref.ref_low > 0) else None
            if low_bound is not None and v <= low_bound:
                return "low"
            if low_bound is None and ref.ref_high is not None and v <= ref.ref_high:
                return "normal"
            return "unknown"
        if q == ">":
            # gerçek değer > v
            if ref.ref_high is not None and v >= ref.ref_high:
                return "high"
            if ref.ref_high is None and ref.ref_low is not None and v >= ref.ref_low:
                return "normal"
            return "unknown"
        return "unknown"

    # 2) Nitel referans
    if ref.ref_text:
        rt = fold(ref.ref_text)
        vt = fold(val.value_text or "")
        if not vt and val.value_numeric is None:
            return "unknown"
        if rt.startswith("negatif") or rt in ("nonreaktif", "non-reaktif"):
            if vt.startswith("pozitif") or vt.startswith("eser") or vt.startswith("reaktif") or vt.startswith("zayif pozitif"):
                return "abnormal"
            if any(vt.startswith(w) for w in NEG_WORDS):
                return "normal"
            return "unknown"
        if rt == "normal":
            return "normal" if vt == "normal" else ("abnormal" if vt else "unknown")
        if vt and vt == rt:
            return "normal"
        return "unknown"

    return "unknown"


def flags_mismatch(flag_computed: str, flag_source: str | None) -> bool:
    if flag_source not in ("ok", "alert"):
        return False
    if flag_computed == "unknown":
        return False
    computed_alert = flag_computed in ("low", "high", "abnormal")
    return computed_alert != (flag_source == "alert")


def normalize_source_flag(s: str | None) -> str | None:
    if s is None:
        return None
    f = fold(s)
    if f in ("ok", "normal", "green", "tick", "yesil"):
        return "ok"
    if f in ("alert", "warning", "red", "kirmizi", "unlem", "!"):
        return "alert"
    return None


# --------------------------------------------------------------------------
#  Toplu sonuç ayrıştırma
# --------------------------------------------------------------------------


@dataclass
class ParsedResult:
    raw_name: str
    name: str
    alias_key: str
    value: ParsedValue
    reference: ParsedReference
    unit_raw: str | None
    flag_source: str | None
    warnings: list[str] = field(default_factory=list)


def parse_result_row(raw_name: str, raw_value: str | None, raw_unit: str | None, raw_reference: str | None, source_flag: str | None) -> ParsedResult:
    name = dedupe_repeated_name(raw_name)
    unit = clean_text(raw_unit) or None
    return ParsedResult(
        raw_name=clean_text(raw_name),
        name=name,
        alias_key=normalize_alias(name),
        value=parse_value(raw_value),
        reference=parse_reference(raw_reference),
        unit_raw=unit,
        flag_source=normalize_source_flag(source_flag),
    )


def value_signature(v: ParsedValue) -> str:
    """Parmak izi için değerin kararlı gösterimi."""
    parts = []
    if v.value_qualifier:
        parts.append(v.value_qualifier)
    if v.value_numeric is not None:
        parts.append(repr(round(v.value_numeric, 6)))
    if v.value_text:
        parts.append(fold(v.value_text))
    return "~".join(parts)


def names_match(document_name: str, member_display: str, member_full: str | None) -> bool:
    d = fold(document_name)
    if not d:
        return True
    dtoks = set(d.split())
    if member_full:
        f = fold(member_full)
        if f == d or set(f.split()) <= dtoks:
            return True
    disp = fold(member_display)
    if not disp:
        return False
    return set(disp.split()) <= dtoks
