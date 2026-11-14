from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..i18n import normalize_lang
from ..config import get_settings
from ..db import get_db
from ..deps import SESSION_COOKIE, actor_for_user, client_ip, get_user, load_session_user
from ..errors import ApiError
from ..models import User, UserSession, utcnow
from ..schemas import LoginIn, PasswordChangeIn
from ..security import hash_password, login_throttle, new_session_token, sha256_hex, verify_password
from ..services.audit import audit
from ..services.queries import member_public

router = APIRouter(prefix="/api/auth", tags=["Oturum"])

# Kullanıcı adı yoksa da aynı sürede yanıt vermek için sahte hash
_DUMMY_HASH = hash_password("rimetra-dummy-password")


def user_public(u: User) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "role": u.role,
        "read_only": u.read_only,
        "theme": u.theme,
        "lang": u.lang,
        "member_id": u.member_id,
        "member": member_public(u.member) if u.member else None,
        "telegram": {
            "linked": u.telegram_chat_id is not None,
            "username": u.telegram_username,
            "linked_at": u.telegram_linked_at.isoformat() if u.telegram_linked_at else None,
            "notify": u.telegram_notify,
        },
    }


@router.post("/login")
def login(body: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    ip = client_ip(request) or "?"
    uname = body.username.strip().lower()
    for key in (f"u:{uname}", f"ip:{ip}"):
        wait = login_throttle.wait_seconds(key)
        if wait:
            raise ApiError(429, "RATE_LIMITED", f"Çok fazla başarısız deneme. {wait} sn sonra tekrar deneyin.",
                           headers={"Retry-After": str(wait)}, retry_after=wait)
    user = db.scalar(select(User).where(func.lower(User.username) == uname))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok or not user.is_active:
        login_throttle.fail(f"u:{uname}")
        login_throttle.fail(f"ip:{ip}")
        audit(db, None, "auth.login_failed", "user", user.id if user else None, {"username": uname[:64], "ip": ip}, commit=True)
        raise ApiError(401, "INVALID_CREDENTIALS", "Kullanıcı adı veya şifre hatalı.")
    login_throttle.success(f"u:{uname}")
    login_throttle.success(f"ip:{ip}")

    tok, tid = new_session_token()
    s = get_settings()
    db.add(UserSession(id=tid, user_id=user.id, expires_at=utcnow() + timedelta(hours=s.session_hours), ip=ip,
                       user_agent=(request.headers.get("user-agent") or "")[:300]))
    user.last_login_at = utcnow()
    db.execute(delete(UserSession).where(UserSession.expires_at < utcnow()))
    audit(db, actor_for_user(user, ip), "auth.login", "user", user.id)
    db.commit()
    response.set_cookie(SESSION_COOKIE, tok, max_age=s.session_hours * 3600, httponly=True, secure=s.cookie_secure,
                        samesite="strict", path="/")
    return user_public(user)


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    tok = request.cookies.get(SESSION_COOKIE)
    if tok:
        db.execute(delete(UserSession).where(UserSession.id == sha256_hex(tok)))
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    user = load_session_user(request, db)
    if user is None:
        raise ApiError(401, "UNAUTHORIZED", "Giriş yapmanız gerekiyor.")
    return user_public(user)


@router.post("/password")
def change_password(body: PasswordChangeIn, request: Request, user: User = Depends(get_user), db: Session = Depends(get_db)):
    if not verify_password(body.current_password, user.password_hash):
        raise ApiError(400, "INVALID_CREDENTIALS", "Mevcut şifre hatalı.")
    user.password_hash = hash_password(body.new_password)
    # diğer oturumları kapat
    current = request.cookies.get(SESSION_COOKIE)
    db.execute(delete(UserSession).where(UserSession.user_id == user.id, UserSession.id != sha256_hex(current or "")))
    audit(db, actor_for_user(user, client_ip(request)), "auth.password_change", "user", user.id)
    db.commit()
    return {"ok": True}


@router.patch("/prefs")
def prefs(body: dict, user: User = Depends(get_user), db: Session = Depends(get_db)):
    theme = body.get("theme")
    if theme in ("light", "dark", "system"):
        user.theme = theme
    if "lang" in body:
        user.lang = normalize_lang(body.get("lang"))
    db.commit()
    return user_public(user)
