"""Şifreli yedekleme: pg_dump + PDF/avatar klasörleri → tar → Fernet ile şifreli tek dosya.

Dosyalar DATA_DIR/backups altında durur (host'ta ./data/backups). BACKUP_RETENTION_DAYS günden eski
yedekler silinir. Geri yükleme: `docker compose exec app rimetra restore <dosya>`.
"""
from __future__ import annotations

import io
import os
import re
import subprocess
import tarfile
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

from ..config import get_settings
from ..errors import ApiError
from ..security import decrypt_bytes, encrypt_bytes

_lock = threading.Lock()
_status: dict = {"last_run": None, "last_ok": None, "last_error": None}
_NAME_RE = re.compile(r"^rimetra-\d{8}-\d{6}\.tar\.enc$")


def _pg_env() -> tuple[dict, list[str]]:
    url = get_settings().database_url.replace("postgresql+psycopg://", "postgresql://")
    u = urlparse(url)
    env = os.environ.copy()
    if u.password:
        env["PGPASSWORD"] = u.password
    args = ["-h", u.hostname or "localhost", "-p", str(u.port or 5432), "-U", u.username or "postgres"]
    return env, args + [u.path.lstrip("/")]


def run_backup() -> dict:
    s = get_settings()
    if not _lock.acquire(blocking=False):
        raise ApiError(409, "BACKUP_RUNNING", "Bir yedekleme zaten çalışıyor.")
    try:
        _status["last_run"] = datetime.now().isoformat(timespec="seconds")
        s.backup_dir.mkdir(parents=True, exist_ok=True)
        env, args = _pg_env()
        dump = subprocess.run(["pg_dump", "-Fc", "--no-owner", *args[:-1], "-d", args[-1]], env=env,
                              capture_output=True, timeout=600)
        if dump.returncode != 0:
            raise RuntimeError(dump.stderr.decode(errors="replace")[:500])
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tar:
            info = tarfile.TarInfo("db.dump")
            info.size = len(dump.stdout)
            tar.addfile(info, io.BytesIO(dump.stdout))
            for sub in ("pdfs", "avatars"):
                p = s.data_path / sub
                if p.exists():
                    tar.add(p, arcname=sub)
        name = f"rimetra-{datetime.now().strftime('%Y%m%d-%H%M%S')}.tar.enc"
        out = s.backup_dir / name
        out.write_bytes(encrypt_bytes(buf.getvalue()))
        prune()
        _status["last_ok"] = _status["last_run"]
        _status["last_error"] = None
        return {"name": name, "size": out.stat().st_size}
    except Exception as e:  # noqa: BLE001
        _status["last_error"] = str(e)[:500]
        if isinstance(e, ApiError):
            raise
        raise ApiError(500, "BACKUP_FAILED", f"Yedekleme başarısız: {str(e)[:300]}")
    finally:
        _lock.release()


def prune() -> int:
    s = get_settings()
    cutoff = datetime.now() - timedelta(days=s.backup_retention_days)
    n = 0
    for f in s.backup_dir.glob("rimetra-*.tar.enc"):
        if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
            f.unlink(missing_ok=True)
            n += 1
    return n


def list_backups() -> list[dict]:
    d = get_settings().backup_dir
    if not d.exists():
        return []
    files = sorted(d.glob("rimetra-*.tar.enc"), reverse=True)
    return [{"name": f.name, "size": f.stat().st_size,
             "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(timespec="seconds")} for f in files]


def last_status() -> dict:
    return dict(_status)


def backup_path(name: str) -> Path:
    if not _NAME_RE.match(name):
        raise ApiError(400, "VALIDATION_ERROR", "Geçersiz yedek adı.")
    p = get_settings().backup_dir / name
    if not p.exists():
        raise ApiError(404, "NOT_FOUND", "Yedek bulunamadı.")
    return p


def restore_backup(file: Path) -> None:
    """Komut satırından çağrılır. Veritabanını ve dosyaları yedekteki hale getirir."""
    s = get_settings()
    raw = decrypt_bytes(file.read_bytes())
    with tempfile.TemporaryDirectory() as tmp:
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tar:
            tar.extractall(tmp, filter="data")
        env, args = _pg_env()
        r = subprocess.run(["pg_restore", "--clean", "--if-exists", "--no-owner", *args[:-1], "-d", args[-1],
                            str(Path(tmp) / "db.dump")], env=env, capture_output=True)
        if r.returncode not in (0, 1):
            raise RuntimeError(r.stderr.decode(errors="replace")[:1000])
        import shutil
        for sub in ("pdfs", "avatars"):
            src = Path(tmp) / sub
            dst = s.data_path / sub
            if src.exists():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
