"""Compatibility layer for legacy imports.

Prefer importing the Paper service from ``backend.core.services.papers``.
"""

from backend.core.services.papers.service import PaperService as PaperLibrary
from backend.core.services.papers.utils import slugify, write_json, write_text, write_yaml

__all__ = ["PaperLibrary", "slugify", "write_json", "write_text", "write_yaml"]
