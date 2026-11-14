from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Specimen = Literal["blood", "serum", "plasma", "urine", "other"]


class ResultIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    raw_name: str = Field(min_length=1, max_length=300)
    raw_value: str | None = Field(default=None, max_length=2000)
    raw_unit: str | None = Field(default=None, max_length=60)
    raw_reference: str | None = Field(default=None, max_length=2000)
    source_flag: str | None = None
    # Ajanın isteğe bağlı ipucu; karar sunucunundur
    test_key: str | None = None


class PanelIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    name: str | None = Field(default=None, max_length=300)
    sample_datetime: datetime | None = None
    specimen: Specimen | None = None
    results: list[ResultIn] = Field(min_length=1)


class ReportIn(BaseModel):
    model_config = ConfigDict(extra="ignore")
    member_id: str
    source: str = Field(default="enabiz", max_length=20)
    report_date: date
    facility: str | None = Field(default=None, max_length=300)
    patient_name_on_document: str | None = Field(default=None, max_length=200)
    # İsteğe bağlı: orijinal PDF'in SHA-256'sı. Aynı dosya tekrar gelirse anında yakalanır.
    pdf_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    panels: list[PanelIn] = Field(min_length=1)


class MemberIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)
    full_name: str | None = Field(default=None, max_length=200)
    sex: Literal["M", "F"] | None = None
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    avatar_color: str | None = Field(default=None, max_length=20)


class MemberPatch(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    full_name: str | None = Field(default=None, max_length=200)
    sex: Literal["M", "F"] | None = None
    birth_year: int | None = Field(default=None, ge=1900, le=2100)
    avatar_color: str | None = Field(default=None, max_length=20)
    sort_order: int | None = None


class AliasIn(BaseModel):
    raw_name: str = Field(min_length=1, max_length=300)
    specimen: Specimen
    test_key: str


class TestDefIn(BaseModel):
    key: str = Field(min_length=3, max_length=80, pattern=r"^[a-z0-9_]+\.[a-z0-9_]+$")
    display_name: str = Field(min_length=1, max_length=200)
    specimen: Specimen
    category: str = Field(min_length=1, max_length=60)
    canonical_unit: str | None = Field(default=None, max_length=40)
    value_type: Literal["numeric", "qualitative", "text"] = "numeric"
    unit_rules: list[dict] | None = None
    info_what: str | None = Field(default=None, max_length=4000)
    info_low: str | None = Field(default=None, max_length=4000)
    info_high: str | None = Field(default=None, max_length=4000)


class NoteIn(BaseModel):
    date: date
    text: str = Field(min_length=1, max_length=2000)
    test_key: str | None = None


class ReminderIn(BaseModel):
    test_key: str
    interval_months: int = Field(ge=1, le=120)
    note: str | None = Field(default=None, max_length=300)


class ManualEntryItem(BaseModel):
    test_key: str
    value: str = Field(min_length=1, max_length=200)
    unit: str | None = None
    reference: str | None = None


class ManualEntryIn(BaseModel):
    date: date
    time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    note: str | None = Field(default=None, max_length=300)
    items: list[ManualEntryItem] = Field(min_length=1)


class ApiKeyIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: list[str] = Field(min_length=1)
    member_scope: list[str] | None = None


class UserIn(BaseModel):
    username: str = Field(min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.\-]+$")
    password: str = Field(min_length=8, max_length=200)
    member_id: str | None = None
    role: Literal["master", "member"] = "member"
    read_only: bool = False


class UserPatch(BaseModel):
    password: str | None = Field(default=None, min_length=8, max_length=200)
    is_active: bool | None = None
    read_only: bool | None = None
    member_id: str | None = None
    # Telegram sohbet kimliği (bota yazınca bot söyler). null = bağlantıyı kaldır.
    telegram_chat_id: int | None = Field(default=None, ge=1, le=10**15)


class LoginIn(BaseModel):
    username: str
    password: str


class PasswordChangeIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=200)


class ResultMappingChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result_id: str = Field(min_length=1, max_length=32)
    # Sonucun şu anki test anahtarı (eşleşmemişse null). Arada değişmişse işlem durur.
    expected_current_test_key: str | None
    target_test_key: str = Field(min_length=1, max_length=80)


class ResultMappingsIn(BaseModel):
    """Bir rapordaki seçili sonuçların test bağlantısını düzeltir (genel alias'a dokunmaz)."""
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=3, max_length=1000)
    changes: list[ResultMappingChange] = Field(min_length=1, max_length=200)
    # İsteğe bağlı: dry_run yanıtındaki jeton. Verilirse gövde önizlenenle aynı olmalı.
    preview_token: str | None = Field(default=None, max_length=200)


class DismissIn(BaseModel):
    """Sonuç olmayan eşleşmemiş satırları gizler. Ya result_ids ya da raw_name (+ specimen) verilir."""
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(default="Sonuç değil", min_length=3, max_length=1000)
    result_ids: list[str] | None = Field(default=None, min_length=1, max_length=500)
    raw_name: str | None = Field(default=None, min_length=1, max_length=300)
    specimen: Specimen | None = None


class RestoreResultsIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    result_ids: list[str] = Field(min_length=1, max_length=500)
