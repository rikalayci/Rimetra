from __future__ import annotations

import logging

from sqlalchemy import func, select

from .catalog_seed import seed_catalog
from .config import get_settings
from .db import SessionLocal
from .models import Member, User
from .security import hash_password

log = logging.getLogger("rimetra")


def ensure_dirs() -> None:
    s = get_settings()
    for d in (s.data_path, s.pdf_dir, s.avatar_dir, s.backup_dir):
        d.mkdir(parents=True, exist_ok=True)


def create_master(db, username: str, password: str, display_name: str | None = None) -> User:
    if db.scalar(select(User.id).where(func.lower(User.username) == username.lower())):
        raise ValueError(f"'{username}' kullanıcı adı zaten var.")
    member = None
    if display_name:
        member = Member(display_name=display_name, sort_order=0)
        db.add(member)
        db.flush()
    u = User(username=username, password_hash=hash_password(password), role="master",
             member_id=member.id if member else None)
    db.add(u)
    db.commit()
    return u


def bootstrap() -> None:
    ensure_dirs()
    s = get_settings()
    with SessionLocal() as db:
        added = seed_catalog(db)
        if added:
            log.info("Kataloğa %d test eklendi.", added)
        from .services.mutations import relink_unmapped
        linked, conflicts = relink_unmapped(db)
        if linked or conflicts:
            log.info("Eşleşmemiş sonuçlardan %d tanesi kataloğa bağlandı (%d çakışma).", linked, conflicts)
        has_master = db.scalar(select(User.id).where(User.role == "master").limit(1))
        if not has_master and s.initial_master_username and s.initial_master_password:
            create_master(db, s.initial_master_username.strip(), s.initial_master_password,
                          s.initial_master_display_name.strip() or None)
            log.warning("İlk master kullanıcı oluşturuldu: %s", s.initial_master_username)
        elif not has_master:
            log.warning("Henüz master kullanıcı yok. Oluşturmak için: docker compose exec app rimetra create-master")
