"""Doktora götürmek için dışa aktarım: CSV ve trend PDF'i (seçilen ya da tüm testler, çok sayfa)."""
from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..i18n import fdate, fdatetime, fnum, t, tcat, tname, tunit
from ..models import Facility, Member, Report, Result, TestDefinition
from .ingest import local_tz

_FONT = "Helvetica"
_FONT_BOLD = "Helvetica-Bold"


def _register_fonts() -> None:
    global _FONT, _FONT_BOLD
    if _FONT != "Helvetica":
        return
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for reg, bold in [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ]:
        if Path(reg).exists() and Path(bold).exists():
            pdfmetrics.registerFont(TTFont("DejaVu", reg))
            pdfmetrics.registerFont(TTFont("DejaVu-Bold", bold))
            _FONT, _FONT_BOLD = "DejaVu", "DejaVu-Bold"
            return


_FLAG_TR = {"normal": "Normal", "high": "Yüksek", "low": "Düşük", "abnormal": "Anormal"}


def flag_label(flag: str | None) -> str:
    if flag == "unknown":
        return "—"
    return t(_FLAG_TR[flag]) if flag in _FLAG_TR else ""


def _rows(db: Session, member: Member, keys: list[str]):
    q = (select(Result, TestDefinition, Report, Facility)
         .join(TestDefinition, Result.test_definition_id == TestDefinition.id)
         .join(Report, Result.report_id == Report.id)
         .outerjoin(Facility, Report.facility_id == Facility.id)
         .where(Result.member_id == member.id, Result.deleted_at.is_(None)))
    if keys:
        q = q.where(TestDefinition.key.in_(keys))
    return db.execute(q.order_by(TestDefinition.sort_order, Result.sample_datetime)).all()


def _val(r: Result) -> str:
    parts = []
    if r.value_text:
        parts.append(r.value_text)
    if r.value_numeric is not None:
        num = fnum(r.value_numeric)
        parts.append((r.value_qualifier or "") + num)
    return " ".join(parts) if parts else (r.raw_value or "")


def _ref(r: Result) -> str:
    f = fnum
    if r.ref_low is not None and r.ref_high is not None:
        return f"{f(r.ref_low)} – {f(r.ref_high)}"
    if r.ref_high is not None:
        return ("<" if r.ref_high_exclusive else "≤") + f(r.ref_high)
    if r.ref_low is not None:
        return (">" if r.ref_low_exclusive else "≥") + f(r.ref_low)
    return r.ref_text or ""


def member_csv(db: Session, member: Member, keys: list[str]) -> bytes:
    out = io.StringIO()
    out.write("﻿")  # Excel için BOM
    w = csv.writer(out, delimiter=";")
    w.writerow([t(h) for h in ("Kişi", "Kategori", "Test", "Test anahtarı", "Numune zamanı", "Değer", "Birim", "Referans",
                                "Durum", "Kurum", "Rapor tarihi")])
    for r, td, rep, fac in _rows(db, member, keys):
        w.writerow([member.display_name, tcat(td.category), tname(td), td.key,
                    fdatetime(r.sample_datetime.astimezone(local_tz())) if r.sample_datetime else "",
                    _val(r), tunit(r.unit_canonical or r.unit_raw) or "", _ref(r), flag_label(r.flag_computed),
                    fac.name_raw if fac else (t("Elle giriş") if rep.source == "manual" else ""),
                    fdate(rep.report_date)])
    return out.getvalue().encode("utf-8")


def member_pdf(db: Session, member: Member, keys: list[str]) -> bytes:
    """Seçilen (boşsa TÜM) testlerin trend grafikleri; ana sayfadaki sırayla, kategori başlıklarıyla,
    gerektiği kadar sayfa."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    from ..catalog_seed import CATEGORY_ORDER

    _register_fonts()
    rows = _rows(db, member, keys)
    by_test: dict[str, list] = {}
    tdefs: dict[str, TestDefinition] = {}
    for r, td, rep, fac in rows:
        by_test.setdefault(td.key, []).append(r)
        tdefs[td.key] = td
    if keys:
        order = [k for k in dict.fromkeys(keys) if k in by_test]
    else:
        cat_idx = {c: i for i, c in enumerate(CATEGORY_ORDER)}
        order = sorted(by_test, key=lambda k: (cat_idx.get(tdefs[k].category, 99), tdefs[k].category,
                                                tdefs[k].sort_order, tdefs[k].display_name))
    # kategoriye göre grupla (seçim sırası korunarak)
    groups: dict[str, list[str]] = {}
    for k in order:
        groups.setdefault(tdefs[k].category, []).append(k)

    buf = io.BytesIO()
    W, H = A4
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(t("Rimetra — {name}", name=member.display_name))
    green = colors.HexColor("#2F5D46")
    grey = colors.HexColor("#555555")
    MARGIN, GAP, BOX_H, HEAD_H, BOTTOM = 40, 20, 168, 26, 46
    box_w = (W - 2 * MARGIN - GAP) / 2
    page = [1]

    def footer():
        c.setFont(_FONT, 8)
        c.setFillColor(grey)
        c.drawString(MARGIN, 24, f"Rimetra · {member.display_name}")
        c.drawRightString(W - MARGIN, 24, t("Sayfa {n}", n=page[0]))

    def first_header() -> float:
        c.setFillColor(green)
        c.setFont(_FONT_BOLD, 18)
        c.drawString(MARGIN, H - 50, "Rimetra")
        c.setFillColor(colors.black)
        c.setFont(_FONT_BOLD, 13)
        title = member.display_name + (f"  ({member.birth_year})" if member.birth_year else "")
        c.drawString(MARGIN, H - 72, title)
        c.setFont(_FONT, 9)
        c.setFillColor(grey)
        c.drawString(MARGIN, H - 86, t("Hazırlanma: {when}  ·  {n} test  ·  Yalnızca değerler ve referans aralıkları; tıbbi yorum içermez.",
                                       when=fdatetime(datetime.now(local_tz())), n=len(order)))
        return H - 100

    def new_page() -> float:
        footer()
        c.showPage()
        page[0] += 1
        return H - 40

    y = first_header()
    if not order:
        c.setFont(_FONT, 11)
        c.setFillColor(colors.black)
        c.drawString(MARGIN, y - 20, t("Seçilen testler için kayıt bulunamadı."))
        footer()
        c.showPage()
        c.save()
        return buf.getvalue()

    for cat, ks in groups.items():
        # başlık + en az bir satır sığmıyorsa yeni sayfa
        if y - HEAD_H - BOX_H < BOTTOM:
            y = new_page()
        c.setFillColor(green)
        c.setFont(_FONT_BOLD, 12)
        c.drawString(MARGIN, y - 16, tcat(cat) or "")
        c.setStrokeColor(colors.HexColor("#DCEBDD"))
        c.setLineWidth(1)
        c.line(MARGIN, y - 21, W - MARGIN, y - 21)
        y -= HEAD_H
        for i in range(0, len(ks), 2):
            if y - max(_box_height(by_test[k], BOX_H) for k in ks[i:i + 2]) < BOTTOM:
                y = new_page()
                c.setFillColor(grey)
                c.setFont(_FONT, 9)
                c.drawString(MARGIN, y - 10, t("{cat} (devam)", cat=tcat(cat)))
                y -= 16
            pair = ks[i:i + 2]
            row_h = max(_box_height(by_test[k], BOX_H) for k in pair)
            for j, key in enumerate(pair):
                _draw_test_box(c, MARGIN + j * (box_w + GAP), y - row_h, box_w, row_h, tdefs[key], by_test[key])
            y -= row_h
    footer()
    c.showPage()
    c.save()
    return buf.getvalue()


def _box_height(res: list, full: float) -> float:
    """Sayısal test: grafik kutusu. Nitel test (Negatif/Pozitif…): yalnızca değer listesi kadar."""
    if any(r.value_numeric is not None and r.sample_datetime for r in res):
        return full
    return 64 + 12 * min(len(res), 6)


def _draw_test_box(c, x0: float, y0: float, box_w: float, box_h: float, td: TestDefinition, res: list) -> None:
    from reportlab.graphics import renderPDF
    from reportlab.graphics.charts.lineplots import LinePlot
    from reportlab.graphics.shapes import Circle, Drawing, Rect, String
    from reportlab.graphics.widgets.markers import makeMarker
    from reportlab.lib import colors

    green = colors.HexColor("#2F5D46")
    sage = colors.HexColor("#DCEBDD")
    red = colors.HexColor("#D9483B")
    d = Drawing(box_w, box_h - 8)
    d.add(Rect(0, 0, box_w, box_h - 8, strokeColor=colors.HexColor("#E5DED3"), fillColor=colors.HexColor("#FFFDF9"), rx=6, ry=6))
    last = res[-1]
    unit = tunit(last.unit_canonical or last.unit_raw) or ""
    d.add(String(10, box_h - 26, tname(td)[:60], fontName=_FONT_BOLD, fontSize=10))
    status = flag_label(last.flag_computed)
    d.add(String(10, box_h - 40, t("Son: {val} {unit}   Ref: {ref}   {status}", val=_val(last), unit=unit, ref=_ref(last), status=status)[:95], fontName=_FONT, fontSize=8,
                 fillColor=red if last.flag_computed in ("high", "low", "abnormal") else colors.HexColor("#444444")))
    pts = [(r.sample_datetime.timestamp(), r.value_numeric, r) for r in res if r.value_numeric is not None and r.sample_datetime]
    if len(pts) >= 1:
        lp = LinePlot()
        lp.x, lp.y = 32, 22
        lp.width, lp.height = box_w - 46, box_h - 78
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        lows = [r.ref_low for r in res if r.ref_low is not None]
        highs = [r.ref_high for r in res if r.ref_high is not None]
        ymin = min(ys + lows) if lows else min(ys)
        ymax = max(ys + highs) if highs else max(ys)
        pad = (ymax - ymin) * 0.15 or abs(ymax) * 0.2 or 1
        ymin, ymax = max(0, ymin - pad) if ymin >= 0 else ymin - pad, ymax + pad
        xmin, xmax = (min(xs), max(xs)) if len(xs) > 1 and max(xs) > min(xs) else (xs[0] - 86400 * 30, xs[0] + 86400 * 30)
        lp.xValueAxis.valueMin, lp.xValueAxis.valueMax = xmin, xmax
        lp.yValueAxis.valueMin, lp.yValueAxis.valueMax = ymin, ymax
        lp.xValueAxis.valueSteps = xs if len(xs) <= 6 else xs[:: max(1, len(xs) // 5)]
        lp.xValueAxis.labelTextFormat = lambda v: datetime.fromtimestamp(v, local_tz()).strftime("%m.%y")
        lp.xValueAxis.labels.fontName = _FONT
        lp.xValueAxis.labels.fontSize = 6
        lp.yValueAxis.labels.fontName = _FONT
        lp.yValueAxis.labels.fontSize = 6
        lp.yValueAxis.labelTextFormat = lambda v: f"{v:.3g}"
        lp.data = [[(p[0], p[1]) for p in pts]]
        lp.lines[0].strokeColor = green
        lp.lines[0].strokeWidth = 1.4
        lp.lines[0].symbol = makeMarker("FilledCircle", size=3.5, fillColor=green)
        # referans bandı (son ölçümün aralığı)
        if last.ref_low is not None or last.ref_high is not None:
            lo = last.ref_low if last.ref_low is not None else ymin
            hi = last.ref_high if last.ref_high is not None else ymax
            lo, hi = max(lo, ymin), min(hi, ymax)
            if hi > lo:
                sy = lp.height / (ymax - ymin)
                d.add(Rect(lp.x, lp.y + (lo - ymin) * sy, lp.width, (hi - lo) * sy, fillColor=sage, strokeColor=None))
        d.add(lp)
        # referans dışı noktalar kırmızı
        sx = lp.width / (xmax - xmin) if xmax > xmin else 0
        sy = lp.height / (ymax - ymin)
        for tx, v, r in pts:
            if r.flag_computed in ("high", "low", "abnormal"):
                d.add(Circle(lp.x + (tx - xmin) * sx, lp.y + (v - ymin) * sy, 2.6, fillColor=red, strokeColor=red))
    else:
        # nitel test: tarih + değer listesi
        y = box_h - 58
        for r in res[-6:]:
            when = fdate(r.sample_datetime.astimezone(local_tz())) if r.sample_datetime else ""
            col_ = red if r.flag_computed in ("abnormal", "high", "low") else colors.HexColor("#333333")
            d.add(String(12, y, f"{when}   {_val(r)}"[:80], fontName=_FONT, fontSize=8, fillColor=col_))
            y -= 12
    renderPDF.draw(d, c, x0, y0)
