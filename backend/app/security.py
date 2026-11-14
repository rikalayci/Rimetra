from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
import time
from collections import defaultdict, deque

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError, InvalidHashError
from cryptography.fernet import Fernet

from .config import get_settings

_ph = PasswordHasher()  # argon2id varsayılan

API_KEY_PREFIX = "rmt_live_"
SCOPES = ["reports:read", "reports:write", "members:read", "members:write", "catalog:write"]


def hash_password(pw: str) -> str:
    return _ph.hash(pw)


def verify_password(pw: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, pw)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


# ---------------- Oturum ----------------

def new_session_token() -> tuple[str, str]:
    tok = secrets.token_urlsafe(32)
    return tok, sha256_hex(tok)


# ---------------- API anahtarı ----------------

def generate_api_key() -> tuple[str, str, str]:
    """(tam anahtar, key_prefix, argon2 hash). Prefix = rastgele kısmın ilk 8 karakteri."""
    body = secrets.token_urlsafe(30).replace("-", "x").replace("_", "y")
    full = API_KEY_PREFIX + body
    return full, body[:8], _ph.hash(full)


def parse_api_key(full: str) -> str | None:
    if not full.startswith(API_KEY_PREFIX):
        return None
    body = full[len(API_KEY_PREFIX):]
    if len(body) < 16:
        return None
    return body[:8]


# Doğrulanmış anahtarlar için kısa ömürlü önbellek (argon2 her istekte pahalı)
_key_cache: dict[str, tuple[str, float]] = {}
_key_cache_lock = threading.Lock()


def verify_api_key(full: str, key_hash: str, key_id: str) -> bool:
    fp = sha256_hex(full)
    now = time.time()
    with _key_cache_lock:
        hit = _key_cache.get(fp)
        if hit and hit[0] == key_id and hit[1] > now:
            return True
    try:
        ok = _ph.verify(key_hash, full)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        ok = False
    if ok:
        with _key_cache_lock:
            _key_cache[fp] = (key_id, now + 300)
    return ok


def forget_api_key_cache() -> None:
    with _key_cache_lock:
        _key_cache.clear()


# ---------------- Hız sınırı ----------------

class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window: float = 60.0) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and q[0] <= now - window:
                q.popleft()
            if len(q) >= limit:
                retry = int(window - (now - q[0])) + 1
                return False, retry
            q.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


rate_limiter = RateLimiter()


# ---------------- Başarısız giriş gecikmesi ----------------

class LoginThrottle:
    """Artan bekleme: eşik sonrası her başarısız deneme 2^n saniye kilit (en çok 15 dk)."""

    def __init__(self) -> None:
        self._fails: dict[str, tuple[int, float]] = {}
        self._lock = threading.Lock()

    def wait_seconds(self, key: str) -> int:
        with self._lock:
            n, until = self._fails.get(key, (0, 0.0))
        rem = until - time.time()
        return int(rem) + 1 if rem > 0 else 0

    def fail(self, key: str) -> None:
        threshold = get_settings().login_fails_before_delay
        with self._lock:
            n, _ = self._fails.get(key, (0, 0.0))
            n += 1
            delay = 0 if n < threshold else min(2 ** (n - threshold + 1), 900)
            self._fails[key] = (n, time.time() + delay)

    def success(self, key: str) -> None:
        with self._lock:
            self._fails.pop(key, None)

    def reset(self) -> None:
        with self._lock:
            self._fails.clear()


login_throttle = LoginThrottle()


# ---------------- Şifreleme (PDF ve yedekler) ----------------

def _fernet() -> Fernet:
    raw = hashlib.sha256(get_settings().data_encryption_key.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw))


def encrypt_bytes(data: bytes) -> bytes:
    return _fernet().encrypt(data)


def decrypt_bytes(data: bytes) -> bytes:
    return _fernet().decrypt(data)


# ---------------- Önizleme jetonu (MCP) ----------------

def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)


def make_preview_token(key_id: str, body_hash: str, ttl: int = 3600) -> str:
    exp = int(time.time()) + ttl
    msg = f"{key_id}.{body_hash}.{exp}"
    sig = hmac.new(get_settings().secret_key.encode(), msg.encode(), hashlib.sha256).hexdigest()[:32]
    return f"pvw.{exp}.{sig}"


def check_preview_token(token: str, key_id: str, body_hash: str) -> bool:
    try:
        _, exp_s, sig = token.split(".")
        exp = int(exp_s)
    except (ValueError, AttributeError):
        return False
    if exp < time.time():
        return False
    msg = f"{key_id}.{body_hash}.{exp}"
    good = hmac.new(get_settings().secret_key.encode(), msg.encode(), hashlib.sha256).hexdigest()[:32]
    return hmac.compare_digest(good, sig)
