"""Telegram için küçük trend grafiği (PNG). Pillow reportlab ile birlikte zaten kurulu gelir."""
from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from ..i18n import is_en, t

W, H = 1000, 560
PAD_L, PAD_R, PAD_T, PAD_B = 96, 40, 70, 78
BG = (251, 250, 246)
INK = (38, 50, 46)
MUTED = (128, 138, 133)
GRID = (228, 226, 219)
BAND = (221, 239, 230)
LINE = (47, 125, 98)
HIGH = (214, 92, 72)
LOW = (66, 120, 196)

_FONT_DIRS = ["/usr/share/fonts/truetype/dejavu"]


def _font(size: int, bold: bool = False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    for d in _FONT_DIRS:
        p = Path(d) / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    return ImageFont.load_default(size)


def _num(v: float) -> str:
    if abs(v) >= 100:
        s = f"{v:.0f}"
    elif abs(v) >= 10:
        s = f"{v:.1f}"
    else:
        s = f"{v:.2f}"
    s = s.rstrip("0").rstrip(".") if "." in s else s
    return s if is_en() else s.replace(".", ",")


def trend_png(title: str, unit: str | None, points: list[tuple[datetime, float, str]],
              ref_low: float | None, ref_high: float | None) -> bytes | None:
    """points: (zaman, değer, flag). En az 2 nokta gerekir."""
    if len(points) < 2:
        return None
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_title, f_axis, f_val = _font(30, True), _font(20), _font(20, True)

    head = title + (f"  ({unit})" if unit else "")
    while d.textlength(head, font=f_title) > W - 300 and len(head) > 10:
        head = head[:-2]
    if head != title + (f"  ({unit})" if unit else ""):
        head = head.rstrip() + "…"
    d.text((PAD_L - 60, 20), head, fill=INK, font=f_title)

    vals = [v for _, v, _ in points]
    lo, hi = min(vals), max(vals)
    for r in (ref_low, ref_high):
        if r is not None:
            lo, hi = min(lo, r), max(hi, r)
    span = hi - lo or abs(hi) or 1.0
    lo -= span * 0.12
    hi += span * 0.15
    if min(vals) >= 0 and lo < 0:
        lo = 0.0

    x0, x1, y0, y1 = PAD_L, W - PAD_R, PAD_T, H - PAD_B
    t0 = points[0][0].timestamp()
    t1 = points[-1][0].timestamp()
    tspan = (t1 - t0) or 1.0

    px0, px1 = x0 + 36, x1 - 36  # noktalar kenara yapışmasın

    def X(i: int, t: datetime) -> float:
        frac = (t.timestamp() - t0) / tspan if t1 > t0 else i / (len(points) - 1)
        return px0 + frac * (px1 - px0)

    def Y(v: float) -> float:
        return y1 - (v - lo) / (hi - lo) * (y1 - y0)

    # referans bandı
    if ref_low is not None or ref_high is not None:
        top = Y(ref_high) if ref_high is not None else y0
        bot = Y(ref_low) if ref_low is not None else y1
        d.rectangle([x0, max(y0, top), x1, min(y1, bot)], fill=BAND)

    # yatay ızgara
    for k in range(5):
        v = lo + (hi - lo) * k / 4
        yy = Y(v)
        d.line([x0, yy, x1, yy], fill=GRID, width=1)
        txt = _num(v)
        tw = d.textlength(txt, font=f_axis)
        d.text((x0 - 12 - tw, yy - 11), txt, fill=MUTED, font=f_axis)

    xy = [(X(i, t), Y(v)) for i, (t, v, _) in enumerate(points)]
    d.line(xy, fill=LINE, width=5, joint="curve")

    # x ekseni etiketleri (en fazla 6)
    n = len(points)
    step = max(1, (n + 5) // 6)
    idxs = sorted(set(list(range(0, n, step)) + [n - 1]))
    last_lbl_x = -1e9
    for i in idxs:
        x = xy[i][0]
        lbl = (points[i][0].strftime("%b %Y" if is_en() else "%m.%Y") if n > 6
               else points[i][0].strftime("%d %b" if is_en() else "%d.%m.%y"))
        tw = d.textlength(lbl, font=f_axis)
        lx = min(max(x - tw / 2, 4), W - tw - 6)
        if lx < last_lbl_x + 12:
            continue
        d.text((lx, y1 + 14), lbl, fill=MUTED, font=f_axis)
        last_lbl_x = lx + tw

    for i, ((x, y), (_, v, flag)) in enumerate(zip(xy, points)):
        col = HIGH if flag in ("high", "abnormal") else LOW if flag == "low" else LINE
        r = 11 if i == n - 1 else 9
        d.ellipse([x - r, y - r, x + r, y + r], fill=col, outline=BG, width=3)
        if n <= 8 or i == n - 1:  # değer etiketleri
            txt = _num(v)
            tw = d.textlength(txt, font=f_val)
            ty = y - 42 if y - 42 > y0 - 20 else y + 16
            d.text((min(max(x - tw / 2, x0), x1 - tw), ty), txt, fill=col if col != LINE else INK, font=f_val)

    if ref_low is not None or ref_high is not None:
        lbl = t("Referans aralığı")
        d.rectangle([x1 - 200, 28, x1 - 180, 44], fill=BAND)
        d.text((x1 - 172, 24), lbl, fill=MUTED, font=f_axis)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
