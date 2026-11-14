"""Sonuç olmayan satırları gizleme ("Sonuç değil").

Ajanın yanlışlıkla sonuç diye gönderdiği satırlar (ör. e-Nabız istem satırı
"Kan Sayımı Otomatik Hemogram (geniş panel) | Kan | : | 1 | 03.06.2023") eşleşmemiş
testlerde birikir. Bunlar kalıcı olarak silinmez: `deleted_at` ile gizlenir, denetim
kaydına yazılır ve geri alınabilir. Rapor, PDF ve rapor parmak izi değişmez.

Yalnızca eşleşmemiş (test_definition_id IS NULL) sonuçlar gizlenebilir; bir teste bağlı
sonuç için doğru yol eşleştirme düzeltmesi ya da raporu silip yeniden girmektir.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..deps import Actor
from ..errors import ApiError
from ..models import Report, Result, utcnow
from .audit import audit


def _visible(actor: Actor, q):
    if actor.member_scope is not None:
        q = q.where(Result.member_id.in_(actor.member_scope or ["-"]))
    return q


def _public(r: Result) -> dict:
    return {"result_id": r.id, "report_id": r.report_id, "member_id": r.member_id, "raw_name": r.raw_name,
            "raw_value": r.raw_value, "raw_unit": r.raw_unit, "specimen": r.specimen,
            "sample_datetime": r.sample_datetime.isoformat() if r.sample_datetime else None}


def dismiss_results(db: Session, actor: Actor, reason: str, dry_run: bool, *,
                    result_ids: list[str] | None = None, raw_name: str | None = None,
                    specimen: str | None = None) -> dict:
    """Ya `result_ids` ya da (`raw_name`, `specimen`) grubu verilir."""
    if bool(result_ids) == bool(raw_name):
        raise ApiError(400, "VALIDATION_ERROR", "Ya result_ids ya da raw_name (+ specimen) gönderin.",
                       fields=[{"field": "result_ids", "message": "result_ids veya raw_name"}])

    q = select(Result).join(Report, Report.id == Result.report_id).where(Report.deleted_at.is_(None))
    if result_ids:
        ids = list(dict.fromkeys(result_ids))
        rows = {r.id: r for r in db.scalars(q.where(Result.id.in_(ids)).with_for_update(of=Result))}
        missing = [i for i in ids if i not in rows]
        if missing:
            raise ApiError(404, "NOT_FOUND", "Bazı sonuçlar bulunamadı.", result_ids=missing)
        for r in rows.values():
            actor.require_member(r.member_id)
        gone = [i for i in ids if rows[i].deleted_at is not None]
        if gone:
            raise ApiError(409, "RESULT_INACTIVE", "Bazı sonuçlar zaten gizlenmiş/silinmiş.", result_ids=gone)
        mapped = [{"result_id": i, "raw_name": rows[i].raw_name} for i in ids if rows[i].test_definition_id is not None]
        if mapped:
            raise ApiError(409, "RESULT_MAPPED",
                           "Bir teste bağlı sonuçlar gizlenemez; eşleştirmeyi düzeltin ya da raporu silip yeniden girin.",
                           results=mapped)
        targets = [rows[i] for i in ids]
    else:
        q = _visible(actor, q.where(Result.test_definition_id.is_(None), Result.deleted_at.is_(None),
                                    Result.raw_name == raw_name,
                                    Result.specimen.is_(None) if specimen is None else Result.specimen == specimen))
        targets = list(db.scalars(q.order_by(Result.sample_datetime).with_for_update(of=Result)))
        if not targets:
            raise ApiError(404, "NOT_FOUND", "Bu ada sahip eşleşmemiş sonuç bulunamadı.")

    items = [_public(r) for r in targets]
    payload = {"dry_run": dry_run, "dismissed_count": len(items), "results": items}
    if dry_run:
        db.rollback()
        return payload

    now = utcnow()
    for r in targets:
        r.deleted_at = now
        audit(db, actor, "result.dismiss", "result", r.id,
              {"report_id": r.report_id, "raw_name": r.raw_name, "raw_value": r.raw_value, "reason": reason})
    db.commit()
    return payload


def restore_dismissed(db: Session, actor: Actor, result_ids: list[str]) -> dict:
    """Gizlenmiş satırları geri getirir (rapor silinmemiş olmalı)."""
    ids = list(dict.fromkeys(result_ids))
    rows = {r.id: r for r in db.scalars(
        select(Result).join(Report, Report.id == Result.report_id)
        .where(Result.id.in_(ids), Report.deleted_at.is_(None)).with_for_update(of=Result))}
    missing = [i for i in ids if i not in rows or rows[i].deleted_at is None]
    if missing:
        raise ApiError(404, "NOT_FOUND", "Gizlenmiş sonuç bulunamadı.", result_ids=missing)
    for r in rows.values():
        actor.require_member(r.member_id)
        if r.test_definition_id is not None:  # olmamalı; gizlenen satırlar hep eşleşmemiştir
            raise ApiError(409, "RESULT_MAPPED", "Bu sonuç bir teste bağlı.", result_ids=[r.id])
    for r in rows.values():
        r.deleted_at = None
        audit(db, actor, "result.undismiss", "result", r.id, {"report_id": r.report_id, "raw_name": r.raw_name})
    db.commit()
    return {"restored_count": len(rows), "results": [_public(rows[i]) for i in ids]}
