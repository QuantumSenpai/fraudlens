import json
import logging
from contextlib import asynccontextmanager
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from routes import admin, checks, history, payments, predict, signals, stats
from services.config import settings
from services.db import db_reachable
from services.model_service import model_service

logger = logging.getLogger("fraudlens")
logging.basicConfig(level=logging.INFO, format="%(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    model_service.load()
    yield


app = FastAPI(title="FraudLens API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = str(uuid4())
    request.state.request_id = request_id
    started = perf_counter()
    response = await call_next(request)
    duration_ms = round((perf_counter() - started) * 1000, 2)
    response.headers["X-Request-ID"] = request_id
    response.headers["Server-Timing"] = f"app;dur={duration_ms}"
    logger.info(json.dumps({
        "event": "request_complete",
        "request_id": request_id,
        "method": request.method,
        "status": response.status_code,
        "duration_ms": duration_ms,
    }))
    return response


def error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {"code": code, "message": message},
            "request_id": getattr(request.state, "request_id", None),
        },
        headers=headers,
    )


@app.exception_handler(StarletteHTTPException)
async def http_error(request: Request, exc: StarletteHTTPException):
    messages = {
        401: "Authentication required",
        403: "Forbidden",
        409: "Request conflicts with current state",
        404: "Resource not found",
        405: "Method not allowed",
        429: "Rate limit exceeded",
        503: "Service unavailable",
    }
    codes = {
        401: "unauthorized",
        403: "forbidden",
        409: "conflict",
        404: "not_found",
        405: "method_not_allowed",
        429: "rate_limited",
        503: "service_unavailable",
    }
    code = codes.get(exc.status_code, "request_failed")
    message = messages.get(exc.status_code, "Request failed")
    headers = {key: value for key, value in (exc.headers or {}).items() if key.lower() in {"retry-after", "www-authenticate"}}
    return error_response(request, exc.status_code, code, message, headers)


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return error_response(request, 422, "validation_error", "Request validation failed")


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    logger.error(json.dumps({
        "event": "request_failed",
        "request_id": getattr(request.state, "request_id", None),
        "error_type": type(exc).__name__,
    }))
    return error_response(request, 500, "internal_error", "Internal server error")


app.include_router(predict.router)
app.include_router(checks.router)
app.include_router(payments.router)
app.include_router(admin.router)
app.include_router(history.router)
app.include_router(signals.router)
app.include_router(stats.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model_service.loaded,
        "db_reachable": db_reachable(),
    }
