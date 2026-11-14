from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .errors import ApiError
from .models import ApiKey, User, UserSession, utcnow
from .security import SCOPES, parse_api_key, rate_limiter, sha256_hex, verify_api_key

SESSION_COOKIE = "rimetra_session"


@dataclass
class Actor:
    kind: str  # user | api_key
    id: str
    label: str
    role: str = "api"  # master | member | api
    scopes: set[str] = field(default_factory=set)
    member_scope: list[str] | None = None  # None = tüm üyeler
    read_only: bool = False
    own_member_id: str | None = None
    ip: str | None = None

    @property
    def is_master(self) -> bool:
        return self.kind == "user" and self.role == "master"

    def can_access_member(self, member_id: str) -> bool:
        if self.member_scope is None:
            return True
        return member_id in self.member_scope

    def require_scope(self, scope: str) -> None:
        if scope not in self.scopes:
            raise ApiError(403, "SCOPE_DENIED", f"Bu işlem için '{scope}' yetkisi gerekli.")

    def require_member(self, member_id: str) -> None:
        if not self.can_access_member(member_id):
            raise ApiError(403, "MEMBER_DENIED", "Bu üyeye erişim yetkiniz yok.")


def client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


# ---------------------------------------------------------------- API anahtarı

def get_api_actor(request: Request, db: Session = Depends(get_db)) -> Actor:
    auth = request.headers.get("authorization", "")
    if not auth.lower().startswith("bearer "):
        raise ApiError(401, "INVALID_API_KEY", "API anahtarı gerekli (Authorization: Bearer ...).")
    full = auth[7:].strip()
    prefix = parse_api_key(full)
    if not prefix:
        raise ApiError(401, "INVALID_API_KEY", "API anahtarı hatalı.")
    key = db.scalar(select(ApiKey).where(ApiKey.key_prefix == prefix))
    if key is None or key.revoked_at is not None or not verify_api_key(full, key.key_hash, key.id):
        raise ApiError(401, "INVALID_API_KEY", "API anahtarı hatalı ya da iptal edilmiş.")

    ok, retry = rate_limiter.allow(f"key:{key.id}", get_settings().api_rate_limit_per_minute)
    if not ok:
        raise ApiError(429, "RATE_LIMITED", "Hız sınırı aşıldı.", headers={"Retry-After": str(retry)}, retry_after=retry)

    key.last_used_at = utcnow()
    db.commit()
    return Actor(
        kind="api_key",
        id=key.id,
        label=key.name,
        role="api",
        scopes=set(key.scopes or []),
        member_scope=list(key.member_scope) if key.member_scope else None,
        ip=client_ip(request),
    )


# ---------------------------------------------------------------- Oturum (web arayüzü)

def load_session_user(request: Request, db: Session) -> User | None:
    tok = request.cookies.get(SESSION_COOKIE)
    if not tok:
        return None
    sess = db.get(UserSession, sha256_hex(tok))
    if sess is None or sess.expires_at < utcnow():
        return None
    user = db.get(User, sess.user_id)
    if user is None or not user.is_active:
        return None
    # kayan süre: yarısı geçtiyse uzat
    remaining = sess.expires_at - utcnow()
    if remaining < timedelta(hours=get_settings().session_hours / 2):
        sess.expires_at = utcnow() + timedelta(hours=get_settings().session_hours)
        db.commit()
    return user


def actor_for_user(user: User, ip: str | None = None) -> Actor:
    if user.role == "master":
        return Actor(kind="user", id=user.id, label=user.username, role="master", scopes=set(SCOPES),
                     member_scope=None, own_member_id=user.member_id, ip=ip)
    scopes = {"reports:read", "members:read"}
    return Actor(kind="user", id=user.id, label=user.username, role="member", scopes=scopes,
                 member_scope=[user.member_id] if user.member_id else [], read_only=user.read_only,
                 own_member_id=user.member_id, ip=ip)


def get_user(request: Request, db: Session = Depends(get_db)) -> User:
    user = load_session_user(request, db)
    if user is None:
        raise ApiError(401, "UNAUTHORIZED", "Giriş yapmanız gerekiyor.")
    if request.method not in ("GET", "HEAD", "OPTIONS") and request.headers.get("x-rimetra") != "1":
        raise ApiError(403, "CSRF", "Geçersiz istek başlığı.")
    return user


def get_user_actor(request: Request, user: User = Depends(get_user)) -> Actor:
    return actor_for_user(user, client_ip(request))


def require_master(actor: Actor = Depends(get_user_actor)) -> Actor:
    if not actor.is_master:
        raise ApiError(403, "FORBIDDEN", "Bu işlem yalnızca master kullanıcıya açık.")
    return actor
