"""Okuma tarafı: özet, geçmiş, rapor detayı, aile paneli, karşılaştırma, eşleşmemiş testler."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..catalog_seed import CATEGORY_ORDER
from ..i18n import t, tinfo, tname, translate, tunit
from ..models import Facility, Member, Note, Panel, Reminder, Report, Result, TestDefinition, User
from ..parsing import flags_mismatch, positive_degree
from .ingest import local_tz

OUT = ("low", "high", "abnormal")


def iso(dt) -> str | None:
    return dt.isoformat() if dt else None


def member_public(m: Member, user: User | None = None) -> dict:
    return {
        "id": m.id,
        "display_name": m.display_name,
        "full_name": m.full_name,
        "sex": m.sex,
        "birth_year": m.birth_year,
        "avatar_color": m.avatar_color,
        "has_avatar": bool(m.avatar_path),
        "avatar_version": m.avatar_path.rsplit("/", 1)[-1].split(".")[0] if m.avatar_path else None,
        "sort_order": m.sort_order,
        "has_login": bool(user or m.user),
        "created_at": iso(m.created_at),
    }


def result_public(r: Result, td: TestDefinition | None = None) -> dict:
    td = td or r.test_definition
    return {
        "id": r.id,
        "report_id": r.report_id,
        "panel_id": r.panel_id,
        "raw_name": r.raw_name,
        "test_key": td.key if td else None,
        "display_name": tname(td) if td else r.raw_name,
        "category": td.category if td else None,
        "specimen": r.specimen or (td.specimen if td else None),
        "value_numeric": r.value_numeric,
        "value_text": r.value_text,
        "value_qualifier": r.value_qualifier,
        "positive_degree": positive_degree(r.value_text),
        "raw_value": r.raw_value,
        "unit": tunit(r.unit_canonical or r.unit_raw),
        "ref_low": r.ref_low,
        "ref_high": r.ref_high,
        "ref_low_exclusive": r.ref_low_exclusive,
        "ref_high_exclusive": r.ref_high_exclusive,
        "ref_text": r.ref_text,
        "ref_note": r.ref_note,
        "flag_computed": r.flag_computed,
        "flag_source": r.flag_source,
        "flag_mismatch": flags_mismatch(r.flag_computed, r.flag_source),
        "sample_datetime": iso(r.sample_datetime),
    }


def report_header(rep: Report, counts: dict | None = None) -> dict:
    counts = counts or {}
    return {
        "id": rep.id,
        "member_id": rep.member_id,
        "report_date": rep.report_date.isoformat(),
        "facility": rep.facility.name_raw if rep.facility else None,
        "source": rep.source,
        "has_pdf": bool(rep.pdf_path),
        "created_at": iso(rep.created_at),
        "deleted_at": iso(rep.deleted_at),
        "panel_count": counts.get("panels", 0),
        "result_count": counts.get("results", 0),
        "out_of_range": counts.get("out", 0),
        "panel_names": counts.get("panel_names", []),
    }


def _shown_with_report():
    """Raporla birlikte gösterilen sonuçlar: aktif olanlar ya da raporla aynı anda silinenler.
    "Sonuç değil" diye gizlenen satırlar hariç."""
    return or_(Result.deleted_at.is_(None), Result.deleted_at == Report.deleted_at)


def _report_counts(db: Session, report_ids: list[str]) -> dict[str, dict]:
    if not report_ids:
        return {}
    out: dict[str, dict] = defaultdict(lambda: {"panels": 0, "results": 0, "out": 0, "panel_names": []})
    for rid, cnt, outc in db.execute(
        select(Result.report_id, func.count(Result.id),
               func.count(Result.id).filter(Result.flag_computed.in_(OUT)))
        .join(Report, Report.id == Result.report_id)
        .where(Result.report_id.in_(report_ids), _shown_with_report())
        .group_by(Result.report_id)
    ):
        out[rid]["results"] = cnt
        out[rid]["out"] = outc
    for rid, name in db.execute(select(Panel.report_id, Panel.name).where(Panel.report_id.in_(report_ids)).order_by(Panel.position)):
        out[rid]["panels"] += 1
        out[rid]["panel_names"].append(translate(name) if name else t("Adsız panel"))
    return out


def list_reports(db: Session, member_id: str, limit: int = 50, offset: int = 0, include_deleted: bool = False) -> dict:
    q = select(Report).options(selectinload(Report.facility)).where(Report.member_id == member_id)
    if not include_deleted:
        q = q.where(Report.deleted_at.is_(None))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    reps = list(db.scalars(q.order_by(Report.report_date.desc(), Report.created_at.desc()).limit(limit).offset(offset)))
    counts = _report_counts(db, [r.id for r in reps])
    return {"items": [report_header(r, counts.get(r.id)) for r in reps], "total": total, "limit": limit, "offset": offset}


def report_detail(db: Session, rep: Report) -> dict:
    counts = _report_counts(db, [rep.id]).get(rep.id)
    panels = db.scalars(
        select(Panel).where(Panel.report_id == rep.id).order_by(Panel.position)
        .options(selectinload(Panel.results).selectinload(Result.test_definition))
    )
    return {
        **report_header(rep, counts),
        "panels": [
            {
                "id": p.id,
                "name": translate(p.name) if p.name else t("Adsız panel"),
                "name_raw": p.name,
                "specimen": p.specimen,
                "sample_datetime": iso(p.sample_datetime),
                "results": [result_public(r) for r in p.results
                            if r.deleted_at is None or r.deleted_at == rep.deleted_at],
            }
            for p in panels
        ],
    }


def _member_results(db: Session, member_id: str, since: datetime | None = None):
    q = (select(Result, TestDefinition)
         .join(TestDefinition, Result.test_definition_id == TestDefinition.id)
         .where(Result.member_id == member_id, Result.deleted_at.is_(None)))
    if since:
        q = q.where(Result.sample_datetime >= since)
    return db.execute(q.order_by(Result.sample_datetime.asc(), Result.position.asc())).all()


def _pct_change(prev: float | None, cur: float | None) -> float | None:
    if prev is None or cur is None or prev == 0:
        return None
    return round((cur - prev) / abs(prev) * 100, 1)


def member_summary(db: Session, member_id: str, since: datetime | None = None) -> dict:
    rows = _member_results(db, member_id, since)
    by_test: dict[str, list[tuple[Result, TestDefinition]]] = defaultdict(list)
    for r, td in rows:
        by_test[td.id].append((r, td))
    items = []
    for tid, lst in by_test.items():
        td = lst[-1][1]
        last = lst[-1][0]
        numeric = [(r.sample_datetime, r.value_numeric) for r, _ in lst if r.value_numeric is not None]
        prev_num = numeric[-2][1] if len(numeric) >= 2 and last.value_numeric is not None else None
        consecutive_out = len(lst) >= 2 and lst[-1][0].flag_computed in OUT and lst[-2][0].flag_computed in OUT
        items.append({
            "test_key": td.key,
            "display_name": tname(td),
            "category": td.category,
            "specimen": td.specimen,
            "value_type": td.value_type,
            "sort_order": td.sort_order,
            "latest": result_public(last, td),
            "previous_value": prev_num,
            "change_pct": _pct_change(prev_num, last.value_numeric),
            "sparkline": [{"t": iso(t), "v": v} for t, v in numeric[-12:]],
            "count": len(lst),
            "consecutive_out": consecutive_out,
        })
    cat_idx = {c: i for i, c in enumerate(CATEGORY_ORDER)}
    items.sort(key=lambda x: (cat_idx.get(x["category"], 99), x["category"], x["sort_order"], x["display_name"]))
    last_report = db.scalar(select(func.max(Report.report_date)).where(Report.member_id == member_id, Report.deleted_at.is_(None)))
    return {
        "member_id": member_id,
        "last_report_date": last_report.isoformat() if last_report else None,
        "total_tests": len(items),
        "out_of_range": sum(1 for i in items if i["latest"]["flag_computed"] in OUT),
        "report_count": db.scalar(select(func.count(Report.id)).where(Report.member_id == member_id, Report.deleted_at.is_(None))),
        "unmapped_count": db.scalar(select(func.count(Result.id)).where(
            Result.member_id == member_id, Result.test_definition_id.is_(None), Result.deleted_at.is_(None))),
        "items": items,
    }


def test_history(db: Session, member_id: str, td: TestDefinition) -> dict:
    rows = db.execute(
        select(Result, Report, Facility)
        .join(Report, Result.report_id == Report.id)
        .outerjoin(Facility, Report.facility_id == Facility.id)
        .where(Result.member_id == member_id, Result.test_definition_id == td.id, Result.deleted_at.is_(None))
        .order_by(Result.sample_datetime.asc())
    ).all()
    notes = db.scalars(select(Note).where(Note.member_id == member_id).order_by(Note.date)).all()
    measurements = []
    for r, rep, fac in rows:
        d = result_public(r, td)
        d["report_date"] = rep.report_date.isoformat()
        d["facility"] = fac.name_raw if fac else None
        d["source"] = rep.source
        measurements.append(d)
    return {
        "test": test_def_public(td, with_info=True),
        "member_id": member_id,
        "measurements": measurements,
        "notes": [note_public(n) for n in notes if n.test_definition_id in (None, td.id)],
    }


def test_def_public(td: TestDefinition, with_aliases: bool = False, with_info: bool = False) -> dict:
    d = {
        "id": td.id,
        "key": td.key,
        "display_name": tname(td),
        "display_name_raw": td.display_name,
        "specimen": td.specimen,
        "category": td.category,
        "canonical_unit": td.canonical_unit,
        "unit_label": tunit(td.canonical_unit),
        "value_type": td.value_type,
        "unit_rules": td.unit_rules,
        "is_builtin": td.is_builtin,
    }
    if with_aliases:
        d["aliases"] = sorted({a.alias_normalized for a in td.aliases})
    if with_info:
        d["info_what"], d["info_low"], d["info_high"] = tinfo(td)
        # Düzenleme formu için kayıtlı (çevrilmemiş) metinler
        d["info_what_raw"], d["info_low_raw"], d["info_high_raw"] = td.info_what, td.info_low, td.info_high
    return d


def note_public(n: Note, td: TestDefinition | None = None) -> dict:
    return {
        "id": n.id,
        "member_id": n.member_id,
        "date": n.date.isoformat(),
        "text": n.text,
        "test_definition_id": n.test_definition_id,
        "created_at": iso(n.created_at),
    }


def family_dashboard(db: Session, members: list[Member]) -> list[dict]:
    out = []
    for m in members:
        reps = list(db.scalars(
            select(Report).options(selectinload(Report.facility))
            .where(Report.member_id == m.id, Report.deleted_at.is_(None))
            .order_by(Report.report_date.desc(), Report.created_at.desc()).limit(3)
        ))
        counts = _report_counts(db, [r.id for r in reps])
        last_out = counts.get(reps[0].id, {}).get("out", 0) if reps else 0
        due = reminders_status(db, m.id)
        out.append({
            **member_public(m),
            "last_report_date": reps[0].report_date.isoformat() if reps else None,
            "last_report_out_of_range": last_out,
            "recent_reports": [report_header(r, counts.get(r.id)) for r in reps],
            "reminders_due": sum(1 for d in due if d["status"] in ("due", "never")),
        })
    return out


def compare_reports(db: Session, a: Report, b: Report) -> dict:
    """İki raporu test bazında yan yana koyar. a: eski, b: yeni (tarihe göre sıralanır)."""
    if (a.report_date, a.created_at) > (b.report_date, b.created_at):
        a, b = b, a

    def rows(rep: Report):
        res = db.scalars(select(Result).options(selectinload(Result.test_definition))
                         .where(Result.report_id == rep.id).order_by(Result.position))
        out = {}
        for r in res:
            k = r.test_definition.key if r.test_definition else f"raw:{r.specimen}:{r.raw_name}"
            out.setdefault(k, r)
        return out

    ra, rb = rows(a), rows(b)
    keys = list(dict.fromkeys([*ra.keys(), *rb.keys()]))
    cat_idx = {c: i for i, c in enumerate(CATEGORY_ORDER)}

    def sort_key(k):
        r = rb.get(k) or ra.get(k)
        td = r.test_definition
        return (cat_idx.get(td.category, 98) if td else 99, td.sort_order if td else 0, r.raw_name)

    lines = []
    for k in sorted(keys, key=sort_key):
        x, y = ra.get(k), rb.get(k)
        r = y or x
        td = r.test_definition
        diff = None
        diff_pct = None
        if x is not None and y is not None and x.value_numeric is not None and y.value_numeric is not None:
            diff = round(y.value_numeric - x.value_numeric, 4)
            diff_pct = _pct_change(x.value_numeric, y.value_numeric)
        lines.append({
            "key": k,
            "test_key": td.key if td else None,
            "display_name": tname(td) if td else r.raw_name,
            "category": td.category if td else "Eşleşmemiş",
            "a": result_public(x) if x else None,
            "b": result_public(y) if y else None,
            "diff": diff,
            "diff_pct": diff_pct,
        })
    return {"a": report_header(a, _report_counts(db, [a.id]).get(a.id)),
            "b": report_header(b, _report_counts(db, [b.id]).get(b.id)), "lines": lines}


def unmapped_groups(db: Session, member_ids: list[str] | None = None) -> list[dict]:
    q = (select(Result.raw_name, Result.specimen, func.count(Result.id), func.max(Result.sample_datetime),
                func.array_agg(func.distinct(Result.member_id)), func.max(Result.raw_value), func.max(Result.unit_raw),
                func.array_agg(Result.id))
         .where(Result.test_definition_id.is_(None), Result.deleted_at.is_(None))
         .group_by(Result.raw_name, Result.specimen).order_by(func.count(Result.id).desc()))
    if member_ids is not None:
        q = q.where(Result.member_id.in_(member_ids))
    return [
        {"raw_name": n, "specimen": s, "count": c, "last_seen": iso(t), "member_ids": list(mids or []),
         "example_value": v, "example_unit": u, "result_ids": list(ids or [])}
        for n, s, c, t, mids, v, u, ids in db.execute(q)
    ]


def reminders_status(db: Session, member_id: str) -> list[dict]:
    rems = db.scalars(select(Reminder).where(Reminder.member_id == member_id, Reminder.active.is_(True))).all()
    out = []
    today = datetime.now(local_tz()).date()
    for rem in rems:
        td = db.get(TestDefinition, rem.test_definition_id)
        last = db.scalar(select(func.max(Result.sample_datetime)).where(
            Result.member_id == member_id, Result.test_definition_id == rem.test_definition_id, Result.deleted_at.is_(None)))
        if last is None:
            status, due = "never", today
        else:
            ld = last.astimezone(local_tz()).date()
            due = _add_months(ld, rem.interval_months)
            status = "due" if due <= today else ("soon" if due <= today + timedelta(days=30) else "ok")
        out.append({
            "id": rem.id, "member_id": member_id, "test_key": td.key if td else None,
            "display_name": tname(td) if td else "?", "interval_months": rem.interval_months,
            "note": rem.note, "last_done": iso(last.astimezone(local_tz()).date()) if last else None,
            "due_date": due.isoformat(), "status": status,
        })
    out.sort(key=lambda x: x["due_date"])
    return out


def _add_months(d: date, months: int) -> date:
    y, m = divmod(d.month - 1 + months, 12)
    year, month = d.year + y, m + 1
    for day in (d.day, 28):
        try:
            return date(year, month, min(day, 31))
        except ValueError:
            continue
    return date(year, month, 28)
