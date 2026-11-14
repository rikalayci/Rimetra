from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..config import get_settings
from ..deps import Actor
from ..errors import ApiError
from ..models import Member, Report, Result, TestAlias, TestDefinition, utcnow
from ..parsing import (
    ParsedReference,
    apply_unit_rules,
    compute_flag,
    normalize_alias,
    parse_reference,
    parse_value,
)
from .audit import audit
from .files import delete_file


def link_alias(db: Session, actor: Actor, raw_name: str, specimen: str, test_key: str) -> dict:
    """Ham adı bir test tanımına bağlar ve bekleyen eşleşmemiş sonuçları günceller."""
    td = db.scalar(select(TestDefinition).where(TestDefinition.key == test_key))
    if td is None:
        raise ApiError(400, "VALIDATION_ERROR", "Bilinmeyen test anahtarı.", fields=[{"field": "test_key", "message": "Bulunamadı"}])
    alias_key = normalize_alias(raw_name)
    existing = db.scalar(select(TestAlias).where(TestAlias.alias_normalized == alias_key, TestAlias.specimen == specimen))
    if existing is not None and existing.test_definition_id != td.id:
        old = db.get(TestDefinition, existing.test_definition_id)
        existing.test_definition_id = td.id
        audit(db, actor, "alias.relink", "test_alias", existing.id, {"alias": alias_key, "from": old.key if old else None, "to": td.key})
    elif existing is None:
        a = TestAlias(test_definition_id=td.id, alias_normalized=alias_key, specimen=specimen)
        db.add(a)
        db.flush()
        audit(db, actor, "alias.create", "test_alias", a.id, {"alias": alias_key, "specimen": specimen, "test_key": td.key})

    # Bekleyen eşleşmemiş sonuçları bağla
    from .catalog import BLOODLIKE
    same_group = list(BLOODLIKE) if specimen in BLOODLIKE else [specimen]
    pending = db.scalars(select(Result).where(Result.test_definition_id.is_(None), Result.deleted_at.is_(None),
                                         Result.specimen.in_(same_group))).all()
    linked, conflicts = 0, 0
    for r in pending:
        if normalize_alias(r.raw_name) != alias_key:
            continue
        clash = db.scalar(select(Result.id).where(
            Result.member_id == r.member_id, Result.test_definition_id == td.id,
            Result.sample_datetime == r.sample_datetime, Result.deleted_at.is_(None),
            (Result.facility_id == r.facility_id) if r.facility_id else Result.facility_id.is_(None),
        ))
        if clash:
            conflicts += 1
            continue
        r.test_definition_id = td.id
        recompute_result(r, td)
        linked += 1
    db.commit()
    return {"test_key": td.key, "alias": alias_key, "specimen": specimen, "linked_results": linked, "conflicts": conflicts}


def relink_unmapped(db: Session) -> tuple[int, int]:
    """Katalogdaki alias'larla artık eşleşen bekleyen sonuçları bağlar (açılışta, seed sonrası)."""
    from ..parsing import parse_value
    from .catalog import CatalogResolver

    resolver = CatalogResolver(db)
    pending = db.scalars(select(Result).where(Result.test_definition_id.is_(None), Result.deleted_at.is_(None))).all()
    linked, conflicts = 0, 0
    for r in pending:
        td = resolver.resolve(normalize_alias(r.raw_name), r.specimen, parse_value(r.raw_value))
        if td is None:
            continue
        clash = db.scalar(select(Result.id).where(
            Result.id != r.id, Result.member_id == r.member_id, Result.test_definition_id == td.id,
            Result.sample_datetime == r.sample_datetime, Result.deleted_at.is_(None),
            (Result.facility_id == r.facility_id) if r.facility_id else Result.facility_id.is_(None),
        ))
        if clash:
            conflicts += 1
            continue
        r.test_definition_id = td.id
        recompute_result(r, td)
        db.flush()
        linked += 1
    db.commit()
    return linked, conflicts


def recompute_result(r: Result, td: TestDefinition | None) -> None:
    val = parse_value(r.raw_value)
    ref = parse_reference(r.raw_reference)
    rules = td.unit_rules if td else None
    if rules:
        ref = ParsedReference(ref_low=apply_unit_rules(ref.ref_low, rules), ref_high=apply_unit_rules(ref.ref_high, rules),
                              ref_low_exclusive=ref.ref_low_exclusive, ref_high_exclusive=ref.ref_high_exclusive,
                              ref_text=ref.ref_text, ref_note=ref.ref_note)
        val.value_numeric = apply_unit_rules(val.value_numeric, rules)
    if val.skip:
        return
    r.value_numeric, r.value_text, r.value_qualifier = val.value_numeric, val.value_text, val.value_qualifier
    r.ref_low, r.ref_high = ref.ref_low, ref.ref_high
    r.ref_low_exclusive, r.ref_high_exclusive = ref.ref_low_exclusive, ref.ref_high_exclusive
    r.ref_text, r.ref_note = ref.ref_text, ref.ref_note
    r.unit_canonical = (td.canonical_unit if td and td.canonical_unit else r.unit_raw)
    r.flag_computed = compute_flag(val, ref)


def soft_delete_report(db: Session, actor: Actor, rep: Report) -> None:
    now = utcnow()
    rep.deleted_at = now
    # Önceden gizlenmiş ("Sonuç değil") satırlar kendi zaman damgalarını korur; geri yüklemede geri gelmezler
    db.execute(update(Result).where(Result.report_id == rep.id, Result.deleted_at.is_(None)).values(deleted_at=now))
    audit(db, actor, "report.delete", "report", rep.id, {"member_id": rep.member_id, "report_date": rep.report_date.isoformat()})
    db.commit()


def restore_report(db: Session, actor: Actor, rep: Report) -> None:
    if rep.deleted_at is None:
        return
    if rep.deleted_at < utcnow() - timedelta(days=get_settings().report_restore_days):
        raise ApiError(400, "RESTORE_EXPIRED", "Geri alma süresi dolmuş.")
    dup = db.scalar(select(Report.id).where(Report.member_id == rep.member_id, Report.content_fingerprint == rep.content_fingerprint,
                                            Report.deleted_at.is_(None)))
    if dup:
        raise ApiError(409, "DUPLICATE_REPORT", "Aynı rapor daha sonra yeniden girilmiş.", existing_report_id=dup)
    results = db.scalars(select(Result).where(Result.report_id == rep.id, Result.deleted_at == rep.deleted_at)).all()
    for r in results:
        if r.test_definition_id is None:
            continue
        clash = db.scalar(select(Result.report_id).where(
            Result.member_id == r.member_id, Result.test_definition_id == r.test_definition_id,
            Result.sample_datetime == r.sample_datetime, Result.deleted_at.is_(None),
            (Result.facility_id == r.facility_id) if r.facility_id else Result.facility_id.is_(None)))
        if clash:
            raise ApiError(409, "OVERLAPPING_RESULTS", "Bazı sonuçlar başka bir raporda kayıtlı.",
                           conflicts=[{"raw_name": r.raw_name, "existing_report_id": clash}])
    deleted_at = rep.deleted_at
    rep.deleted_at = None
    db.execute(update(Result).where(Result.report_id == rep.id, Result.deleted_at == deleted_at).values(deleted_at=None))
    audit(db, actor, "report.restore", "report", rep.id)
    db.commit()


def purge_expired_reports(db: Session) -> int:
    cutoff = utcnow() - timedelta(days=get_settings().report_restore_days)
    reps = db.scalars(select(Report).where(Report.deleted_at.is_not(None), Report.deleted_at < cutoff)).all()
    for rep in reps:
        delete_file(rep.pdf_path)
        audit(db, None, "report.purge", "report", rep.id)
        db.delete(rep)
    db.commit()
    return len(reps)


def delete_member_completely(db: Session, actor: Actor, m: Member) -> None:
    reps = db.scalars(select(Report).where(Report.member_id == m.id)).all()
    for rep in reps:
        delete_file(rep.pdf_path)
    delete_file(m.avatar_path)
    if m.user:
        db.delete(m.user)
    audit(db, actor, "member.delete", "member", m.id, {"display_name": m.display_name, "reports": len(reps)})
    db.delete(m)
    db.commit()
