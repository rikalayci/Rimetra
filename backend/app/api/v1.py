"""Ajan API'si — /api/v1 (Bearer API anahtarı ile)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, Header, Query, Request, UploadFile
from fastapi.responses import JSONResponse, Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import Actor, get_api_actor
from ..schemas import AliasIn, DismissIn, MemberIn, ReportIn, RestoreResultsIn, ResultMappingsIn
from ..services import ops
from ..services.audit import audit


def api_actor_logged(request: Request, actor: Actor = Depends(get_api_actor), db: Session = Depends(get_db)) -> Actor:
    audit(db, actor, "api.call", request.method, request.url.path[:64], {"query": str(request.url.query)[:300]} if request.url.query else None, commit=True)
    return actor


router = APIRouter(prefix="/api/v1", tags=["Ajan API"])


@router.get("/me")
def me(actor: Actor = Depends(api_actor_logged), db: Session = Depends(get_db)):
    return ops.me(actor, db)


@router.get("/members")
def list_members(actor: Actor = Depends(api_actor_logged), db: Session = Depends(get_db)):
    return {"items": ops.list_members(db, actor)}


@router.post("/members", status_code=201)
def create_member(body: MemberIn, actor: Actor = Depends(api_actor_logged), db: Session = Depends(get_db)):
    return ops.create_member(db, actor, body)


@router.get("/catalog/tests")
def catalog_tests(actor: Actor = Depends(api_actor_logged), db: Session = Depends(get_db)):
    return {"items": ops.catalog_tests(db, actor)}


@router.post("/catalog/aliases", status_code=201)
def create_alias(body: AliasIn, actor: Actor = Depends(api_actor_logged), db: Session = Depends(get_db)):
    return ops.create_alias(db, actor, body)


@router.post("/reports")
def post_report(
    body: ReportIn,
    dry_run: bool = Query(False),
    on_overlap: str = Query("error"),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: Actor = Depends(api_actor_logged),
    db: Session = Depends(get_db),
):
    status, payload = ops.post_report(db, actor, body, dry_run, on_overlap, idempotency_key)
    return JSONResponse(payload, status_code=status)


@router.post("/reports/{report_id}/pdf")
async def attach_pdf(report_id: str, file: UploadFile = File(...), actor: Actor = Depends(api_actor_logged),
                     db: Session = Depends(get_db)):
    data = await file.read()
    return ops.attach_pdf(db, actor, report_id, data, file.filename)


@router.get("/members/{member_id}/reports")
def member_reports(member_id: str, limit: int = 50, offset: int = 0, actor: Actor = Depends(api_actor_logged),
                   db: Session = Depends(get_db)):
    return ops.member_reports(db, actor, member_id, limit, offset)


@router.get("/reports/{report_id}")
def get_report(report_id: str, actor: Actor = Depends(api_actor_logged), db: Session = Depends(get_db)):
    return ops.get_report(db, actor, report_id)


@router.post("/reports/{report_id}/result-mappings")
def remap_result_mappings(
    report_id: str,
    body: ResultMappingsIn,
    dry_run: bool = Query(False),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    actor: Actor = Depends(api_actor_logged),
    db: Session = Depends(get_db),
):
    """Bu rapordaki seçili sonuçların standart test bağlantısını düzeltir (genel alias kurallarına dokunmaz)."""
    status, payload = ops.remap_report_results(db, actor, report_id, body, dry_run, idempotency_key)
    return JSONResponse(payload, status_code=status)


@router.get("/unmapped")
def unmapped(actor: Actor = Depends(api_actor_logged), db: Session = Depends(get_db)):
    """Kataloğa eşlenmemiş sonuçlar, ham ada göre gruplu (result_ids ile)."""
    return {"items": ops.unmapped(db, actor)}


@router.post("/results/dismiss")
def dismiss_results(body: DismissIn, dry_run: bool = Query(False), actor: Actor = Depends(api_actor_logged),
                    db: Session = Depends(get_db)):
    """Sonuç olmayan eşleşmemiş satırları gizler (ör. e-Nabız istem satırları). Geri alınabilir."""
    return ops.dismiss_results(db, actor, body, dry_run)


@router.post("/results/restore")
def restore_results(body: RestoreResultsIn, actor: Actor = Depends(api_actor_logged), db: Session = Depends(get_db)):
    """Gizlenmiş satırları geri getirir."""
    return ops.restore_results(db, actor, body)


@router.delete("/reports/{report_id}")
def delete_report(report_id: str, actor: Actor = Depends(api_actor_logged), db: Session = Depends(get_db)):
    return ops.delete_report(db, actor, report_id)


@router.get("/members/{member_id}/tests/{test_key}/history")
def test_history(member_id: str, test_key: str, actor: Actor = Depends(api_actor_logged), db: Session = Depends(get_db)):
    return ops.test_history(db, actor, member_id, test_key)


@router.get("/members/{member_id}/summary")
def member_summary(member_id: str, actor: Actor = Depends(api_actor_logged), db: Session = Depends(get_db)):
    return ops.member_summary(db, actor, member_id)


@router.get("/agent/skill")
def agent_skill(actor: Actor = Depends(api_actor_logged)):
    """Ajanın e-Nabız PDF giriş talimatları (SKILL.md). Kurulum komutları bu adresten indirir."""
    from ..agent_skill import read_skill
    from ..errors import not_found
    text = read_skill()
    if text is None:
        raise not_found("Skill dosyası")
    return Response(text, media_type="text/markdown; charset=utf-8")
