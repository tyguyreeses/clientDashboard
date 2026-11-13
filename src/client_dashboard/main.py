from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from .api.admin import router as admin_router
from .api.auth import router as auth_router
from .api.inquiry import router as inquiry_router
from .api.public import router as public_router

COMING_SOON = """<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\"><title>Hair By Maddie — Coming Soon</title></head><body><main><h1>Hair By Maddie</h1><p>Coming Soon</p></main></body></html>"""


def create_app() -> FastAPI:
    app = FastAPI(title="Client Dashboard API", docs_url=None, redoc_url=None, openapi_url=None)
    @app.middleware("http")
    async def security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response

    app.include_router(public_router)
    app.include_router(inquiry_router)
    app.include_router(auth_router)
    app.include_router(admin_router)

    @app.get("/", include_in_schema=False)
    def coming_soon():
        return HTMLResponse(COMING_SOON)

    return app


app = create_app()
