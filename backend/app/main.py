from __future__ import annotations

import logging
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from .api import app as app_api
from .api import auth, mcp, v1
from .config import get_settings
from .errors import install_error_handlers
from .i18n import lang_from_accept, normalize_lang, t, use_lang

log = logging.getLogger("rimetra")
STATIC_DIR = Path(__file__).parent / "static"


def _check_keys() -> None:
    s = get_settings()
    bad = s.insecure_keys()
    if not bad:
        return
    msg = (f"{', '.join(bad)} varsayılan/örnek değerde. .env dosyasında uzun rastgele bir değer verin: "
           'python3 -c "import secrets; print(secrets.token_urlsafe(48))"')
    if s.allow_insecure_keys:
        log.warning("GÜVENSİZ: %s (ALLOW_INSECURE_KEYS=true)", msg)
        return
    raise RuntimeError(msg)


def _startup_tasks() -> None:
    _check_keys()
    from .bootstrap import bootstrap
    bootstrap()


def _scheduler(stop: threading.Event) -> None:
    from .db import SessionLocal
    from .services import backup, idempotency
    from .services.ingest import local_tz
    from .services.mutations import purge_expired_reports

    last_backup_day = None
    last_purge_day = None
    while not stop.wait(60):
        s = get_settings()
        now = datetime.now(local_tz())
        today = now.date()
        try:
            if last_purge_day != today:
                with SessionLocal() as db:
                    purge_expired_reports(db)
                    idempotency.purge_old(db)
                last_purge_day = today
            if s.backup_enabled and now.hour == s.backup_hour and last_backup_day != today:
                last_backup_day = today
                info = backup.run_backup()
                log.info("Günlük yedek alındı: %s", info["name"])
        except Exception as e:  # noqa: BLE001
            log.exception("Zamanlanmış görev hatası: %s", e)


@asynccontextmanager
async def lifespan(_: FastAPI):
    _startup_tasks()
    stop = threading.Event()
    if not get_settings().disable_scheduler:
        threading.Thread(target=_scheduler, args=(stop,), daemon=True, name="rimetra-scheduler").start()
        from .services import telegram
        telegram.start(stop)
    yield
    stop.set()


def create_app() -> FastAPI:
    app = FastAPI(title="Rimetra", version="1.3.0", lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    install_error_handlers(app)

    # API dokümanı yalnızca giriş yapmış kullanıcıya açık
    from fastapi import Depends
    from fastapi.openapi.docs import get_swagger_ui_html
    from .deps import get_user

    @app.get("/api/openapi.json", include_in_schema=False)
    def openapi_json(_=Depends(get_user)):
        return app.openapi()

    @app.get("/api/docs", include_in_schema=False)
    def docs(_=Depends(get_user)):
        return get_swagger_ui_html(openapi_url="/api/openapi.json", title="Rimetra API")

    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        resp: Response = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        if request.url.path.startswith("/api/"):
            resp.headers.setdefault("Cache-Control", "no-store")
        if get_settings().cookie_secure:
            resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
        return resp

    app.include_router(auth.router)
    app.include_router(app_api.router)
    app.include_router(v1.router)
    app.include_router(mcp.router)

    @app.get("/healthz", include_in_schema=False)
    def healthz():
        return {"ok": True}

    @app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"], include_in_schema=False)
    def api_404(rest: str):
        return JSONResponse({"error": {"code": "NOT_FOUND", "message": t("Uç nokta bulunamadı.")}}, status_code=404)

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str):
        if STATIC_DIR.exists():
            candidate = (STATIC_DIR / full_path).resolve()
            if full_path and candidate.is_file() and STATIC_DIR.resolve() in candidate.parents:
                headers = {"Cache-Control": "public, max-age=31536000, immutable"} if full_path.startswith("assets/") else {}
                return FileResponse(candidate, headers=headers)
            index = STATIC_DIR / "index.html"
            if index.exists():
                return FileResponse(index, headers={"Cache-Control": "no-cache"})
        return JSONResponse({"message": t("Rimetra API çalışıyor. Arayüz derlenmemiş (frontend/ → npm run build).")})

    app.add_middleware(LangMiddleware)
    return app


class LangMiddleware:
    """İstek dilini belirler: X-Rimetra-Lang başlığı > ?lang= > rimetra_lang çerezi > Accept-Language > tr."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode("latin-1").lower(): v.decode("latin-1") for k, v in scope.get("headers", [])}
        lang = normalize_lang(headers.get("x-rimetra-lang"))
        if not lang and scope.get("query_string"):
            from urllib.parse import parse_qs
            q = parse_qs(scope["query_string"].decode("latin-1"))
            lang = normalize_lang((q.get("lang") or [None])[0])
        if not lang and "cookie" in headers:
            for part in headers["cookie"].split(";"):
                k, _, v = part.strip().partition("=")
                if k == "rimetra_lang":
                    lang = normalize_lang(v)
        lang = lang or lang_from_accept(headers.get("accept-language"))
        with use_lang(lang):
            await self.app(scope, receive, send)


app = create_app()
