"""TARS control server — FastAPI entry point."""

from __future__ import annotations

import uvicorn
from fastapi import FastAPI

from .config import get_settings
from .logger import get_logger
from .router import router

log = get_logger()

app = FastAPI(
    title="TARS Control Server",
    version="1.0.0",
    docs_url="/docs",
    redoc_url=None,
)

app.include_router(router)


@app.on_event("startup")
async def startup():
    log.info("TARS Control Server starting up")


def main():
    settings = get_settings()
    log.info("Launching TARS on %s:%d", settings.tars_host, settings.tars_port)
    uvicorn.run(
        "server.main:app",
        host=settings.tars_host,
        port=settings.tars_port,
        reload=False,
    )


if __name__ == "__main__":
    main()
