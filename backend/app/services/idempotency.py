from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..errors import ApiError
from ..models import IdempotencyRecord, utcnow


def lookup(db: Session, scope: str, key: str | None, request_hash: str) -> tuple[int, dict] | None:
    if not key:
        return None
    rec = db.scalar(select(IdempotencyRecord).where(IdempotencyRecord.scope == scope, IdempotencyRecord.idem_key == key))
    if rec is None:
        return None
    if rec.request_hash != request_hash:
        raise ApiError(409, "IDEMPOTENCY_KEY_REUSED", "Bu Idempotency-Key farklı bir istek gövdesiyle kullanılmış.")
    return rec.status_code, rec.response_json


def store(db: Session, scope: str, key: str | None, request_hash: str, status: int, body: dict) -> None:
    if not key:
        return
    try:
        db.add(IdempotencyRecord(scope=scope, idem_key=key[:200], request_hash=request_hash, status_code=status, response_json=body))
        db.commit()
    except IntegrityError:
        db.rollback()


def purge_old(db: Session, days: int = 7) -> None:
    db.execute(delete(IdempotencyRecord).where(IdempotencyRecord.created_at < utcnow() - timedelta(days=days)))
    db.commit()
