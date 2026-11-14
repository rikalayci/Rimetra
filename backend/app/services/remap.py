"""Rapor bazında sonuç eşleştirmesi düzeltme.

Genel alias kurallarına dokunmadan, tek bir rapordaki seçili sonuçların hangi standart teste
bağlı olduğunu değiştirir. Ham veriler (raw_*, işaret, numune zamanı, panel/rapor, PDF) korunur;
yalnızca test bağlantısı ve buna bağlı gösterim alanları (değer/ referans/ birim/ işaret) ham
veriden yeniden hesaplanır. Yüzde ↔ sayım gibi değer dönüşümü yapılmaz.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..deps import Actor
from ..errors import ApiError
from ..models import Report, Result, TestDefinition
from ..parsing import clean_text, parse_value
from ..schemas import ResultMappingsIn
from ..security import canonical_json, check_preview_token, make_preview_token, sha256_hex
from . import idempotency
from .audit import audit
from .catalog import specimen_group
from .mutations import recompute_result


def request_hash(report_id: str, body: ResultMappingsIn) -> str:
    data = body.model_dump(mode="json", exclude={"preview_token"})
    return sha256_hex(canonical_json({"report_id": report_id, **data}))


def _is_percent(unit: str | None) -> bool:
    return bool(unit) and "%" in unit


def _incompatibility(r: Result, td: TestDefinition) -> str | None:
    """Hedef test bu satır için uygun değilse nedenini döndürür."""
    if r.specimen and td.specimen not in specimen_group(r.specimen):
        return f"Numune uyuşmuyor: sonuç '{r.specimen}', test '{td.specimen}'."
    raw_unit = clean_text(r.raw_unit) or None
    if raw_unit and td.canonical_unit and _is_percent(raw_unit) != _is_percent(td.canonical_unit):
        return f"Ölçüm biçimi uyuşmuyor: satırın birimi '{raw_unit}', testin birimi '{td.canonical_unit}'."
    if td.value_type == "numeric":
        val = parse_value(r.raw_value)
        if not val.skip and val.value_numeric is None:
            return "Hedef test sayısal, ancak satırın değeri sayısal değil."
    return None


def _same_slot(a: Result, b: Result) -> bool:
    return a.member_id == b.member_id and a.sample_datetime == b.sample_datetime and a.facility_id == b.facility_id


def remap_results(db: Session, actor: Actor, report: Report, body: ResultMappingsIn, dry_run: bool,
                  idem_key: str | None) -> tuple[int, dict]:
    rhash = request_hash(report.id, body)
    scope = f"{actor.kind}:{actor.id}"
    if not dry_run:
        prev = idempotency.lookup(db, scope, idem_key, rhash)
        if prev is not None:
            return prev
        if body.preview_token and not check_preview_token(body.preview_token, actor.id, rhash):
            raise ApiError(400, "PREVIEW_MISMATCH",
                           "Önizleme jetonu bu gövdeye ait değil ya da süresi dolmuş. Önce dry_run=true ile yeniden önizleyin.")

    ids = [c.result_id for c in body.changes]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise ApiError(400, "VALIDATION_ERROR", "Aynı sonuç birden fazla kez gönderilmiş.",
                       fields=[{"field": "changes", "message": f"Tekrarlanan result_id: {', '.join(dupes)}"}])

    # Satırları kilitle: eşzamanlı başka bir düzeltme araya giremesin
    rows = {r.id: r for r in db.scalars(select(Result).where(Result.id.in_(ids)).with_for_update())}

    foreign = [i for i in ids if i not in rows or rows[i].report_id != report.id]
    if foreign:
        raise ApiError(422, "RESULT_NOT_IN_REPORT", "Bazı sonuçlar bu rapora ait değil ya da bulunamadı.",
                       report_id=report.id, result_ids=foreign)
    inactive = [i for i in ids if rows[i].deleted_at is not None]
    if inactive:
        raise ApiError(409, "RESULT_INACTIVE", "Bazı sonuçlar silinmiş.", result_ids=inactive)

    keys = {c.target_test_key for c in body.changes} | {c.expected_current_test_key for c in body.changes if c.expected_current_test_key}
    tds_by_key = {t.key: t for t in db.scalars(select(TestDefinition).where(TestDefinition.key.in_(keys)))}
    tds_by_id = {t.id: t for t in tds_by_key.values()}
    current_ids = {r.test_definition_id for r in rows.values() if r.test_definition_id and r.test_definition_id not in tds_by_id}
    if current_ids:
        for t in db.scalars(select(TestDefinition).where(TestDefinition.id.in_(current_ids))):
            tds_by_id[t.id] = t

    unknown = sorted({c.target_test_key for c in body.changes if c.target_test_key not in tds_by_key})
    if unknown:
        raise ApiError(400, "UNKNOWN_TEST_KEY", "Hedef test katalogda yok.", test_keys=unknown)

    stale = []
    for c in body.changes:
        r = rows[c.result_id]
        actual = tds_by_id[r.test_definition_id].key if r.test_definition_id else None
        if actual != c.expected_current_test_key:
            stale.append({"result_id": r.id, "raw_name": r.raw_name, "expected_current_test_key": c.expected_current_test_key,
                          "actual_current_test_key": actual})
    if stale:
        raise ApiError(409, "MAPPING_CHANGED", "Bazı sonuçların bağlantısı beklenenden farklı; araya başka bir değişiklik girmiş olabilir.",
                       mismatches=stale)

    bad = []
    for c in body.changes:
        if c.expected_current_test_key == c.target_test_key:
            continue  # değişmeyen satır: mevcut bağlantıya dokunulmaz
        reason = _incompatibility(rows[c.result_id], tds_by_key[c.target_test_key])
        if reason:
            bad.append({"result_id": c.result_id, "raw_name": rows[c.result_id].raw_name,
                        "target_test_key": c.target_test_key, "message": reason})
    if bad:
        raise ApiError(422, "INCOMPATIBLE_TEST", "Hedef test bazı satırlar için uygun değil.", problems=bad)

    # ---- Nihai duruma göre çakışma kontrolü
    final = {c.result_id: tds_by_key[c.target_test_key] for c in body.changes}
    conflicts: list[dict] = []
    seen: dict[tuple, Result] = {}
    for rid, td in final.items():
        r = rows[rid]
        slot = (td.id, r.member_id, r.sample_datetime, r.facility_id)
        if slot in seen:
            conflicts.append({"result_id": rid, "raw_name": r.raw_name, "target_test_key": td.key,
                              "conflicting_result_id": seen[slot].id, "conflicting_report_id": report.id,
                              "message": "Aynı istekte iki satır aynı teste ve numune zamanına bağlanıyor."})
        else:
            seen[slot] = r
    target_ids = {td.id for td in final.values()}
    members = {r.member_id for r in rows.values()}
    others = db.scalars(select(Result).where(
        Result.test_definition_id.in_(target_ids), Result.member_id.in_(members),
        Result.deleted_at.is_(None), Result.id.not_in(ids),
    )).all()
    for rid, td in final.items():
        r = rows[rid]
        for o in others:
            if o.test_definition_id == td.id and _same_slot(o, r):
                conflicts.append({"result_id": rid, "raw_name": r.raw_name, "target_test_key": td.key,
                                  "conflicting_result_id": o.id, "conflicting_report_id": o.report_id,
                                  "message": "Aynı kişi, test, numune zamanı ve kurum için başka bir kayıt var."})

    def describe(r: Result) -> dict:
        return {"value_numeric": r.value_numeric, "value_text": r.value_text, "unit": r.unit_canonical or r.unit_raw,
                "ref_low": r.ref_low, "ref_high": r.ref_high, "flag_computed": r.flag_computed}

    items = []
    for c in body.changes:
        r = rows[c.result_id]
        items.append({
            "result_id": r.id, "raw_name": r.raw_name, "raw_value": r.raw_value, "raw_unit": r.raw_unit,
            "from_test_key": c.expected_current_test_key, "to_test_key": c.target_test_key,
            "changed": c.expected_current_test_key != c.target_test_key, "before": describe(r),
        })
    changed_count = sum(1 for i in items if i["changed"])

    if conflicts:
        if dry_run:
            db.rollback()
            return 200, {"report_id": report.id, "dry_run": True, "ok": False, "changed_count": changed_count,
                         "changes": items, "conflicts": conflicts}
        db.rollback()
        raise ApiError(409, "MAPPING_CONFLICT", "Değişiklik sonrası durumda başka kayıtlarla çakışma var.", conflicts=conflicts)

    # ---- Uygula: önce bağlantıları boşalt, sonra yenilerini yaz (benzersiz indekse takılmamak için)
    to_change = [c for c in body.changes if c.expected_current_test_key != c.target_test_key]
    for c in to_change:
        rows[c.result_id].test_definition_id = None
    db.flush()
    for c in to_change:
        r, td = rows[c.result_id], tds_by_key[c.target_test_key]
        r.test_definition_id = td.id
        recompute_result(r, td)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ApiError(409, "MAPPING_CONFLICT", "Değişiklik eşzamanlı başka bir kayıtla çakıştı; yeniden önizleyin.", conflicts=[])
    for item in items:
        item["after"] = describe(rows[item["result_id"]])

    payload = {"report_id": report.id, "dry_run": dry_run, "ok": True, "changed_count": changed_count,
               "changes": items, "conflicts": []}
    if dry_run:
        db.rollback()
        payload["preview_token"] = make_preview_token(actor.id, rhash)
        return 200, payload

    for c in to_change:
        r = rows[c.result_id]
        audit(db, actor, "result.remap", "result", r.id, {
            "report_id": report.id, "raw_name": r.raw_name, "from": c.expected_current_test_key,
            "to": c.target_test_key, "reason": body.reason})
    audit(db, actor, "report.remap_results", "report", report.id,
          {"reason": body.reason, "changed": changed_count,
           "changes": [{"result_id": c.result_id, "from": c.expected_current_test_key, "to": c.target_test_key} for c in to_change]})
    db.commit()
    idempotency.store(db, scope, idem_key, rhash, 200, payload)
    return 200, payload
