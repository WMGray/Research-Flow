from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.config import router as config_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.discover import router as discover_router
from backend.app.api.papers import router as papers_router
from backend.app.schemas.common import HealthResponse
from backend.core.config import get_settings
from backend.core.services.papers.service import PaperService


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.paper_service = PaperService(data_root=settings.data_root)
    yield


settings = get_settings()
origins = list(
    dict.fromkeys(
        [
            settings.frontend_origin,
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
    )
)

app = FastAPI(
    title=settings.app_name,
    description="Research-Flow Paper workflow backend",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(dashboard_router)
app.include_router(papers_router)
app.include_router(config_router)
app.include_router(discover_router)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
