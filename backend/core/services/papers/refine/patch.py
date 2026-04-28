from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import hashlib
import re
from typing import Any

from .parsing import (
    PatchApplyReport,
    RefinePatch,
    RefineVerifyReport,
)


CITATION_RE = re.compile(r"\[[0-9,\-\s;]+\]|\([A-Z][A-Za-z-]+(?: et al\.)?,\s*\d{4}[a-z]?\)")
NUMBER_RE = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?%?")
IMAGE_RE = re.compile(r"!\[[^\]]*]\([^)]+\)")
FORMULA_RE = re.compile(r"\$\$?|\\begin\{(?:equation|align|gather)")
TRUNCATED_EVIDENCE_RE = re.compile(r"\[truncated chars=\d+\s+sha256=[0-9a-f]{16,}\]")
FLOAT_NUMBER_PATTERN = r"(?:[A-Za-z]\.\d+(?:\.\d+)*|[A-Za-z]?\d+(?:\.\d+)*)"
FLOAT_CAPTION_RE = re.compile(
    rf"^\s*>\s*(?:fig(?:ure)?|table)\s*{FLOAT_NUMBER_PATTERN}",
    re.IGNORECASE,
)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b")
INSTITUTION_HINT_RE = re.compile(
    r"\b(?:University|Institute|College|Corporation|Inc\.?|Ltd\.?|Department|Laboratory|Lab)\b",
    re.IGNORECASE,
)
METADATA_PATCH_WINDOW_LINES = 40


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def apply_refine_patches(
    *,
    markdown_text: str,
    source_hash: str,
    patches: list[RefinePatch],
    min_confidence: float = 0.65,
) -> tuple[str, PatchApplyReport]:
    lines = markdown_text.splitlines()
    edited = list(lines)
    applied: list[str] = []
    rejected: list[dict[str, Any]] = []
    review_items: list[dict[str, Any]] = []
    occupied: set[int] = set()

    for patch in sorted(patches, key=lambda item: item.start_line, reverse=True):
        reason = _patch_rejection_reason(patch, len(lines), min_confidence, occupied)
        if patch.op == "mark_needs_review":
            review_items.append(asdict(patch))
            continue
        if reason is not None:
            rejected.append({"patch": asdict(patch), "reason": reason})
            continue
        start = patch.start_line - 1
        end = patch.end_line
        content_reason = _patch_content_rejection_reason(patch, lines[start:end])
        if content_reason is not None:
            rejected.append({"patch": asdict(patch), "reason": content_reason})
            continue
        if patch.op == "replace_span":
            edited[start:end] = patch.replacement.splitlines()
        elif patch.op == "insert_after":
            edited[patch.start_line : patch.start_line] = patch.replacement.splitlines()
        elif patch.op == "delete_span":
            del edited[start:end]
        applied.append(patch.patch_id)
        occupied.update(range(patch.start_line, patch.end_line + 1))

    refined_text = "\n".join(edited).rstrip() + "\n"
    report = PatchApplyReport(
        source_hash=source_hash,
        output_hash=_sha256_text(refined_text),
        changed=refined_text != markdown_text.rstrip() + "\n",
        applied_patch_ids=list(reversed(applied)),
        rejected_patches=list(reversed(rejected)),
        review_items=list(reversed(review_items)),
    )
    return refined_text, report


def build_local_verify_report(
    *,
    raw_text: str,
    refined_text: str,
    source_hash: str,
    apply_report: PatchApplyReport,
    llm_verdict: dict[str, Any],
) -> RefineVerifyReport:
    raw_paper_text = _paper_content(raw_text)
    refined_paper_text = _paper_content(refined_text)
    checks = [
        _count_check(
            "citations",
            CITATION_RE,
            raw_paper_text,
            refined_paper_text,
            allow_added=True,
        ),
        _count_check(
            "numbers",
            NUMBER_RE,
            _without_emails(raw_paper_text),
            _without_emails(refined_paper_text),
            allow_added=True,
        ),
        _count_check(
            "image_links",
            IMAGE_RE,
            raw_paper_text,
            refined_paper_text,
            allow_added=False,
        ),
        _count_check(
            "formula_markers",
            FORMULA_RE,
            raw_paper_text,
            refined_paper_text,
            allow_added=True,
        ),
        _length_ratio_check(raw_text, refined_text),
    ]
    if apply_report.rejected_patches:
        checks.append(
            {
                "name": "patch_rejections",
                "status": "warning",
                "detail": f"{len(apply_report.rejected_patches)} patches rejected.",
            }
        )
    llm_status = str(llm_verdict.get("status") or "").lower()
    if llm_status == "fail":
        checks.append({"name": "llm_verdict", "status": "fail", "detail": llm_verdict})
    elif llm_status == "warning":
        checks.append({"name": "llm_verdict", "status": "warning", "detail": llm_verdict})

    statuses = {str(check["status"]) for check in checks}
    status = "fail" if "fail" in statuses else "warning" if "warning" in statuses else "pass"
    return RefineVerifyReport(
        source_hash=source_hash,
        output_hash=_sha256_text(refined_text),
        status=status,
        checks=checks,
        llm_verdict=llm_verdict,
    )


def _patch_rejection_reason(
    patch: RefinePatch,
    line_count: int,
    min_confidence: float,
    occupied: set[int],
) -> str | None:
    if patch.confidence < min_confidence:
        return "confidence_below_threshold"
    if patch.op not in {"replace_span", "insert_after", "delete_span", "mark_needs_review"}:
        return "unsupported_operation"
    if patch.start_line < 1 or patch.end_line < patch.start_line:
        return "invalid_line_range"
    if patch.op != "insert_after" and patch.end_line > line_count:
        return "line_range_out_of_bounds"
    if patch.op in {"replace_span", "insert_after"} and not patch.replacement.strip():
        return "replacement_is_empty"
    if patch.op in {"replace_span", "insert_after"} and TRUNCATED_EVIDENCE_RE.search(patch.replacement):
        return "replacement_contains_truncated_evidence"
    if patch.op != "insert_after" and any(
        line_no in occupied for line_no in range(patch.start_line, patch.end_line + 1)
    ):
        return "overlapping_patch_range"
    return None


def _patch_content_rejection_reason(patch: RefinePatch, source_lines: list[str]) -> str | None:
    if patch.op != "replace_span":
        return None
    source_text = "\n".join(source_lines)
    source_images = set(IMAGE_RE.findall(source_text))
    replacement_images = set(IMAGE_RE.findall(patch.replacement))
    if source_images and not source_images.issubset(replacement_images):
        return "replacement_drops_image_links"
    if _is_front_matter_metadata_patch(patch, source_text):
        return "metadata_replacement_missing_front_matter_labels"
    if FLOAT_CAPTION_RE.match(patch.replacement):
        source_numbers = Counter(NUMBER_RE.findall(source_text))
        replacement_numbers = Counter(NUMBER_RE.findall(patch.replacement))
        if source_numbers - replacement_numbers:
            return "caption_replacement_drops_numbers"
    return None


def _is_front_matter_metadata_patch(patch: RefinePatch, source_text: str) -> bool:
    if patch.start_line > METADATA_PATCH_WINDOW_LINES:
        return False
    if not (EMAIL_RE.search(source_text) or INSTITUTION_HINT_RE.search(source_text)):
        return False
    replacement = patch.replacement.lower()
    return "authors:" not in replacement or "institutions:" not in replacement


def _count_check(
    name: str,
    pattern: re.Pattern[str],
    raw_text: str,
    refined_text: str,
    *,
    allow_added: bool,
) -> dict[str, Any]:
    raw_items = pattern.findall(raw_text)
    refined_items = pattern.findall(refined_text)
    missing = len(raw_items) - len(refined_items)
    ok = missing <= 0 if allow_added else set(raw_items).issubset(set(refined_items))
    return {
        "name": name,
        "status": "pass" if ok else "fail",
        "raw_count": len(raw_items),
        "refined_count": len(refined_items),
    }


def _without_emails(text: str) -> str:
    return EMAIL_RE.sub("", text)


def _paper_content(text: str) -> str:
    ignored_prefixes = (
        "- Parser:",
        "- Figure rendering:",
        "- Organization:",
        "- Embedded figure references:",
    )
    return "\n".join(
        line for line in text.splitlines() if not line.strip().startswith(ignored_prefixes)
    )


def _length_ratio_check(raw_text: str, refined_text: str) -> dict[str, Any]:
    raw_len = max(len(raw_text.strip()), 1)
    ratio = len(refined_text.strip()) / raw_len
    status = "pass" if 0.55 <= ratio <= 2.20 else "fail"
    return {"name": "length_ratio", "status": status, "ratio": ratio}
