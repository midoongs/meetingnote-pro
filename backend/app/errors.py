"""오류 본문은 항상 {code, msg}."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, status: int, code: str, msg: str):
        self.status = status
        self.code = code
        self.msg = msg


def bad(code: str, msg: str, status: int = 400) -> AppError:
    return AppError(status, code, msg)


def validation(msg: str) -> AppError:
    return AppError(400, "VALIDATION_ERROR", msg)


def forbidden(msg: str = "권한이 없음") -> AppError:
    return AppError(403, "FORBIDDEN", msg)


def owner_only() -> AppError:
    return AppError(403, "OWNER_ONLY", "owner 만 할 수 있음")


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, e: AppError):
        return JSONResponse({"code": e.code, "msg": e.msg}, status_code=e.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, e: RequestValidationError):
        return JSONResponse({"code": "VALIDATION_ERROR", "msg": "입력값이 올바르지 않음"}, status_code=400)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, e: StarletteHTTPException):
        code = {404: "NOT_FOUND", 403: "FORBIDDEN", 405: "NOT_FOUND"}.get(e.status_code, "VALIDATION_ERROR")
        return JSONResponse({"code": code, "msg": str(e.detail)}, status_code=e.status_code)
