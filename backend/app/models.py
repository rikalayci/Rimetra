from __future__ import annotations

import secrets
from datetime import date, datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"


def new_id(prefix: str) -> str:
    return f"{prefix}_" + "".join(secrets.choice(_ALPHABET) for _ in range(12))


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Member(Base):
    __tablename__ = "members"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("mbr"))
    display_name: Mapped[str] = mapped_column(String(100))
    # Belgedeki ad-soyad (isim uyuşmazlığı kontrolü için). TC kimlik no ASLA tutulmaz.
    full_name: Mapped[str | None] = mapped_column(String(200))
    sex: Mapped[str | None] = mapped_column(String(1))  # M | F
    birth_year: Mapped[int | None] = mapped_column(Integer)
    avatar_color: Mapped[str | None] = mapped_column(String(20))
    avatar_path: Mapped[str | None] = mapped_column(String(300))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped[User | None] = relationship(back_populates="member", uselist=False)


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("usr"))
    member_id: Mapped[str | None] = mapped_column(
        ForeignKey("members.id", ondelete="SET NULL"), unique=True
    )
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(10))  # master | member
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    read_only: Mapped[bool] = mapped_column(Boolean, default=False)
    theme: Mapped[str | None] = mapped_column(String(10))
    lang: Mapped[str | None] = mapped_column(String(5))  # tr | en (boş: tarayıcı dili)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Telegram bağlantısı: bu sohbet kimliğinden gelen mesajlar bu kullanıcı adına (onun yetkileriyle) yanıtlanır.
    telegram_chat_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    telegram_username: Mapped[str | None] = mapped_column(String(64))
    telegram_linked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    telegram_notify: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    # Botta en son bakılan kişi (bir sonraki mesajda hatırlamak için)
    telegram_member_id: Mapped[str | None] = mapped_column(String(32))

    member: Mapped[Member | None] = relationship(back_populates="user")


class TelegramLinkCode(Base):
    """Web arayüzünden üretilen tek kullanımlık bağlama kodu (t.me/<bot>?start=<kod>)."""
    __tablename__ = "telegram_link_codes"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256(kod)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class UserSession(Base):
    __tablename__ = "sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # sha256(token)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))


class ApiKey(Base):
    __tablename__ = "api_keys"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("key"))
    name: Mapped[str] = mapped_column(String(100))
    key_prefix: Mapped[str] = mapped_column(String(16), unique=True)
    key_hash: Mapped[str] = mapped_column(String(255))
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String(32)), default=list)
    member_scope: Mapped[list[str] | None] = mapped_column(ARRAY(String(32)))
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Facility(Base):
    __tablename__ = "facilities"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("fac"))
    name_normalized: Mapped[str] = mapped_column(String(300), unique=True)
    name_raw: Mapped[str] = mapped_column(String(300))


class Report(Base):
    __tablename__ = "reports"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("rpt"))
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    facility_id: Mapped[str | None] = mapped_column(ForeignKey("facilities.id"))
    report_date: Mapped[date] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(20), default="enabiz")
    content_fingerprint: Mapped[str] = mapped_column(String(64))
    pdf_path: Mapped[str | None] = mapped_column(String(300))
    pdf_sha256: Mapped[str | None] = mapped_column(String(64), index=True)
    pdf_original_name: Mapped[str | None] = mapped_column(String(300))
    created_via_api_key_id: Mapped[str | None] = mapped_column(
        ForeignKey("api_keys.id", ondelete="SET NULL")
    )
    created_via_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    facility: Mapped[Facility | None] = relationship()
    panels: Mapped[list[Panel]] = relationship(
        back_populates="report", cascade="all, delete-orphan", order_by="Panel.position"
    )

    __table_args__ = (
        Index(
            "uq_reports_member_fingerprint",
            "member_id",
            "content_fingerprint",
            unique=True,
            postgresql_where=text("deleted_at IS NULL"),
        ),
    )


class Panel(Base):
    __tablename__ = "panels"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("pnl"))
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), index=True)
    name: Mapped[str | None] = mapped_column(String(300))
    specimen: Mapped[str | None] = mapped_column(String(20))
    sample_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    position: Mapped[int] = mapped_column(Integer, default=0)

    report: Mapped[Report] = relationship(back_populates="panels")
    results: Mapped[list[Result]] = relationship(
        back_populates="panel", cascade="all, delete-orphan", order_by="Result.position"
    )


class TestDefinition(Base):
    __tablename__ = "test_definitions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("tst"))
    key: Mapped[str] = mapped_column(String(80), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    specimen: Mapped[str] = mapped_column(String(20))  # blood | urine | serum | other
    category: Mapped[str] = mapped_column(String(60))
    canonical_unit: Mapped[str | None] = mapped_column(String(40))
    value_type: Mapped[str] = mapped_column(String(12), default="numeric")
    # Ölçek kuralları: [{"if_gt": 100, "factor": 0.001}]
    unit_rules: Mapped[list | None] = mapped_column(JSONB)
    sort_order: Mapped[int] = mapped_column(Integer, default=1000)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False)
    # Herkesin anlayacağı dilde açıklamalar (genel bilgi, teşhis değildir).
    info_what: Mapped[str | None] = mapped_column(Text)
    info_low: Mapped[str | None] = mapped_column(Text)
    info_high: Mapped[str | None] = mapped_column(Text)

    aliases: Mapped[list[TestAlias]] = relationship(
        back_populates="test_definition", cascade="all, delete-orphan"
    )


class TestAlias(Base):
    __tablename__ = "test_aliases"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("als"))
    test_definition_id: Mapped[str] = mapped_column(
        ForeignKey("test_definitions.id", ondelete="CASCADE"), index=True
    )
    alias_normalized: Mapped[str] = mapped_column(String(200))
    specimen: Mapped[str] = mapped_column(String(20))

    test_definition: Mapped[TestDefinition] = relationship(back_populates="aliases")
    __table_args__ = (UniqueConstraint("alias_normalized", "specimen", name="uq_alias_specimen"),)


class Result(Base):
    __tablename__ = "results"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("res"))
    panel_id: Mapped[str] = mapped_column(ForeignKey("panels.id", ondelete="CASCADE"), index=True)
    report_id: Mapped[str] = mapped_column(ForeignKey("reports.id", ondelete="CASCADE"), index=True)
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    facility_id: Mapped[str | None] = mapped_column(ForeignKey("facilities.id"))
    test_definition_id: Mapped[str | None] = mapped_column(
        ForeignKey("test_definitions.id", ondelete="SET NULL"), index=True
    )
    specimen: Mapped[str | None] = mapped_column(String(20))
    position: Mapped[int] = mapped_column(Integer, default=0)

    raw_name: Mapped[str] = mapped_column(String(300))
    raw_value: Mapped[str | None] = mapped_column(Text)
    raw_unit: Mapped[str | None] = mapped_column(String(60))
    raw_reference: Mapped[str | None] = mapped_column(Text)

    value_numeric: Mapped[float | None] = mapped_column(Float)
    value_text: Mapped[str | None] = mapped_column(String(300))
    value_qualifier: Mapped[str | None] = mapped_column(String(2))
    unit_raw: Mapped[str | None] = mapped_column(String(60))
    unit_canonical: Mapped[str | None] = mapped_column(String(40))
    ref_low: Mapped[float | None] = mapped_column(Float)
    ref_high: Mapped[float | None] = mapped_column(Float)
    ref_low_exclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    ref_high_exclusive: Mapped[bool] = mapped_column(Boolean, default=False)
    ref_text: Mapped[str | None] = mapped_column(String(200))
    ref_note: Mapped[str | None] = mapped_column(Text)
    flag_computed: Mapped[str] = mapped_column(String(10), default="unknown")
    flag_source: Mapped[str | None] = mapped_column(String(10))
    sample_datetime: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    panel: Mapped[Panel] = relationship(back_populates="results")
    test_definition: Mapped[TestDefinition | None] = relationship()

    __table_args__ = (
        Index(
            "uq_results_member_test_time_facility",
            "member_id",
            "test_definition_id",
            "sample_datetime",
            "facility_id",
            unique=True,
            postgresql_where=text("test_definition_id IS NOT NULL AND deleted_at IS NULL"),
            postgresql_nulls_not_distinct=True,
        ),
    )


class Note(Base):
    __tablename__ = "notes"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("not"))
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    date: Mapped[date] = mapped_column(Date)
    text: Mapped[str] = mapped_column(Text)
    test_definition_id: Mapped[str | None] = mapped_column(
        ForeignKey("test_definitions.id", ondelete="SET NULL")
    )
    created_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Reminder(Base):
    __tablename__ = "reminders"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=lambda: new_id("rem"))
    member_id: Mapped[str] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), index=True)
    test_definition_id: Mapped[str] = mapped_column(
        ForeignKey("test_definitions.id", ondelete="CASCADE")
    )
    interval_months: Mapped[int] = mapped_column(Integer)
    note: Mapped[str | None] = mapped_column(String(300))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    actor_type: Mapped[str] = mapped_column(String(10))  # user | api_key | system
    actor_id: Mapped[str | None] = mapped_column(String(32))
    actor_label: Mapped[str | None] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity: Mapped[str | None] = mapped_column(String(40))
    entity_id: Mapped[str | None] = mapped_column(String(64))
    payload_diff: Mapped[dict | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_keys"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(40))
    idem_key: Mapped[str] = mapped_column(String(200))
    request_hash: Mapped[str] = mapped_column(String(64))
    status_code: Mapped[int] = mapped_column(Integer)
    response_json: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint("scope", "idem_key", name="uq_idempotency_scope_key"),)
