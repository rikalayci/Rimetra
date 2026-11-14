from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .i18n import t, translate, translate_payload


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict | None = None, **extra):
        self.status = status
        self.code = code
        self.message = message
        self.extra = extra
        self.headers = headers

    def body(self) -> dict:
        return {"error": {"code": self.code, "message": translate(self.message), **translate_payload(self.extra)}}


def not_found(what: str = "Kayıt") -> ApiError:
    return ApiError(404, "NOT_FOUND", f"{what} bulunamadı.")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        return JSONResponse(exc.body(), status_code=exc.status, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        fields = []
        for e in exc.errors():
            loc = [str(x) for x in e.get("loc", []) if x not in ("body", "query", "path")]
            fields.append({"field": ".".join(loc), "message": e.get("msg")})
        return JSONResponse(
            {"error": {"code": "VALIDATION_ERROR", "message": t("Eksik veya hatalı alan."), "fields": fields}},
            status_code=400,
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(
            exc.status_code, "HTTP_ERROR"
        )
        return JSONResponse({"error": {"code": code, "message": translate(str(exc.detail))}}, status_code=exc.status_code)
