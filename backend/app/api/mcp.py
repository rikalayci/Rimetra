"""MCP sunucusu — /mcp (Streamable HTTP, JSON yanıt). Kimlik doğrulama: aynı API anahtarı."""
from __future__ import annotations

import base64
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from sqlalchemy.orm import Session

from ..i18n import translate
from ..db import get_db
from ..deps import Actor, get_api_actor
from ..errors import ApiError
from ..schemas import DismissIn, ReportIn, RestoreResultsIn, ResultMappingsIn
from ..security import check_preview_token, make_preview_token
from ..services import ingest, ops
from ..services.audit import audit

router = APIRouter(tags=["MCP"])

SUPPORTED_VERSIONS = ["2025-06-18", "2025-03-26", "2024-11-05", "2025-11-25"]
SERVER_INFO = {"name": "rimetra", "title": "Rimetra — Aile Tahlil Takip", "version": "1.3.0"}

INSTRUCTIONS = (
    "Rimetra aile tahlil sonuçlarını saklar. İş akışı: list_members ile üyeleri al; PDF'teki 'Adı/Soyadı' ile "
    "üyeyi eşleştir (emin değilsen kullanıcıya sor, tahmin etme). Ham metinleri olduğu gibi gönder (raw_*). "
    "Sayfalara bölünmüş hücreleri birleştir, '.' değerli satırları atla, TC kimlik numarasını asla gönderme. "
    "Önce preview_report ile önizle, sonucu kullanıcıya özetle; kullanıcı onaylarsa aynı gövdeyi preview_token ile "
    "submit_report'a gönder. DUPLICATE_REPORT gelirse 'Bu rapor zaten kayıtlı' de ve dur; veriyi değiştirerek tekrar deneme. "
    "e-Nabız istem satırlarını ('… | Kan | : | 1 | tarih') sonuç olarak gönderme."
)

_REPORT_SCHEMA = {
    "type": "object",
    "description": "Rapor gövdesi (REST POST /api/v1/reports ile aynı).",
    "required": ["member_id", "report_date", "panels"],
    "properties": {
        "member_id": {"type": "string"},
        "source": {"type": "string", "default": "enabiz"},
        "report_date": {"type": "string", "format": "date"},
        "facility": {"type": ["string", "null"]},
        "patient_name_on_document": {"type": ["string", "null"]},
        "pdf_sha256": {"type": ["string", "null"]},
        "panels": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["results"],
                "properties": {
                    "name": {"type": ["string", "null"]},
                    "sample_datetime": {"type": ["string", "null"], "format": "date-time"},
                    "specimen": {"type": ["string", "null"], "enum": ["blood", "serum", "plasma", "urine", "other", None]},
                    "results": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["raw_name"],
                            "properties": {
                                "raw_name": {"type": "string"},
                                "raw_value": {"type": ["string", "null"]},
                                "raw_unit": {"type": ["string", "null"]},
                                "raw_reference": {"type": ["string", "null"]},
                                "source_flag": {"type": ["string", "null"], "enum": ["ok", "alert", None]},
                            },
                        },
                    },
                },
            },
        },
    },
}

_MAPPING_PROPS = {
    "report_id": {"type": "string"},
    "reason": {"type": "string", "description": "Düzeltmenin gerekçesi (denetim kaydına yazılır)."},
    "changes": {
        "type": "array",
        "items": {
            "type": "object",
            "required": ["result_id", "expected_current_test_key", "target_test_key"],
            "properties": {
                "result_id": {"type": "string"},
                "expected_current_test_key": {"type": ["string", "null"], "description": "Şu anki bağlantı; eşleşmemişse null."},
                "target_test_key": {"type": "string"},
            },
        },
    },
}

TOOLS = [
    {"name": "list_members", "description": "Erişilebilen aile üyelerini listeler (GET /members).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "preview_report", "description": "Raporu kaydetmeden önizler (POST /reports?dry_run=true). "
     "Dönen preview_token submit_report için gereklidir.",
     "inputSchema": {"type": "object", "required": ["report"], "properties": {
         "report": _REPORT_SCHEMA,
         "on_overlap": {"type": "string", "enum": ["error", "skip_existing"], "default": "error"}}}},
    {"name": "submit_report", "description": "Önizlenmiş raporu kaydeder (POST /reports). Yalnızca preview_report ile "
     "önizlenmiş ve aynı içeriğe sahip gövdeyi kabul eder.",
     "inputSchema": {"type": "object", "required": ["report", "preview_token"], "properties": {
         "report": _REPORT_SCHEMA, "preview_token": {"type": "string"},
         "on_overlap": {"type": "string", "enum": ["error", "skip_existing"], "default": "error"},
         "idempotency_key": {"type": "string"}}}},
    {"name": "attach_pdf", "description": "Orijinal PDF'i (base64) kayıtlı rapora ekler (POST /reports/{id}/pdf).",
     "inputSchema": {"type": "object", "required": ["report_id", "pdf_base64"], "properties": {
         "report_id": {"type": "string"}, "pdf_base64": {"type": "string"}, "filename": {"type": "string"}}}},
    {"name": "get_member_summary", "description": "Üyenin her testinin son değeri ve durumu (GET /members/{id}/summary).",
     "inputSchema": {"type": "object", "required": ["member_id"], "properties": {"member_id": {"type": "string"}}}},
    {"name": "get_test_history", "description": "Bir testin tüm ölçümleri (GET /members/{id}/tests/{key}/history).",
     "inputSchema": {"type": "object", "required": ["member_id", "test_key"], "properties": {
         "member_id": {"type": "string"}, "test_key": {"type": "string"}}}},
    {"name": "get_report", "description": "Rapor + paneller + sonuçlar; her sonucun id'si ve test_key'i ile (GET /reports/{id}).",
     "inputSchema": {"type": "object", "required": ["report_id"], "properties": {"report_id": {"type": "string"}}}},
    {"name": "preview_result_mappings", "description": "Bir rapordaki seçili sonuçların test bağlantısı düzeltmesini kaydetmeden "
     "önizler (POST /reports/{id}/result-mappings?dry_run=true). Genel alias kurallarına dokunmaz. Dönen preview_token "
     "apply_result_mappings için gereklidir.",
     "inputSchema": {"type": "object", "required": ["report_id", "reason", "changes"], "properties": _MAPPING_PROPS}},
    {"name": "apply_result_mappings", "description": "Önizlenmiş eşleştirme düzeltmesini tek işlemde uygular. Yalnızca "
     "preview_result_mappings ile önizlenmiş aynı gövdeyi kabul eder.",
     "inputSchema": {"type": "object", "required": ["report_id", "reason", "changes", "preview_token"], "properties": {
         **_MAPPING_PROPS, "preview_token": {"type": "string"}, "idempotency_key": {"type": "string"}}}},
    {"name": "list_unmapped", "description": "Kataloğa eşlenmemiş sonuçlar, ham ada göre gruplu; her grupta result_ids (GET /unmapped).",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "dismiss_results", "description": "Sonuç olmayan eşleşmemiş satırları gizler (POST /results/dismiss), ör. e-Nabız "
     "istem satırları ('Kan Sayımı Otomatik Hemogram (geniş panel) | Kan | : | 1 | tarih'). Kalıcı silmez, geri alınabilir. "
     "Önce dry_run=true ile listeyi kullanıcıya göster, onay alınca dry_run=false ile aynı isteği gönder. "
     "Ya result_ids ya da raw_name (+ specimen) ver. Bir teste bağlı sonuçlar gizlenemez.",
     "inputSchema": {"type": "object", "required": ["reason"], "properties": {
         "reason": {"type": "string"},
         "result_ids": {"type": "array", "items": {"type": "string"}},
         "raw_name": {"type": "string"},
         "specimen": {"type": ["string", "null"], "enum": ["blood", "serum", "plasma", "urine", "other", None]},
         "dry_run": {"type": "boolean", "default": True}}}},
    {"name": "restore_results", "description": "Gizlenmiş satırları geri getirir (POST /results/restore).",
     "inputSchema": {"type": "object", "required": ["result_ids"], "properties": {
         "result_ids": {"type": "array", "items": {"type": "string"}}}}},
    {"name": "list_reports", "description": "Üyenin raporları (GET /members/{id}/reports).",
     "inputSchema": {"type": "object", "required": ["member_id"], "properties": {
         "member_id": {"type": "string"}, "limit": {"type": "integer", "default": 50},
         "offset": {"type": "integer", "default": 0}}}},
]


def _parse_report(args: dict) -> ReportIn:
    try:
        return ReportIn.model_validate(args.get("report") or {})
    except ValidationError as e:
        raise ApiError(400, "VALIDATION_ERROR", "Rapor gövdesi hatalı.",
                       fields=[{"field": ".".join(str(x) for x in err["loc"]), "message": err["msg"]} for err in e.errors()])


def _validate(model, data: dict):
    try:
        return model.model_validate(data)
    except ValidationError as e:
        raise ApiError(400, "VALIDATION_ERROR", "Gövde hatalı.",
                       fields=[{"field": ".".join(str(x) for x in err["loc"]), "message": err["msg"]} for err in e.errors()])


def _call_tool(db: Session, actor: Actor, name: str, args: dict) -> dict:
    if name == "list_members":
        return {"items": ops.list_members(db, actor)}
    if name == "preview_report":
        body = _parse_report(args)
        on_overlap = args.get("on_overlap", "error")
        _, payload = ops.post_report(db, actor, body, True, on_overlap, None)
        payload["preview_token"] = make_preview_token(actor.id, ingest.body_hash(body) + on_overlap)
        return payload
    if name == "submit_report":
        body = _parse_report(args)
        on_overlap = args.get("on_overlap", "error")
        if not check_preview_token(str(args.get("preview_token", "")), actor.id, ingest.body_hash(body) + on_overlap):
            raise ApiError(400, "PREVIEW_REQUIRED", "Bu gövde önizlenmemiş ya da önizleme sonrası değiştirilmiş. Önce preview_report çağırın.")
        _, payload = ops.post_report(db, actor, body, False, on_overlap, args.get("idempotency_key"))
        return payload
    if name == "attach_pdf":
        try:
            data = base64.b64decode(args.get("pdf_base64", ""), validate=False)
        except ValueError:
            raise ApiError(400, "VALIDATION_ERROR", "pdf_base64 çözülemedi.")
        return ops.attach_pdf(db, actor, str(args.get("report_id")), data, args.get("filename"))
    if name == "get_member_summary":
        return ops.member_summary(db, actor, str(args.get("member_id")))
    if name == "get_test_history":
        return ops.test_history(db, actor, str(args.get("member_id")), str(args.get("test_key")))
    if name == "get_report":
        return ops.get_report(db, actor, str(args.get("report_id")))
    if name in ("preview_result_mappings", "apply_result_mappings"):
        try:
            body = ResultMappingsIn.model_validate({k: args.get(k) for k in ("reason", "changes")}
                                                   | ({"preview_token": args.get("preview_token")} if name == "apply_result_mappings" else {}))
        except ValidationError as e:
            raise ApiError(400, "VALIDATION_ERROR", "Gövde hatalı.",
                           fields=[{"field": ".".join(str(x) for x in err["loc"]), "message": err["msg"]} for err in e.errors()])
        if name == "apply_result_mappings" and not body.preview_token:
            raise ApiError(400, "PREVIEW_REQUIRED", "Önce preview_result_mappings çağırın.")
        _, payload = ops.remap_report_results(db, actor, str(args.get("report_id")), body,
                                              name == "preview_result_mappings", args.get("idempotency_key"))
        return payload
    if name == "list_unmapped":
        return {"items": ops.unmapped(db, actor)}
    if name == "dismiss_results":
        body = _validate(DismissIn, {k: args[k] for k in ("reason", "result_ids", "raw_name", "specimen") if k in args})
        return ops.dismiss_results(db, actor, body, bool(args.get("dry_run", True)))
    if name == "restore_results":
        return ops.restore_results(db, actor, _validate(RestoreResultsIn, {"result_ids": args.get("result_ids")}))
    if name == "list_reports":
        return ops.member_reports(db, actor, str(args.get("member_id")), int(args.get("limit", 50)), int(args.get("offset", 0)))
    raise KeyError(name)


def _rpc_result(id_, result):
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _rpc_error(id_, code, message):
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": translate(message)}}


def _handle(db: Session, actor: Actor, msg: dict) -> dict | None:
    if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
        return _rpc_error(msg.get("id") if isinstance(msg, dict) else None, -32600, "Invalid Request")
    method = msg.get("method")
    id_ = msg.get("id")
    params = msg.get("params") or {}
    if id_ is None:  # bildirim
        return None
    if method == "initialize":
        requested = params.get("protocolVersion")
        version = requested if requested in SUPPORTED_VERSIONS else SUPPORTED_VERSIONS[0]
        return _rpc_result(id_, {"protocolVersion": version, "capabilities": {"tools": {"listChanged": False}},
                                 "serverInfo": SERVER_INFO, "instructions": INSTRUCTIONS})
    if method == "ping":
        return _rpc_result(id_, {})
    if method == "tools/list":
        return _rpc_result(id_, {"tools": TOOLS})
    if method == "tools/call":
        name = params.get("name")
        args = params.get("arguments") or {}
        audit(db, actor, "mcp.call", "tool", str(name)[:64], None, commit=True)
        try:
            data = _call_tool(db, actor, name, args)
            return _rpc_result(id_, {"content": [{"type": "text", "text": json.dumps(data, ensure_ascii=False, default=str)}],
                                     "structuredContent": data, "isError": False})
        except KeyError:
            return _rpc_error(id_, -32602, f"Bilinmeyen araç: {name}")
        except ApiError as e:
            db.rollback()
            return _rpc_result(id_, {"content": [{"type": "text", "text": json.dumps(e.body(), ensure_ascii=False)}],
                                     "structuredContent": e.body(), "isError": True})
    if method in ("resources/list", "prompts/list"):
        return _rpc_result(id_, {"resources": []} if method == "resources/list" else {"prompts": []})
    return _rpc_error(id_, -32601, f"Method not found: {method}")


@router.post("/mcp")
async def mcp_post(request: Request, actor: Actor = Depends(get_api_actor), db: Session = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception:  # noqa: BLE001
        return JSONResponse(_rpc_error(None, -32700, "Parse error"), status_code=400)
    if isinstance(payload, list):
        out = [r for r in (_handle(db, actor, m) for m in payload) if r is not None]
        return JSONResponse(out) if out else Response(status_code=202)
    res = _handle(db, actor, payload)
    if res is None:
        return Response(status_code=202)
    return JSONResponse(res)


@router.get("/mcp")
async def mcp_get():
    return Response(status_code=405, headers={"Allow": "POST"})


@router.delete("/mcp")
async def mcp_delete():
    return Response(status_code=405, headers={"Allow": "POST"})
