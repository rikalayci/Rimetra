"""Web arayüzünün kullandığı uç noktalar — /api/app (oturum çerezi ile)."""
from __future__ import annotations

import calendar as cal
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import Response
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from ..catalog_seed import CATEGORY_ORDER
from ..config import get_settings
from ..db import get_db
from ..deps import Actor, actor_for_user, client_ip, get_user, get_user_actor, require_master
from ..errors import ApiError, not_found
from ..models import (
    ApiKey, AuditLog, Facility, Member, Note, Reminder, Report, Result, TestAlias, TestDefinition, User, UserSession, utcnow,
)
from ..parsing import fold, normalize_alias
from ..schemas import (
    AliasIn, ApiKeyIn, ManualEntryIn, MemberIn, MemberPatch, NoteIn, PanelIn, ReminderIn, ReportIn, ResultIn,
    DismissIn, RestoreResultsIn, ResultMappingsIn, TestDefIn, UserIn, UserPatch,
)
from ..security import SCOPES, forget_api_key_cache, generate_api_key, hash_password
from ..i18n import t
from ..services import backup, export, ingest, ops, queries
from ..services.audit import audit
from ..services.files import delete_file, image_ext, load_avatar, load_pdf, store_avatar
from ..services.mutations import delete_member_completely, link_alias, restore_report
from .auth import user_public

router = APIRouter(prefix="/api/app", tags=["Web arayüzü"])


# ------------------------------------------------------------------ yardımcılar

def _member(db: Session, actor: Actor, member_id: str) -> Member:
    return ops.get_member(db, actor, member_id)


def _test(db: Session, key: str) -> TestDefinition:
    td = db.scalar(select(TestDefinition).where(TestDefinition.key == key))
    if td is None:
        raise not_found("Test")
    return td


# ------------------------------------------------------------------ genel

@router.get("/meta")
def meta(actor: Actor = Depends(get_user_actor)):
    s = get_settings()
    return {
        "categories": CATEGORY_ORDER,
        "scopes": SCOPES,
        "public_base_url": s.public_base_url.rstrip("/"),
        "report_restore_days": s.report_restore_days,
        "backup_enabled": s.backup_enabled,
        "version": "1.3.0",
    }


@router.get("/agent/skill")
def agent_skill(download: bool = False, actor: Actor = Depends(get_user_actor)):
    from ..agent_skill import read_skill
    text = read_skill()
    if text is None:
        raise not_found("Skill dosyası")
    headers = {"Content-Disposition": 'attachment; filename="SKILL.md"'} if download else {}
    return Response(text, media_type="text/markdown; charset=utf-8", headers=headers)


@router.get("/dashboard")
def dashboard(actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    members = ops.visible_members(db, actor)
    return {"members": queries.family_dashboard(db, members)}


# ------------------------------------------------------------------ üyeler

@router.get("/members")
def members(actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    return {"items": [queries.member_public(m) for m in ops.visible_members(db, actor)]}


@router.post("/members", status_code=201)
def create_member(body: MemberIn, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    return ops.create_member(db, actor, body)


@router.get("/members/{member_id}")
def get_member(member_id: str, actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    m = _member(db, actor, member_id)
    d = queries.member_public(m)
    if actor.is_master and m.user:
        d["user"] = {"id": m.user.id, "username": m.user.username, "read_only": m.user.read_only, "is_active": m.user.is_active}
    return d


@router.patch("/members/{member_id}")
def patch_member(member_id: str, body: MemberPatch, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    m = _member(db, actor, member_id)
    changes = body.model_dump(exclude_unset=True)
    before = {k: getattr(m, k) for k in changes}
    for k, v in changes.items():
        setattr(m, k, v)
    audit(db, actor, "member.update", "member", m.id, {"before": before, "after": changes})
    db.commit()
    return queries.member_public(m)


@router.delete("/members/{member_id}")
def delete_member(member_id: str, confirm: str = Query(...), actor: Actor = Depends(require_master),
                  db: Session = Depends(get_db)):
    m = _member(db, actor, member_id)
    if fold(confirm) != fold(m.display_name):
        raise ApiError(400, "CONFIRM_MISMATCH", "Onay için üyenin adını aynen yazın.")
    if m.user and m.user.role == "master":
        raise ApiError(400, "FORBIDDEN", "Master kullanıcının profili silinemez.")
    delete_member_completely(db, actor, m)
    return {"deleted": True}


@router.post("/members/{member_id}/avatar")
async def upload_avatar(member_id: str, file: UploadFile = File(...), actor: Actor = Depends(require_master),
                        db: Session = Depends(get_db)):
    m = _member(db, actor, member_id)
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise ApiError(400, "VALIDATION_ERROR", "Görsel en fazla 5 MB olabilir.")
    ext = image_ext(data)
    if not ext:
        raise ApiError(400, "VALIDATION_ERROR", "PNG, JPG veya WEBP yükleyin.")
    old = m.avatar_path
    m.avatar_path = store_avatar(m.id, data, ext)
    audit(db, actor, "member.avatar", "member", m.id)
    db.commit()
    delete_file(old)
    return queries.member_public(m)


@router.delete("/members/{member_id}/avatar")
def delete_avatar(member_id: str, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    m = _member(db, actor, member_id)
    delete_file(m.avatar_path)
    m.avatar_path = None
    db.commit()
    return queries.member_public(m)


@router.get("/members/{member_id}/avatar")
def get_avatar(member_id: str, actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    m = db.get(Member, member_id)
    if m is None or not m.avatar_path:
        raise not_found("Avatar")
    ext = m.avatar_path.split(".")[-2]
    mime = {"png": "image/png", "jpg": "image/jpeg", "webp": "image/webp"}.get(ext, "application/octet-stream")
    return Response(load_avatar(m.avatar_path), media_type=mime, headers={"Cache-Control": "private, max-age=86400"})


@router.get("/members/{member_id}/summary")
def member_summary(member_id: str, since_days: int | None = None, actor: Actor = Depends(get_user_actor),
                   db: Session = Depends(get_db)):
    since = utcnow() - timedelta(days=since_days) if since_days else None
    return ops.member_summary(db, actor, member_id, since)


@router.get("/members/{member_id}/reports")
def member_reports(member_id: str, include_deleted: bool = False, limit: int = 100, offset: int = 0,
                   actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    _member(db, actor, member_id)
    return queries.list_reports(db, member_id, min(limit, 500), offset, include_deleted and actor.is_master)


@router.get("/members/{member_id}/tests/{test_key}/history")
def test_history(member_id: str, test_key: str, actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    return ops.test_history(db, actor, member_id, test_key)


# ------------------------------------------------------------------ raporlar

@router.get("/reports/{report_id}")
def get_report(report_id: str, actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    rep = ops.get_report_obj(db, actor, report_id, allow_deleted=actor.is_master)
    return queries.report_detail(db, rep)


@router.delete("/reports/{report_id}")
def delete_report(report_id: str, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    return ops.delete_report(db, actor, report_id)


@router.post("/reports/{report_id}/result-mappings")
def remap_result_mappings(report_id: str, body: ResultMappingsIn, dry_run: bool = False,
                          actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    """Master için aynı rapor bazlı eşleştirme düzeltmesi (ajan API'siyle aynı servis)."""
    _, payload = ops.remap_report_results(db, actor, report_id, body, dry_run, None)
    return payload


@router.post("/reports/{report_id}/restore")
def restore(report_id: str, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    rep = ops.get_report_obj(db, actor, report_id, allow_deleted=True)
    restore_report(db, actor, rep)
    return {"report_id": rep.id, "restored": True}


@router.get("/reports/{report_id}/pdf")
def report_pdf(report_id: str, actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    rep = ops.get_report_obj(db, actor, report_id)
    if not rep.pdf_path:
        raise not_found("PDF")
    data = load_pdf(rep.pdf_path)
    audit(db, actor, "report.pdf_view", "report", rep.id, commit=True)
    fname = f"rimetra-{rep.report_date.isoformat()}.pdf"
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{fname}"', "Cache-Control": "no-store"})


@router.post("/reports/{report_id}/pdf")
async def upload_report_pdf(report_id: str, file: UploadFile = File(...), actor: Actor = Depends(require_master),
                            db: Session = Depends(get_db)):
    return ops.attach_pdf(db, actor, report_id, await file.read(), file.filename)


@router.post("/reports")
def post_report_json(body: ReportIn, dry_run: bool = False, on_overlap: str = "error",
                     actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    """Master'ın arayüzden JSON ile rapor girişi (ajan çıktısını elle yapıştırmak için)."""
    status, payload = ops.post_report(db, actor, body, dry_run, on_overlap, None)
    return payload


@router.get("/compare")
def compare(a: str, b: str, actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    ra = ops.get_report_obj(db, actor, a)
    rb = ops.get_report_obj(db, actor, b)
    if ra.member_id != rb.member_id:
        raise ApiError(400, "VALIDATION_ERROR", "İki rapor aynı üyeye ait olmalı.")
    return queries.compare_reports(db, ra, rb)


# ------------------------------------------------------------------ notlar

@router.get("/members/{member_id}/notes")
def list_notes(member_id: str, actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    _member(db, actor, member_id)
    notes = db.scalars(select(Note).where(Note.member_id == member_id).order_by(Note.date.desc(), Note.created_at.desc()))
    tds = {t.id: t for t in db.scalars(select(TestDefinition))}
    out = []
    for n in notes:
        d = queries.note_public(n)
        td = tds.get(n.test_definition_id)
        d["test_key"] = td.key if td else None
        d["test_name"] = td.display_name if td else None
        d["can_delete"] = actor.is_master or (n.created_by_user_id == actor.id and not actor.read_only)
        out.append(d)
    return {"items": out}


def _can_write_notes(actor: Actor, member_id: str) -> None:
    if actor.is_master:
        return
    if actor.read_only or actor.own_member_id != member_id:
        raise ApiError(403, "FORBIDDEN", "Not ekleme yetkiniz yok.")


@router.post("/members/{member_id}/notes", status_code=201)
def add_note(member_id: str, body: NoteIn, actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    _member(db, actor, member_id)
    _can_write_notes(actor, member_id)
    td = _test(db, body.test_key) if body.test_key else None
    n = Note(member_id=member_id, date=body.date, text=body.text.strip(), test_definition_id=td.id if td else None,
             created_by_user_id=actor.id)
    db.add(n)
    db.flush()
    audit(db, actor, "note.create", "note", n.id, {"member_id": member_id})
    db.commit()
    return queries.note_public(n)


@router.delete("/notes/{note_id}")
def delete_note(note_id: str, actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    n = db.get(Note, note_id)
    if n is None:
        raise not_found("Not")
    actor.require_member(n.member_id)
    if not (actor.is_master or (n.created_by_user_id == actor.id and not actor.read_only)):
        raise ApiError(403, "FORBIDDEN", "Bu notu silemezsiniz.")
    audit(db, actor, "note.delete", "note", n.id)
    db.delete(n)
    db.commit()
    return {"deleted": True}


# ------------------------------------------------------------------ hatırlatıcılar

@router.get("/members/{member_id}/reminders")
def list_reminders(member_id: str, actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    _member(db, actor, member_id)
    return {"items": queries.reminders_status(db, member_id)}


@router.post("/members/{member_id}/reminders", status_code=201)
def add_reminder(member_id: str, body: ReminderIn, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    _member(db, actor, member_id)
    td = _test(db, body.test_key)
    rem = Reminder(member_id=member_id, test_definition_id=td.id, interval_months=body.interval_months, note=body.note)
    db.add(rem)
    db.flush()
    audit(db, actor, "reminder.create", "reminder", rem.id, body.model_dump())
    db.commit()
    return {"id": rem.id}


@router.delete("/reminders/{reminder_id}")
def delete_reminder(reminder_id: str, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    rem = db.get(Reminder, reminder_id)
    if rem is None:
        raise not_found("Hatırlatıcı")
    audit(db, actor, "reminder.delete", "reminder", rem.id)
    db.delete(rem)
    db.commit()
    return {"deleted": True}


# ------------------------------------------------------------------ elle değer girişi

@router.post("/members/{member_id}/manual", status_code=201)
def manual_entry(member_id: str, body: ManualEntryIn, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    _member(db, actor, member_id)
    hh, mm = (body.time or "09:00").split(":")
    sdt = datetime(body.date.year, body.date.month, body.date.day, int(hh), int(mm), tzinfo=ingest.local_tz())
    by_specimen: dict[str, list[ResultIn]] = {}
    for it in body.items:
        td = _test(db, it.test_key)
        by_specimen.setdefault(td.specimen, []).append(ResultIn(
            raw_name=td.display_name, raw_value=it.value, raw_unit=it.unit or td.canonical_unit,
            raw_reference=it.reference, test_key=td.key))
    rep = ReportIn(member_id=member_id, source="manual", report_date=body.date, facility=None,
                   panels=[PanelIn(name="Elle giriş", sample_datetime=sdt, specimen=sp, results=rs) for sp, rs in by_specimen.items()])
    status, payload = ops.post_report(db, actor, rep, False, "error", None)
    if body.note and payload.get("report_id"):
        db.add(Note(member_id=member_id, date=body.date, text=body.note, created_by_user_id=actor.id))
        db.commit()
    return payload


# ------------------------------------------------------------------ katalog ve eşleşmemiş testler

@router.get("/catalog")
def catalog(actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    tds = db.scalars(select(TestDefinition).options(selectinload(TestDefinition.aliases)).order_by(TestDefinition.sort_order))
    return {"items": [queries.test_def_public(td, with_aliases=True, with_info=True) for td in tds], "categories": CATEGORY_ORDER}


@router.post("/catalog/tests", status_code=201)
def create_test(body: TestDefIn, link_raw_name: str | None = None, actor: Actor = Depends(require_master),
                db: Session = Depends(get_db)):
    if db.scalar(select(TestDefinition.id).where(TestDefinition.key == body.key)):
        raise ApiError(409, "DUPLICATE_KEY", "Bu test anahtarı zaten var.")
    td = TestDefinition(**body.model_dump(), sort_order=5000, is_builtin=False)
    db.add(td)
    db.flush()
    audit(db, actor, "catalog.test_create", "test_definition", td.id, body.model_dump())
    db.commit()
    linked = None
    if link_raw_name:
        linked = link_alias(db, actor, link_raw_name, body.specimen, td.key)
    else:
        link_alias(db, actor, body.display_name, body.specimen, td.key)
    return {"test": queries.test_def_public(td), "linked": linked}


@router.patch("/catalog/tests/{key}")
def patch_test(key: str, body: dict, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    td = _test(db, key)
    allowed = {"display_name", "category", "canonical_unit", "unit_rules", "value_type", "info_what", "info_low", "info_high"}
    if not td.is_builtin:
        # Kullanıcının eklediği testlerde anahtar ve numune de düzeltilebilir.
        # Sonuçlar ve alias'lar teste id ile bağlı olduğu için anahtar değişikliği güvenlidir.
        allowed |= {"key", "specimen"}
    changes = {k: v for k, v in body.items() if k in allowed and getattr(td, k) != v}
    if "key" in changes:
        import re as _re
        if not isinstance(changes["key"], str) or not _re.fullmatch(r"[a-z0-9_]+\.[a-z0-9_]+", changes["key"]) or len(changes["key"]) > 80:
            raise ApiError(400, "VALIDATION_ERROR", "Anahtar numune.ad biçiminde olmalı (küçük harf, rakam, _).",
                           fields=[{"field": "key", "message": "Geçersiz biçim"}])
        if db.scalar(select(TestDefinition.id).where(TestDefinition.key == changes["key"])):
            raise ApiError(409, "DUPLICATE_KEY", "Bu test anahtarı zaten var.")
    for f in ("info_what", "info_low", "info_high"):
        if f in changes:
            v = changes[f]
            if v is not None and (not isinstance(v, str) or len(v) > 4000):
                raise ApiError(400, "VALIDATION_ERROR", "Açıklama en fazla 4000 karakter olabilir.",
                               fields=[{"field": f, "message": "Geçersiz"}])
            changes[f] = v.strip() if isinstance(v, str) else v
    changes = {k: v for k, v in changes.items() if getattr(td, k) != v}
    if "specimen" in changes and changes["specimen"] not in ("blood", "serum", "plasma", "urine", "other"):
        raise ApiError(400, "VALIDATION_ERROR", "Geçersiz numune.", fields=[{"field": "specimen", "message": "Geçersiz"}])
    for k, v in changes.items():
        setattr(td, k, v)
    audit(db, actor, "catalog.test_update", "test_definition", td.id, changes)
    db.commit()
    if "unit_rules" in changes or "canonical_unit" in changes:
        from ..services.mutations import recompute_result
        for r in db.scalars(select(Result).where(Result.test_definition_id == td.id)):
            recompute_result(r, td)
        db.commit()
    return queries.test_def_public(td, with_aliases=True, with_info=True)


@router.post("/catalog/aliases", status_code=201)
def create_alias(body: AliasIn, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    return link_alias(db, actor, body.raw_name, body.specimen, body.test_key)


@router.get("/unmapped")
def unmapped(actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    ids = None if actor.member_scope is None else actor.member_scope
    groups = queries.unmapped_groups(db, ids)
    # öneri: aynı numunede benzer adlı testler — ad ve alias'lara göre puanlanır.
    # İlk öneri arayüzde seçili gelir; bu yüzden yalnızca ilk kelime tutan zayıf
    # eşleşmeler ("Üre Azotu" → "Üre") güçlü eşleşmelerin önüne geçmemeli.
    tds = {td.id: td for td in db.scalars(select(TestDefinition))}
    names: dict[str, set[str]] = {tid: {normalize_alias(td.display_name)} for tid, td in tds.items()}
    for a in db.scalars(select(TestAlias)):
        if a.test_definition_id in names:
            names[a.test_definition_id].add(a.alias_normalized)
    bloodlike = ("blood", "serum", "plasma")

    def score(key: str, cand: str) -> float:
        if not key or not cand:
            return 0.0
        if key == cand:
            return 100.0
        if key in cand or cand in key:
            return 50.0 * min(len(key), len(cand)) / max(len(key), len(cand)) + 20.0
        kw, cw = set(key.split(" ")), set(cand.split(" "))
        common = kw & cw
        if common:
            return 30.0 * len(common) / len(kw | cw)
        return 0.0

    for g in groups:
        key = normalize_alias(g["raw_name"])
        scored = []
        for tid, td in tds.items():
            if g["specimen"] and td.specimen != g["specimen"] and not (g["specimen"] in bloodlike and td.specimen in bloodlike):
                continue
            best = max(score(key, n) for n in names[tid])
            if best > 0:
                scored.append((best, td.sort_order or 0, td))
        scored.sort(key=lambda x: (-x[0], x[1]))
        g["suggestions"] = [{"key": td.key, "display_name": td.display_name} for _, _, td in scored[:5]]
    return {"items": groups}


@router.post("/unmapped/dismiss")
def dismiss_unmapped(body: DismissIn, dry_run: bool = False, actor: Actor = Depends(require_master),
                     db: Session = Depends(get_db)):
    """'Sonuç değil': eşleşmemiş satırları gizler (kalıcı silmez, geri alınabilir)."""
    return ops.dismiss_results(db, actor, body, dry_run)


@router.post("/results/restore")
def restore_results(body: RestoreResultsIn, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    return ops.restore_results(db, actor, body)


# ------------------------------------------------------------------ dışa aktarım

@router.get("/members/{member_id}/export.csv")
def export_csv(member_id: str, tests: str = "", actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    m = _member(db, actor, member_id)
    keys = [k for k in tests.split(",") if k]
    data = export.member_csv(db, m, keys)
    audit(db, actor, "export.csv", "member", m.id, {"tests": keys}, commit=True)
    return Response(data, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="rimetra-{fold(m.display_name)}.csv"'})


@router.get("/members/{member_id}/export.pdf")
def export_pdf(member_id: str, tests: str = "", actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    m = _member(db, actor, member_id)
    keys = [k for k in tests.split(",") if k]
    data = export.member_pdf(db, m, keys)
    audit(db, actor, "export.pdf", "member", m.id, {"tests": keys}, commit=True)
    return Response(data, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="rimetra-{fold(m.display_name)}.pdf"'})


# ------------------------------------------------------------------ arama ve takvim

@router.get("/search")
def search(q: str = Query(min_length=1), actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    members = ops.visible_members(db, actor)
    mids = [m.id for m in members]
    names = {m.id: m.display_name for m in members}
    like = f"%{q.strip()}%"
    fq = fold(q)
    out_tests = []
    tds = list(db.scalars(select(TestDefinition)))
    match_ids = [td.id for td in tds if fq in fold(td.display_name) or fq in td.key]
    if match_ids and mids:
        rows = db.execute(select(Result.member_id, Result.test_definition_id).where(
            Result.member_id.in_(mids), Result.test_definition_id.in_(match_ids), Result.deleted_at.is_(None)).distinct())
        tmap = {t.id: t for t in tds}
        for mid, tid in rows:
            out_tests.append({"member_id": mid, "member_name": names[mid], "test_key": tmap[tid].key,
                              "display_name": tmap[tid].display_name})
    reps = db.execute(select(Report, Facility).outerjoin(Facility, Report.facility_id == Facility.id).where(
        Report.member_id.in_(mids), Report.deleted_at.is_(None),
        or_(Facility.name_raw.ilike(like), func.to_char(Report.report_date, "DD.MM.YYYY").ilike(like))
    ).order_by(Report.report_date.desc()).limit(20)).all() if mids else []
    notes = db.scalars(select(Note).where(Note.member_id.in_(mids), Note.text.ilike(like)).limit(20)).all() if mids else []
    return {
        "tests": out_tests[:30],
        "reports": [{"id": r.id, "member_id": r.member_id, "member_name": names[r.member_id],
                     "report_date": r.report_date.isoformat(), "facility": f.name_raw if f else None} for r, f in reps],
        "notes": [{"id": n.id, "member_id": n.member_id, "member_name": names[n.member_id], "date": n.date.isoformat(),
                   "text": n.text} for n in notes],
    }


@router.get("/calendar")
def calendar(year: int, month: int, actor: Actor = Depends(get_user_actor), db: Session = Depends(get_db)):
    members = ops.visible_members(db, actor)
    mids = [m.id for m in members]
    names = {m.id: m.display_name for m in members}
    start = date(year, month, 1)
    end = date(year, month, cal.monthrange(year, month)[1])
    events = []
    if mids:
        reps = db.execute(select(Report, Facility).outerjoin(Facility, Report.facility_id == Facility.id).where(
            Report.member_id.in_(mids), Report.deleted_at.is_(None), Report.report_date.between(start, end))).all()
        counts = queries._report_counts(db, [r.id for r, _ in reps])
        for r, f in reps:
            events.append({"type": "report", "date": r.report_date.isoformat(), "member_id": r.member_id,
                           "member_name": names[r.member_id], "id": r.id, "title": f.name_raw if f else (t("Elle giriş") if r.source == "manual" else t("Rapor")),
                           "out_of_range": counts.get(r.id, {}).get("out", 0), "source": r.source})
        for n in db.scalars(select(Note).where(Note.member_id.in_(mids), Note.date.between(start, end))):
            events.append({"type": "note", "date": n.date.isoformat(), "member_id": n.member_id,
                           "member_name": names[n.member_id], "id": n.id, "title": n.text})
    reminders = []
    for m in members:
        for rem in queries.reminders_status(db, m.id):
            rem["member_name"] = m.display_name
            reminders.append(rem)
            d = date.fromisoformat(rem["due_date"])
            if start <= d <= end:
                events.append({"type": "reminder", "date": rem["due_date"], "member_id": m.id, "member_name": m.display_name,
                               "id": rem["id"], "title": t("{name} kontrolü", name=rem["display_name"]), "status": rem["status"]})
    events.sort(key=lambda e: e["date"])
    return {"year": year, "month": month, "events": events, "reminders": reminders}


# ------------------------------------------------------------------ yönetim: kullanıcılar

@router.get("/admin/users")
def admin_users(actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    users = db.scalars(select(User).order_by(User.created_at))
    return {"items": [{**user_public(u), "is_active": u.is_active, "last_login_at": queries.iso(u.last_login_at),
                       "telegram_chat_id": u.telegram_chat_id} for u in users]}


@router.post("/admin/users", status_code=201)
def admin_create_user(body: UserIn, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    if db.scalar(select(User.id).where(func.lower(User.username) == body.username.lower())):
        raise ApiError(409, "DUPLICATE_USERNAME", "Bu kullanıcı adı alınmış.")
    if body.member_id:
        m = db.get(Member, body.member_id)
        if m is None:
            raise not_found("Üye")
        if m.user is not None:
            raise ApiError(409, "MEMBER_HAS_USER", "Bu profile zaten bir hesap bağlı.")
    elif body.role == "member":
        raise ApiError(400, "VALIDATION_ERROR", "Üye hesabı bir profile bağlanmalı.", fields=[{"field": "member_id", "message": "Gerekli"}])
    u = User(username=body.username, password_hash=hash_password(body.password), role=body.role,
             member_id=body.member_id, read_only=body.read_only)
    db.add(u)
    db.flush()
    audit(db, actor, "user.create", "user", u.id, {"username": u.username, "role": u.role, "member_id": u.member_id})
    db.commit()
    return user_public(u)


@router.patch("/admin/users/{user_id}")
def admin_patch_user(user_id: str, body: UserPatch, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if u is None:
        raise not_found("Kullanıcı")
    ch = body.model_dump(exclude_unset=True)
    if u.id == actor.id and ch.get("is_active") is False:
        raise ApiError(400, "FORBIDDEN", "Kendi hesabınızı pasifleştiremezsiniz.")
    if "password" in ch and ch["password"]:
        u.password_hash = hash_password(ch["password"])
        db.query(UserSession).filter(UserSession.user_id == u.id).delete()
    for k in ("is_active", "read_only", "member_id"):
        if k in ch:
            setattr(u, k, ch[k])
    if "telegram_chat_id" in ch:
        from ..services import telegram
        if ch["telegram_chat_id"] is None:
            telegram.unlink_user(u)
        elif ch["telegram_chat_id"] != u.telegram_chat_id:
            telegram.link_chat(db, u, ch["telegram_chat_id"], None)
    if ch.get("is_active") is False:
        db.query(UserSession).filter(UserSession.user_id == u.id).delete()
    audit(db, actor, "user.update", "user", u.id, {k: v for k, v in ch.items() if k != "password"} | ({"password": "***"} if "password" in ch else {}))
    db.commit()
    return user_public(u)


@router.delete("/admin/users/{user_id}")
def admin_delete_user(user_id: str, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if u is None:
        raise not_found("Kullanıcı")
    if u.id == actor.id:
        raise ApiError(400, "FORBIDDEN", "Kendi hesabınızı silemezsiniz.")
    audit(db, actor, "user.delete", "user", u.id, {"username": u.username})
    db.delete(u)
    db.commit()
    return {"deleted": True}


# ------------------------------------------------------------------ yönetim: API anahtarları

def _key_public(k: ApiKey) -> dict:
    return {"id": k.id, "name": k.name, "key_prefix": f"rmt_live_{k.key_prefix}…", "scopes": k.scopes,
            "member_scope": k.member_scope, "created_at": queries.iso(k.created_at),
            "last_used_at": queries.iso(k.last_used_at), "revoked_at": queries.iso(k.revoked_at)}


@router.get("/admin/api-keys")
def admin_keys(actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    return {"items": [_key_public(k) for k in db.scalars(select(ApiKey).order_by(ApiKey.created_at.desc()))]}


@router.post("/admin/api-keys", status_code=201)
def admin_create_key(body: ApiKeyIn, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    bad = [s for s in body.scopes if s not in SCOPES]
    if bad:
        raise ApiError(400, "VALIDATION_ERROR", f"Bilinmeyen yetki: {', '.join(bad)}")
    if body.member_scope:
        found = set(db.scalars(select(Member.id).where(Member.id.in_(body.member_scope))))
        if found != set(body.member_scope):
            raise ApiError(400, "VALIDATION_ERROR", "Bilinmeyen üye kimliği.")
    full, prefix, h = generate_api_key()
    k = ApiKey(name=body.name, key_prefix=prefix, key_hash=h, scopes=body.scopes,
               member_scope=body.member_scope or None, created_by=actor.id)
    db.add(k)
    db.flush()
    audit(db, actor, "api_key.create", "api_key", k.id, {"name": k.name, "scopes": k.scopes, "member_scope": k.member_scope})
    db.commit()
    return {**_key_public(k), "key": full}


@router.post("/admin/api-keys/{key_id}/revoke")
def admin_revoke_key(key_id: str, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    k = db.get(ApiKey, key_id)
    if k is None:
        raise not_found("API anahtarı")
    if k.revoked_at is None:
        k.revoked_at = utcnow()
        audit(db, actor, "api_key.revoke", "api_key", k.id, {"name": k.name})
        db.commit()
        forget_api_key_cache()
    return _key_public(k)


# ------------------------------------------------------------------ yönetim: denetim kaydı

@router.get("/admin/audit")
def admin_audit(limit: int = 100, offset: int = 0, action: str | None = None, hide_api_calls: bool = False,
                actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    q = select(AuditLog)
    if action:
        q = q.where(AuditLog.action.ilike(f"{action}%"))
    if hide_api_calls:
        q = q.where(AuditLog.action.not_in(["api.call", "mcp.call"]))
    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(q.order_by(AuditLog.id.desc()).limit(min(limit, 500)).offset(offset))
    return {"total": total, "items": [{
        "id": a.id, "actor_type": a.actor_type, "actor_label": a.actor_label, "action": a.action, "entity": a.entity,
        "entity_id": a.entity_id, "payload_diff": a.payload_diff, "ip": a.ip, "created_at": queries.iso(a.created_at)} for a in rows]}


# ------------------------------------------------------------------ yönetim: yedekleme

@router.get("/admin/backups")
def admin_backups(actor: Actor = Depends(require_master)):
    return {"items": backup.list_backups(), "status": backup.last_status()}


@router.post("/admin/backups", status_code=201)
def admin_run_backup(actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    info = backup.run_backup()
    audit(db, actor, "backup.manual", "backup", info["name"], commit=True)
    return info


@router.get("/admin/backups/{name}")
def admin_download_backup(name: str, actor: Actor = Depends(require_master), db: Session = Depends(get_db)):
    path = backup.backup_path(name)
    audit(db, actor, "backup.download", "backup", name, commit=True)
    return Response(path.read_bytes(), media_type="application/octet-stream",
                    headers={"Content-Disposition": f'attachment; filename="{path.name}"'})


# ------------------------------------------------------------------ Telegram botu (her kullanıcı kendi hesabı için)

def _telegram_me(u: User) -> dict:
    from ..services import telegram
    st = telegram.public_status()
    return {**st, **user_public(u)["telegram"],
            "bot_url": f"https://t.me/{st['bot_username']}" if st["bot_username"] else None}


@router.get("/telegram")
def telegram_me(user: User = Depends(get_user)):
    from ..services import telegram
    if get_settings().telegram_enabled and not telegram.status.bot_username:
        telegram.bot_username()
    return _telegram_me(user)


@router.post("/telegram/link")
def telegram_link(request: Request, user: User = Depends(get_user), db: Session = Depends(get_db)):
    from ..services import telegram
    if not get_settings().telegram_enabled:
        raise ApiError(400, "TELEGRAM_DISABLED", "Telegram botu kapalı. Sunucudaki .env dosyasına TELEGRAM_BOT_TOKEN ekleyin.")
    name = telegram.bot_username()
    if not name:
        raise ApiError(503, "TELEGRAM_UNAVAILABLE", telegram.status.last_error or "Telegram'a ulaşılamadı.")
    code, ttl = telegram.create_link_code(db, user)
    audit(db, actor_for_user(user, client_ip(request)), "telegram.link_code", "user", user.id, commit=True)
    return {"url": f"https://t.me/{name}?start={code}", "code": code, "bot_username": name, "expires_in": ttl}


@router.patch("/telegram")
def telegram_prefs(body: dict, request: Request, user: User = Depends(get_user), db: Session = Depends(get_db)):
    if "notify" in body:
        user.telegram_notify = bool(body["notify"])
        audit(db, actor_for_user(user, client_ip(request)), "telegram.notify", "user", user.id, {"notify": user.telegram_notify})
        db.commit()
    return _telegram_me(user)


@router.delete("/telegram")
def telegram_unlink(request: Request, user: User = Depends(get_user), db: Session = Depends(get_db)):
    from ..services import telegram
    telegram.unlink_user(user)
    audit(db, actor_for_user(user, client_ip(request)), "telegram.unlink", "user", user.id, {"by": "web"})
    db.commit()
    return _telegram_me(user)
