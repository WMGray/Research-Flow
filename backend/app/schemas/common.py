from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class APIEnvelope(BaseModel):
    ok: bool
    data: Any = None
    error: Any | None = None


class HealthResponse(BaseModel):
    status: str
