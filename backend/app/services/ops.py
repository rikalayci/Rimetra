"""REST API, web arayüzü ve MCP'nin ortak kullandığı işlemler (servis katmanı)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import get_settings
from ..deps import Actor
from ..errors import ApiError, not_found
from ..models import Member, Report, TestDefinition
from ..schemas import AliasIn, DismissIn, MemberIn, ReportIn, RestoreResultsIn, ResultMappingsIn
from . import idempotency, ingest, queries
from .audit import audit
from .files import is_pdf, store_pdf
from .mutations import link_alias, soft_delete_report


def me(actor: Actor, db: Session) -> dict:
    members = visible_members(db, actor)
    return {
        "name": actor.label,
        "kind": actor.kind,
        "scopes": sorted(actor.scopes),
        "member_scope": actor.member_scope,
        "members": [{"id": m.id, "display_name": m.display_name} for m in members],
    }


def visible_members(db: Session, actor: Actor) -> list[Member]:
    q = select(Member).order_by(Member.sort_order, Member.created_at)
    if actor.member_scope is not None:
        if not actor.member_scope:
            return []
        q = q.where(Member.id.in_(actor.member_scope))
    return list(db.scalars(q))


def list_members(db: Session, actor: Actor) -> list[dict]:
    actor.require_scope("members:read")
    return [
        {"id": m.id, "display_name": m.display_name, "full_name": m.full_name, "birth_year": m.birth_year, "sex": m.sex}
        for m in visible_members(db, actor)
    ]


def create_member(db: Session, actor: Actor, body: MemberIn) -> dict:
    actor.require_scope("members:write")
    if actor.member_scope is not None:
        raise ApiError(403, "MEMBER_DENIED", "Üye kısıtlı anahtar yeni üye oluşturamaz.")
    m = Member(**body.model_dump())
    db.add(m)
    db.flush()
    audit(db, actor, "member.create", "member", m.id, body.model_dump())
    db.commit()
    return queries.member_public(m)


def get_member(db: Session, actor: Actor, member_id: str) -> Member:
    m = db.get(Member, member_id)
    if m is None:
        raise not_found("Üye")
    actor.require_member(m.id)
    return m


def catalog_tests(db: Session, actor: Actor) -> list[dict]:
    actor.require_scope("reports:read")
    tds = db.scalars(select(TestDefinition).options(selectinload(TestDefinition.aliases)).order_by(TestDefinition.sort_order))
    return [queries.test_def_public(td, with_aliases=True) for td in tds]


def create_alias(db: Session, actor: Actor, body: AliasIn) -> dict:
    actor.require_scope("catalog:write")
    return link_alias(db, actor, body.raw_name, body.specimen, body.test_key)


def post_report(db: Session, actor: Actor, body: ReportIn, dry_run: bool, on_overlap: str, idem_key: str | None) -> tuple[int, dict]:
    actor.require_scope("reports:write")
    if on_overlap not in ("error", "skip_existing"):
        raise ApiError(400, "VALIDATION_ERROR", "on_overlap 'error' veya 'skip_existing' olmalı.",
                       fields=[{"field": "on_overlap", "message": "Geçersiz"}])
    actor.require_member(body.member_id)
    from ..security import sha256_hex
    rhash = sha256_hex(ingest.body_hash(body) + on_overlap)
    scope = f"{actor.kind}:{actor.id}"
    if not dry_run:
        prev = idempotency.lookup(db, scope, idem_key, rhash)
        if prev is not None:
            return prev
    if body.pdf_sha256:
        dup = db.scalar(select(Report.id).where(Report.member_id == body.member_id,
                                               Report.pdf_sha256 == body.pdf_sha256.lower(), Report.deleted_at.is_(None)))
        if dup:
            raise ApiError(409, "DUPLICATE_REPORT", "Bu PDF dosyası zaten yüklenmiş.", existing_report_id=dup)
    status, payload = ingest.submit_report(db, actor, body, dry_run=dry_run, on_overlap=on_overlap,
                                           pdf_sha256=body.pdf_sha256.lower() if body.pdf_sha256 else None)
    if not dry_run:
        idempotency.store(db, scope, idem_key, rhash, status, payload)
    return status, payload


def get_report_obj(db: Session, actor: Actor, report_id: str, allow_deleted: bool = False) -> Report:
    rep = db.scalar(select(Report).options(selectinload(Report.facility)).where(Report.id == report_id))
    if rep is None or (rep.deleted_at is not None and not allow_deleted):
        raise not_found("Rapor")
    actor.require_member(rep.member_id)
    return rep


def attach_pdf(db: Session, actor: Actor, report_id: str, data: bytes, filename: str | None) -> dict:
    actor.require_scope("reports:write")
    rep = get_report_obj(db, actor, report_id)
    if len(data) > get_settings().max_pdf_mb * 1024 * 1024:
        raise ApiError(400, "VALIDATION_ERROR", "PDF çok büyük.", fields=[{"field": "file", "message": "Boyut sınırı"}])
    if not is_pdf(data):
        raise ApiError(400, "VALIDATION_ERROR", "Dosya PDF değil.", fields=[{"field": "file", "message": "PDF bekleniyor"}])
    import hashlib
    sha = hashlib.sha256(data).hexdigest()
    other = db.scalar(select(Report.id).where(Report.member_id == rep.member_id, Report.pdf_sha256 == sha,
                                             Report.id != rep.id, Report.deleted_at.is_(None)))
    if other:
        raise ApiError(409, "DUPLICATE_REPORT", "Bu PDF başka bir rapora zaten eklenmiş.", existing_report_id=other)
    if rep.pdf_path and rep.pdf_sha256 == sha:
        return {"report_id": rep.id, "pdf_sha256": sha, "already_attached": True}
    from .files import delete_file
    old = rep.pdf_path
    rel, sha = store_pdf(rep.member_id, rep.id, data)
    rep.pdf_path, rep.pdf_sha256, rep.pdf_original_name = rel, sha, (filename or "rapor.pdf")[:300]
    audit(db, actor, "report.pdf_attach", "report", rep.id, {"sha256": sha, "bytes": len(data)})
    db.commit()
    delete_file(old)
    return {"report_id": rep.id, "pdf_sha256": sha, "already_attached": False}


def member_reports(db: Session, actor: Actor, member_id: str, limit: int, offset: int) -> dict:
    actor.require_scope("reports:read")
    get_member(db, actor, member_id)
    return queries.list_reports(db, member_id, min(max(limit, 1), 200), max(offset, 0))


def get_report(db: Session, actor: Actor, report_id: str) -> dict:
    actor.require_scope("reports:read")
    return queries.report_detail(db, get_report_obj(db, actor, report_id))


def remap_report_results(db: Session, actor: Actor, report_id: str, body: ResultMappingsIn, dry_run: bool,
                         idem_key: str | None) -> tuple[int, dict]:
    """Rapordaki seçili sonuçların test bağlantısını düzeltir. Katalog/alias değişmez → reports:write yeterli."""
    actor.require_scope("reports:write")
    rep = get_report_obj(db, actor, report_id)
    from .remap import remap_results
    return remap_results(db, actor, rep, body, dry_run, idem_key)


def unmapped(db: Session, actor: Actor) -> list[dict]:
    actor.require_scope("reports:read")
    return queries.unmapped_groups(db, actor.member_scope)


def dismiss_results(db: Session, actor: Actor, body: DismissIn, dry_run: bool) -> dict:
    """Eşleşmemiş, sonuç olmayan satırları gizler (geri alınabilir)."""
    actor.require_scope("reports:write")
    from .dismiss import dismiss_results as _dismiss
    return _dismiss(db, actor, body.reason, dry_run, result_ids=body.result_ids,
                    raw_name=body.raw_name, specimen=body.specimen)


def restore_results(db: Session, actor: Actor, body: RestoreResultsIn) -> dict:
    actor.require_scope("reports:write")
    from .dismiss import restore_dismissed
    return restore_dismissed(db, actor, body.result_ids)


def delete_report(db: Session, actor: Actor, report_id: str) -> dict:
    actor.require_scope("reports:write")
    rep = get_report_obj(db, actor, report_id)
    soft_delete_report(db, actor, rep)
    return {"report_id": rep.id, "deleted": True, "restore_days": get_settings().report_restore_days}


def test_history(db: Session, actor: Actor, member_id: str, test_key: str) -> dict:
    actor.require_scope("reports:read")
    get_member(db, actor, member_id)
    td = db.scalar(select(TestDefinition).where(TestDefinition.key == test_key))
    if td is None:
        raise not_found("Test")
    return queries.test_history(db, member_id, td)


def member_summary(db: Session, actor: Actor, member_id: str, since=None) -> dict:
    actor.require_scope("reports:read")
    get_member(db, actor, member_id)
    return queries.member_summary(db, member_id, since)
