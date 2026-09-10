from __future__ import annotations

from fastapi import FastAPI

from client_dashboard.api.routes import router


def create_app() -> FastAPI:
    app = FastAPI(title="Client Dashboard API")
    app.include_router(router)
    return app


app = create_app()

