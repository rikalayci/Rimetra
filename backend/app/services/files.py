from __future__ import annotations

import hashlib
import secrets
from pathlib import Path

from ..config import get_settings
from ..security import decrypt_bytes, encrypt_bytes


def _ensure(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


def store_pdf(member_id: str, report_id: str, data: bytes) -> tuple[str, str]:
    """PDF'i şifreleyip diske yazar. (göreli yol, sha256) döner."""
    sha = hashlib.sha256(data).hexdigest()
    rel = f"pdfs/{member_id}/{report_id}-{secrets.token_hex(4)}.pdf.enc"
    full = get_settings().data_path / rel
    _ensure(full.parent)
    full.write_bytes(encrypt_bytes(data))
    return rel, sha


def load_pdf(rel: str) -> bytes:
    return decrypt_bytes((get_settings().data_path / rel).read_bytes())


def delete_file(rel: str | None) -> None:
    if not rel:
        return
    p = get_settings().data_path / rel
    try:
        p.unlink(missing_ok=True)
    except OSError:
        pass


def store_avatar(member_id: str, data: bytes, ext: str) -> str:
    rel = f"avatars/{member_id}-{secrets.token_hex(4)}.{ext}.enc"
    full = get_settings().data_path / rel
    _ensure(full.parent)
    full.write_bytes(encrypt_bytes(data))
    return rel


def load_avatar(rel: str) -> bytes:
    return decrypt_bytes((get_settings().data_path / rel).read_bytes())


def is_pdf(data: bytes) -> bool:
    return data[:5] == b"%PDF-"


def image_ext(data: bytes) -> str | None:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if data[:3] == b"\xff\xd8\xff":
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None
