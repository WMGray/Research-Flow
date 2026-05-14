from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.app.library import PaperLibrary
from backend.app.settings import get_settings


class IngestRequest(BaseModel):
    source: str
    domain: str | None = None
    area: str | None = None
    topic: str | None = None
    target_path: str | None = None
    move: bool = False


class GenerateNoteRequest(BaseModel):
    title: str | None = None
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    domain: str | None = None
    area: str | None = None
    topic: str | None = None
    tags: list[str] = Field(default_factory=lambda: ["paper"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    app.state.library = PaperLibrary(settings.data_root)
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_library() -> PaperLibrary:
    library = getattr(app.state, "library", None)
    if library is None:
        library = PaperLibrary(settings.data_root)
        app.state.library = library
    return library


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard/home")
def dashboard_home() -> dict[str, Any]:
    return {"ok": True, "data": get_library().dashboard_home(), "error": None}


@app.get("/api/dashboard/papers-overview")
def dashboard_papers_overview() -> dict[str, Any]:
    library = get_library()
    data = {
        "papers": [paper.to_dict() for paper in library.list_papers()],
        "totals": library.dashboard_home()["totals"],
    }
    return {"ok": True, "data": data, "error": None}


@app.get("/api/dashboard/discover")
def dashboard_discover() -> dict[str, Any]:
    return {"ok": True, "data": get_library().dashboard_discover(), "error": None}


@app.get("/api/dashboard/acquire")
def dashboard_acquire() -> dict[str, Any]:
    return {"ok": True, "data": get_library().dashboard_acquire(), "error": None}


@app.get("/api/dashboard/library")
def dashboard_library() -> dict[str, Any]:
    return {"ok": True, "data": get_library().dashboard_library(), "error": None}


@app.get("/api/papers")
def list_papers() -> dict[str, Any]:
    papers = [paper.to_dict() for paper in get_library().list_papers()]
    return {"ok": True, "data": {"items": papers, "total": len(papers)}, "error": None}


@app.get("/api/papers/{paper_id}")
def paper_detail(paper_id: str) -> dict[str, Any]:
    paper = get_library().get_paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return {"ok": True, "data": paper.to_dict(), "error": None}


@app.post("/api/papers/ingest")
def ingest_paper(request: IngestRequest) -> dict[str, Any]:
    paper = get_library().ingest(
        Path(request.source),
        domain=request.domain,
        area=request.area,
        topic=request.topic,
        target_path=request.target_path,
        move=request.move,
    )
    return {"ok": True, "data": paper.to_dict(), "error": None}


@app.post("/api/papers/migrate")
def migrate_paper(request: IngestRequest) -> dict[str, Any]:
    paper = get_library().migrate(
        Path(request.source),
        domain=request.domain,
        area=request.area,
        topic=request.topic,
        target_path=request.target_path,
    )
    return {"ok": True, "data": paper.to_dict(), "error": None}


@app.post("/api/papers/generate-note")
def generate_note(request: GenerateNoteRequest) -> dict[str, Any]:
    metadata = {
        "title": request.title or "",
        "year": request.year or "",
        "venue": request.venue or "",
        "doi": request.doi or "",
        "domain": request.domain or "",
        "area": request.area or "",
        "topic": request.topic or "",
        "status": "draft",
        "tags": request.tags or ["paper"],
    }
    content = get_library().generate_note_template(metadata)
    return {"ok": True, "data": {"content": content}, "error": None}

