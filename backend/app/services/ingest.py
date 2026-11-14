"""Rapor girişi: ayrıştırma, eşleme, işaretleme, mükerrer kontrolü (RIMETRA.md §7–9)."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from zoneinfo import ZoneInfo

from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import get_settings
from ..deps import Actor
from ..errors import ApiError
from ..models import Facility, Member, Panel, Report, Result
from ..parsing import (
    ParsedReference,
    apply_unit_rules,
    clean_text,
    compute_flag,
    flags_mismatch,
    names_match,
    normalize_facility,
    parse_result_row,
    value_signature,
)
from ..schemas import ReportIn
from ..security import canonical_json, sha256_hex
from .audit import audit
from ..i18n import translate
from .catalog import CatalogResolver


def local_tz() -> ZoneInfo:
    try:
        return ZoneInfo(get_settings().tz)
    except Exception:  # noqa: BLE001
        return ZoneInfo("Europe/Istanbul")


def aware(dt: datetime | None, fallback_date) -> datetime:
    if dt is None:
        return datetime.combine(fallback_date, time(0, 0), tzinfo=local_tz())
    if dt.tzinfo is None:
        return dt.replace(tzinfo=local_tz())
    return dt


@dataclass
class PreparedResult:
    panel_index: int
    position: int
    raw_name: str
    raw_value: str | None
    raw_unit: str | None
    raw_reference: str | None
    name: str
    alias_key: str
    specimen: str | None
    test_def: object | None
    value_numeric: float | None
    value_text: str | None
    value_qualifier: str | None
    unit_raw: str | None
    unit_canonical: str | None
    ref: ParsedReference
    flag_computed: str
    flag_source: str | None
    sample_datetime: datetime

    @property
    def mismatch(self) -> bool:
        return flags_mismatch(self.flag_computed, self.flag_source)

    def to_public(self) -> dict:
        td = self.test_def
        return {
            "raw_name": self.raw_name,
            "name": self.name,
            "test_key": td.key if td else None,
            "display_name": td.display_name if td else self.name,
            "specimen": self.specimen,
            "value_numeric": self.value_numeric,
            "value_text": self.value_text,
            "value_qualifier": self.value_qualifier,
            "unit": self.unit_canonical or self.unit_raw,
            "ref_low": self.ref.ref_low,
            "ref_high": self.ref.ref_high,
            "ref_text": self.ref.ref_text,
            "ref_note": self.ref.ref_note,
            "flag_computed": self.flag_computed,
            "flag_source": self.flag_source,
            "flag_mismatch": self.mismatch,
            "sample_datetime": self.sample_datetime.isoformat(),
        }


@dataclass
class PreparedPanel:
    name: str | None
    specimen: str | None
    sample_datetime: datetime


@dataclass
class Prepared:
    member: Member
    facility_raw: str | None
    facility_norm: str | None
    facility: Facility | None
    panels: list[PreparedPanel]
    results: list[PreparedResult]
    fingerprint: str
    warnings: list[dict] = field(default_factory=list)


def _warn(lst: list, code: str, message: str, raw_name: str | None = None) -> None:
    w = {"code": code, "message": translate(message)}
    if raw_name:
        w["raw_name"] = raw_name
    lst.append(w)


def prepare_report(db: Session, actor: Actor, body: ReportIn) -> Prepared:
    member = db.get(Member, body.member_id)
    if member is None:
        raise ApiError(400, "VALIDATION_ERROR", "Üye bulunamadı.", fields=[{"field": "member_id", "message": "Bilinmeyen üye"}])
    actor.require_member(member.id)

    if body.patient_name_on_document and not names_match(body.patient_name_on_document, member.display_name, member.full_name):
        raise ApiError(
            422, "NAME_MISMATCH",
            f"Belgedeki ad ('{body.patient_name_on_document}') seçilen üyeyle ('{member.display_name}') uyuşmuyor.",
            member_display_name=member.display_name,
        )

    warnings: list[dict] = []
    if not body.patient_name_on_document and body.source != "manual":
        _warn(warnings, "NO_PATIENT_NAME", "Belgedeki hasta adı gönderilmedi; isim kontrolü yapılamadı.")

    facility_raw = clean_text(body.facility) or None
    facility_norm = normalize_facility(facility_raw) if facility_raw else None
    facility = db.scalar(select(Facility).where(Facility.name_normalized == facility_norm)) if facility_norm else None

    resolver = CatalogResolver(db)
    panels: list[PreparedPanel] = []
    results: list[PreparedResult] = []
    seen: set[tuple[str, datetime]] = set()

    for pi, p in enumerate(body.panels):
        sdt = aware(p.sample_datetime, body.report_date)
        panels.append(PreparedPanel(name=clean_text(p.name) or None, specimen=p.specimen, sample_datetime=sdt))
        for ri, r in enumerate(p.results):
            pr = parse_result_row(r.raw_name, r.raw_value, r.raw_unit, r.raw_reference, r.source_flag)
            if pr.value.skip:
                _warn(warnings, "SKIPPED_PLACEHOLDER", "Değer '.' (yer tutucu) olduğu için satır atlandı.", pr.raw_name)
                continue
            td = resolver.resolve(pr.alias_key, p.specimen, pr.value)
            if td is None and r.test_key:
                hint = resolver.by_key(r.test_key)
                if hint is not None:
                    td = hint
                    _warn(warnings, "MAPPED_BY_HINT", f"Ajanın önerdiği '{r.test_key}' anahtarıyla eşlendi.", pr.raw_name)
            if td is not None and (td.id, sdt) in seen:
                _warn(warnings, "DUPLICATE_IN_REPORT",
                      f"Aynı test ({td.key}) aynı numune zamanında raporda iki kez geçiyor; ikincisi eşlenmedi.", pr.raw_name)
                td = None
            if td is not None:
                seen.add((td.id, sdt))

            rules = td.unit_rules if td else None
            ref = pr.reference
            if rules:
                ref = ParsedReference(
                    ref_low=apply_unit_rules(ref.ref_low, rules), ref_high=apply_unit_rules(ref.ref_high, rules),
                    ref_low_exclusive=ref.ref_low_exclusive, ref_high_exclusive=ref.ref_high_exclusive,
                    ref_text=ref.ref_text, ref_note=ref.ref_note,
                )
            val = pr.value
            if rules and val.value_numeric is not None:
                val.value_numeric = apply_unit_rules(val.value_numeric, rules)
            flag = compute_flag(val, ref)
            prepared = PreparedResult(
                panel_index=pi, position=ri, raw_name=pr.raw_name, raw_value=r.raw_value, raw_unit=r.raw_unit,
                raw_reference=r.raw_reference, name=pr.name, alias_key=pr.alias_key, specimen=p.specimen,
                test_def=td, value_numeric=val.value_numeric, value_text=val.value_text,
                value_qualifier=val.value_qualifier, unit_raw=pr.unit_raw,
                unit_canonical=(td.canonical_unit if td and td.canonical_unit else pr.unit_raw),
                ref=ref, flag_computed=flag, flag_source=pr.flag_source, sample_datetime=sdt,
            )
            if td is None:
                _warn(warnings, "UNMAPPED", "Test kataloğa eşlenemedi; 'Eşleşmemiş testler' ekranında bağlanabilir.", pr.raw_name)
            if prepared.mismatch:
                _warn(warnings, "FLAG_MISMATCH",
                      f"Belgedeki işaret ({pr.flag_source}) ile hesaplanan işaret ({flag}) uyuşmuyor.", pr.raw_name)
            results.append(prepared)

    if not results:
        raise ApiError(400, "VALIDATION_ERROR", "Raporda kaydedilecek sonuç yok.", fields=[{"field": "panels", "message": "Boş"}])

    fingerprint = compute_fingerprint(member.id, facility_norm, panels, results)
    return Prepared(member=member, facility_raw=facility_raw, facility_norm=facility_norm, facility=facility,
                    panels=panels, results=results, fingerprint=fingerprint, warnings=warnings)


def compute_fingerprint(member_id: str, facility_norm: str | None, panels: list[PreparedPanel],
                        results: list[PreparedResult]) -> str:
    """İçerik parmak izi: üye + kurum + her panel için (numune zamanı + sıralı [numune|ad, değer]).

    Ad olarak katalog anahtarı yerine normalize ham ad kullanılır; böylece katalog sonradan
    değişse bile aynı rapor aynı parmak izini üretir.
    """
    by_panel: dict[int, list[str]] = {}
    for r in results:
        by_panel.setdefault(r.panel_index, []).append(f"{r.specimen or ''}|{r.alias_key}|{value_signature_from(r)}")
    blocks = []
    for i, p in enumerate(panels):
        rows = sorted(by_panel.get(i, []))
        if rows:
            blocks.append({"t": p.sample_datetime.astimezone(local_tz()).strftime("%Y-%m-%dT%H:%M"), "r": rows})
    blocks.sort(key=lambda b: (b["t"], b["r"]))
    return sha256_hex(canonical_json({"m": member_id, "f": facility_norm or "", "p": blocks}))


def value_signature_from(r: PreparedResult) -> str:
    from ..parsing import ParsedValue
    return value_signature(ParsedValue(value_numeric=r.value_numeric, value_text=r.value_text, value_qualifier=r.value_qualifier))


def summarize(prep: Prepared) -> dict:
    out = sum(1 for r in prep.results if r.flag_computed in ("low", "high", "abnormal"))
    return {
        "results_total": len(prep.results),
        "out_of_range": out,
        "unmapped": sum(1 for r in prep.results if r.test_def is None),
        "flag_mismatches": sum(1 for r in prep.results if r.mismatch),
        "skipped": sum(1 for w in prep.warnings if w["code"] == "SKIPPED_PLACEHOLDER"),
    }


def find_duplicate(db: Session, prep: Prepared) -> Report | None:
    return db.scalar(select(Report).where(
        Report.member_id == prep.member.id, Report.content_fingerprint == prep.fingerprint, Report.deleted_at.is_(None)
    ))


def find_overlaps(db: Session, prep: Prepared) -> list[tuple[PreparedResult, Result]]:
    mapped = [r for r in prep.results if r.test_def is not None]
    if not mapped:
        return []
    fac_id = prep.facility.id if prep.facility else None
    conds = [and_(Result.test_definition_id == r.test_def.id, Result.sample_datetime == r.sample_datetime) for r in mapped]
    q = select(Result).where(
        Result.member_id == prep.member.id, Result.deleted_at.is_(None),
        (Result.facility_id == fac_id) if fac_id else Result.facility_id.is_(None),
        or_(*conds),
    )
    existing = {(e.test_definition_id, e.sample_datetime): e for e in db.scalars(q)}
    out = []
    for r in mapped:
        e = existing.get((r.test_def.id, r.sample_datetime))
        if e is not None:
            out.append((r, e))
    return out


def submit_report(db: Session, actor: Actor, body: ReportIn, dry_run: bool, on_overlap: str = "error",
                  pdf_sha256: str | None = None) -> tuple[int, dict]:
    prep = prepare_report(db, actor, body)

    dup = find_duplicate(db, prep)
    if dup is not None:
        raise ApiError(409, "DUPLICATE_REPORT", "Bu rapor zaten kayıtlı.", existing_report_id=dup.id)

    overlaps = find_overlaps(db, prep)
    if overlaps:
        if on_overlap == "skip_existing":
            skip_ids = {id(r) for r, _ in overlaps}
            for r, e in overlaps:
                _warn(prep.warnings, "SKIPPED_EXISTING", f"Bu sonuç zaten {e.report_id} raporunda var; atlandı.", r.raw_name)
            prep.results = [r for r in prep.results if id(r) not in skip_ids]
            if not any(r.test_def is not None for r in prep.results):
                raise ApiError(409, "OVERLAPPING_RESULTS", "Raporda eklenecek yeni sonuç kalmadı.",
                               conflicts=[_conflict(r, e) for r, e in overlaps])
        else:
            raise ApiError(409, "OVERLAPPING_RESULTS", "Bazı sonuçlar başka bir raporda zaten kayıtlı.",
                           conflicts=[_conflict(r, e) for r, e in overlaps])

    payload = {
        "report_id": None,
        "dry_run": dry_run,
        "member_id": prep.member.id,
        "fingerprint": prep.fingerprint,
        "summary": summarize(prep),
        "results": [r.to_public() for r in prep.results],
        "warnings": prep.warnings,
    }
    if dry_run:
        return 200, payload

    try:
        report = persist(db, actor, body, prep, pdf_sha256)
        audit(db, actor, "report.create", "report", report.id,
              {"member_id": prep.member.id, "summary": payload["summary"], "source": body.source})
        db.commit()
    except IntegrityError:
        db.rollback()
        dup = find_duplicate(db, prep)
        if dup is not None:
            raise ApiError(409, "DUPLICATE_REPORT", "Bu rapor zaten kayıtlı.", existing_report_id=dup.id)
        raise ApiError(409, "OVERLAPPING_RESULTS", "Bazı sonuçlar eş zamanlı olarak başka raporda kaydedildi.", conflicts=[])
    payload["report_id"] = report.id
    from .telegram import notify_new_report
    notify_new_report(report.id, actor.id if actor.kind == "user" else None)
    return 201, payload


def _conflict(r: PreparedResult, e: Result) -> dict:
    return {
        "raw_name": r.raw_name,
        "test_key": r.test_def.key if r.test_def else None,
        "sample_datetime": r.sample_datetime.isoformat(),
        "existing_report_id": e.report_id,
        "existing_result_id": e.id,
    }


def persist(db: Session, actor: Actor, body: ReportIn, prep: Prepared, pdf_sha256: str | None = None) -> Report:
    facility = prep.facility
    if facility is None and prep.facility_norm:
        facility = Facility(name_normalized=prep.facility_norm, name_raw=prep.facility_raw)
        db.add(facility)
        db.flush()
    report = Report(
        member_id=prep.member.id,
        facility_id=facility.id if facility else None,
        report_date=body.report_date,
        source=body.source,
        content_fingerprint=prep.fingerprint,
        pdf_sha256=pdf_sha256,
        created_via_api_key_id=actor.id if actor.kind == "api_key" else None,
        created_via_user_id=actor.id if actor.kind == "user" else None,
    )
    db.add(report)
    db.flush()
    panel_objs: dict[int, Panel] = {}
    used_panels = sorted({r.panel_index for r in prep.results})
    for pos, pi in enumerate(used_panels):
        pp = prep.panels[pi]
        pnl = Panel(report_id=report.id, name=pp.name, specimen=pp.specimen, sample_datetime=pp.sample_datetime, position=pos)
        db.add(pnl)
        panel_objs[pi] = pnl
    db.flush()
    for r in prep.results:
        db.add(Result(
            panel_id=panel_objs[r.panel_index].id, report_id=report.id, member_id=prep.member.id,
            facility_id=facility.id if facility else None,
            test_definition_id=r.test_def.id if r.test_def else None, specimen=r.specimen, position=r.position,
            raw_name=r.raw_name, raw_value=r.raw_value, raw_unit=r.raw_unit, raw_reference=r.raw_reference,
            value_numeric=r.value_numeric, value_text=r.value_text, value_qualifier=r.value_qualifier,
            unit_raw=r.unit_raw, unit_canonical=r.unit_canonical,
            ref_low=r.ref.ref_low, ref_high=r.ref.ref_high, ref_low_exclusive=r.ref.ref_low_exclusive,
            ref_high_exclusive=r.ref.ref_high_exclusive, ref_text=r.ref.ref_text, ref_note=r.ref.ref_note,
            flag_computed=r.flag_computed, flag_source=r.flag_source, sample_datetime=r.sample_datetime,
        ))
    db.flush()
    return report


def body_hash(body: ReportIn) -> str:
    return sha256_hex(canonical_json(body.model_dump(mode="json")))
