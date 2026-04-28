"""Shared document helpers."""

from core.services.documents.blocks import (
    RFBlock,
    extract_managed_blocks,
    extract_rf_blocks,
    merge_managed_blocks,
    render_managed_block,
)

__all__ = [
    "RFBlock",
    "extract_managed_blocks",
    "extract_rf_blocks",
    "merge_managed_blocks",
    "render_managed_block",
]
