from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PaperDataLayout:
    name: str
    data_root: Path
    discover_root: Path
    search_batches_root: Path
    acquire_root: Path
    curated_root: Path
    library_root: Path
    legacy_library_roots: tuple[Path, ...]
    archive_root: Path
    template_root: Path
    reject_policy: str
    write_policy: str

    def ensure_paths(self) -> tuple[Path, ...]:
        paths = [
            self.search_batches_root,
            self.curated_root,
            self.library_root,
            self.template_root,
        ]
        if self.reject_policy == "archive":
            paths.append(self.archive_root)
        return tuple(paths)

    def protected_roots(self) -> tuple[Path, ...]:
        return (
            self.data_root,
            self.discover_root,
            self.search_batches_root,
            self.acquire_root,
            self.curated_root,
            self.library_root,
            *self.legacy_library_roots,
            self.archive_root,
            self.template_root,
        )


def resolve_data_layout(data_root: Path, data_layout: str = "native") -> PaperDataLayout:
    root = data_root.expanduser().resolve(strict=False)
    layout_name = data_layout.strip().lower() or "native"

    if layout_name == "native":
        return PaperDataLayout(
            name="native",
            data_root=root,
            discover_root=root / "Discover",
            search_batches_root=root / "Discover" / "search_batches",
            acquire_root=root / "Acquire",
            curated_root=root / "Acquire" / "curated",
            library_root=root / "01_Papers",
            legacy_library_roots=(),
            archive_root=root / "Archives",
            template_root=root / "templates",
            reject_policy="delete",
            write_policy="direct-delete-reject",
        )

    if layout_name == "research_vault":
        return PaperDataLayout(
            name="research_vault",
            data_root=root,
            discover_root=root / "02_Inbox",
            search_batches_root=root / "02_Inbox" / "01_Search",
            acquire_root=root / "02_Inbox",
            curated_root=root / "02_Inbox" / "02_Curated",
            library_root=root / "01_Papers",
            legacy_library_roots=(root / "03_Papers", root / "Papers"),
            archive_root=root / "06_Archives",
            template_root=root / "02_Inbox" / "03_Template",
            reject_policy="delete",
            write_policy="direct-delete-reject",
        )

    raise ValueError(f"Unsupported data layout: {data_layout}")


def _first_existing(root: Path, names: tuple[str, ...], *, default: str) -> Path:
    for name in names:
        candidate = root / name
        if candidate.exists():
            return candidate
    return root / default
