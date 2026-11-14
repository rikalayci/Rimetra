from __future__ import annotations

from sqlalchemy.orm import Session

from ..deps import Actor
from ..models import AuditLog


def audit(db: Session, actor: Actor | None, action: str, entity: str | None = None,
          entity_id: str | None = None, diff: dict | None = None, commit: bool = False) -> None:
    db.add(AuditLog(
        actor_type=actor.kind if actor else "system",
        actor_id=actor.id if actor else None,
        actor_label=actor.label if actor else "sistem",
        action=action,
        entity=entity,
        entity_id=entity_id,
        payload_diff=diff,
        ip=actor.ip if actor else None,
    ))
    if commit:
        db.commit()
