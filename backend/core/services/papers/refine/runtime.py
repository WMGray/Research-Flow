from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from core.config import get_settings
from core.services.llm import llm_registry
from core.services.llm.schemas import LLMMessage, LLMRequest, LLMResponse
from core.services.papers.skill_runtime import (
    load_skill_runtime_instructions,
    render_skill_instructions,
)
from .normalization import normalize_markdown_structure
from .parsing import (
    DeterministicNormalizationReport,
    PatchApplyReport,
    RefinePatch,
    RefineVerifyReport,
    build_line_index,
    build_line_numbered_markdown,
    build_structural_evidence_markdown,
    diagnosis_from_payload,
    extract_json_object,
    patches_from_payload,
)
from .patch import (
    apply_refine_patches,
    build_local_verify_report,
)


DEFAULT_REFINE_SKILL_KEY = "paper_refine_parse"


class LLMGenerateClient(Protocol):
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generate an LLM response for a configured feature."""


@dataclass(frozen=True, slots=True)
class ResolvedSkillBinding:
    skill_key: str
    diagnose_instruction_key: str
    repair_instruction_key: str
    verify_instruction_key: str
    diagnose_feature: str
    repair_feature: str
    verify_feature: str

    @property
    def instruction_key(self) -> str:
        return self.repair_instruction_key

    @property
    def feature(self) -> str:
        return self.repair_feature


@dataclass(frozen=True, slots=True)
class RefineExecutionResult:
    markdown_path: Path
    refined: bool
    error: str | None
    llm_run_id: str | None
    skill_key: str
    instruction_key: str
    feature: str
    artifact_dir: Path
    artifacts: dict[str, str]
    verify_status: str
    applied_patch_count: int
    rejected_patch_count: int
    deterministic_operation_count: int


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def resolve_skill_binding(skill_key: str) -> ResolvedSkillBinding:
    return ResolvedSkillBinding(
        skill_key=skill_key,
        diagnose_instruction_key=f"{skill_key}.diagnose",
        repair_instruction_key=f"{skill_key}.repair",
        verify_instruction_key=f"{skill_key}.verify",
        diagnose_feature=f"{skill_key}_diagnose",
        repair_feature=f"{skill_key}_repair",
        verify_feature=f"{skill_key}_verify",
    )


async def _generate_json(
    *,
    llm_client: LLMGenerateClient,
    feature: str,
    prompt: str,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    response = await llm_client.generate(
        LLMRequest(
            feature=feature,
            messages=[LLMMessage(role="user", content=prompt)],
            max_tokens=max_tokens,
            extra={"response_format": {"type": "json_object"}},
        )
    )
    return extract_json_object(response.message.content)


async def _refine_markdown_async(
    *,
    markdown_path: Path,
    output_path: Path,
    skill_key: str,
    instruction: str,
    llm_client: LLMGenerateClient,
    metadata: dict[str, Any] | None,
) -> RefineExecutionResult:
    settings = get_settings()
    if not settings.pdf_parser.markdown_refine.enabled:
        return _failed_result(markdown_path, output_path, skill_key, "markdown refine is disabled")

    raw_text = markdown_path.read_text(encoding="utf-8")
    if not raw_text.strip():
        return _failed_result(markdown_path, output_path, skill_key, "source markdown is empty")

    binding = resolve_skill_binding(skill_key)
    line_index = build_line_index(markdown_path, raw_text)
    line_numbered = build_structural_evidence_markdown(line_index)
    artifact_dir = output_path.parent / "refine"
    artifacts = _artifact_paths(artifact_dir)
    _write_json(artifacts["line_index"], asdict(line_index))
    llm_warnings: list[dict[str, Any]] = []

    common_values = {
        "instruction": instruction.strip(),
        "source_hash": line_index.source_hash,
        "line_numbered_markdown": line_numbered,
        "metadata_json": json.dumps(metadata or {}, ensure_ascii=False, indent=2),
    }
    try:
        diagnosis_payload = await _generate_json(
            llm_client=llm_client,
            feature=binding.diagnose_feature,
            prompt=render_skill_instructions(
                load_skill_runtime_instructions(binding.diagnose_instruction_key),
                common_values,
            ),
            max_tokens=2048,
        )
    except Exception as exc:  # noqa: BLE001 - preserve source and continue with review warning
        diagnosis_payload = {"source_hash": line_index.source_hash, "issues": []}
        llm_warnings.append(
            {
                "stage": "diagnose",
                "message": str(exc),
                "policy": "no_op_refine",
            }
        )
    diagnosis = diagnosis_from_payload(
        diagnosis_payload,
        source_hash=line_index.source_hash,
        line_count=line_index.line_count,
    )
    _write_json(
        artifacts["diagnosis"],
        {**asdict(diagnosis), "warnings": list(llm_warnings)},
    )

    patches: list[RefinePatch] = []
    if diagnosis.issues:
        try:
            patches_payload = await _generate_json(
                llm_client=llm_client,
                feature=binding.repair_feature,
                prompt=render_skill_instructions(
                    load_skill_runtime_instructions(binding.repair_instruction_key),
                    {
                        **common_values,
                        "diagnosis_json": json.dumps(asdict(diagnosis), ensure_ascii=False, indent=2),
                    },
                ),
                max_tokens=2048,
            )
            if str(patches_payload.get("source_hash") or line_index.source_hash) != line_index.source_hash:
                raise ValueError("repair response source_hash does not match line_index source_hash")
            patches = patches_from_payload(patches_payload, line_count=line_index.line_count)
        except Exception as exc:  # noqa: BLE001 - unsafe patches should not block raw preservation
            llm_warnings.append(
                {
                    "stage": "repair",
                    "message": str(exc),
                    "policy": "drop_llm_patches",
                }
            )
    _write_json(
        artifacts["patches"],
        {"source_hash": line_index.source_hash, "patches": [asdict(patch) for patch in patches]},
    )

    refined_text, apply_report = apply_refine_patches(
        markdown_text=raw_text,
        source_hash=line_index.source_hash,
        patches=patches,
    )
    _write_json(artifacts["patch_apply_report"], asdict(apply_report))
    refined_text, normalization_report = normalize_markdown_structure(
        refined_text,
        source_hash=line_index.source_hash,
        expected_title=str((metadata or {}).get("title") or ""),
    )
    _write_json(
        artifacts["deterministic_normalization"],
        asdict(normalization_report),
    )

    verify_context = _build_verify_context(
        raw_text=raw_text,
        refined_text=refined_text,
        line_index=line_index,
        apply_report=apply_report,
        normalization_report=normalization_report,
    )
    _write_json(
        artifacts["skill_context"],
        {
            "source_hash": line_index.source_hash,
            "raw_chars": len(raw_text),
            "refined_chars": len(refined_text),
            "structural_evidence_chars": len(line_numbered),
            "verify_context_chars": len(verify_context),
            "llm_warnings": llm_warnings,
            "metadata": metadata or {},
            "deterministic_operation_count": normalization_report.operation_count,
            "structural_evidence": line_numbered,
            "verify_context": verify_context,
        },
    )
    if not apply_report.changed:
        verify_payload = {
            "source_hash": line_index.source_hash,
            "status": "warning" if apply_report.review_items or llm_warnings else "pass",
            "summary": (
                "No LLM text patches were applied; deterministic normalization "
                "and local preservation checks are authoritative."
            ),
            "blocking_issues": [],
            "review_items": [*apply_report.review_items, *llm_warnings],
        }
    else:
        try:
            verify_payload = await _generate_json(
                llm_client=llm_client,
                feature=binding.verify_feature,
                prompt=render_skill_instructions(
                    load_skill_runtime_instructions(binding.verify_instruction_key),
                    {
                        "instruction": instruction.strip(),
                        "source_hash": line_index.source_hash,
                        "verify_context": verify_context,
                        "patch_apply_report_json": json.dumps(asdict(apply_report), ensure_ascii=False, indent=2),
                    },
                ),
                max_tokens=1024,
            )
        except Exception as exc:  # noqa: BLE001 - local verifier remains authoritative
            verify_payload = {
                "source_hash": line_index.source_hash,
                "status": "warning",
                "summary": "LLM verification returned invalid control data; local checks were used.",
                "blocking_issues": [],
                "review_items": [{"stage": "verify", "message": str(exc)}],
            }
    verify_report = build_local_verify_report(
        raw_text=raw_text,
        refined_text=refined_text,
        source_hash=line_index.source_hash,
        apply_report=apply_report,
        llm_verdict=verify_payload,
    )
    _write_json(artifacts["verify"], asdict(verify_report))

    needs_annotation = verify_report.status in ("warning", "fail")
    output_text = (
        _annotate_refine_warnings(refined_text, apply_report, verify_report)
        if needs_annotation
        else refined_text
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(output_text, encoding="utf-8")

    if verify_report.status == "fail":
        return _execution_result(
            output_path=output_path,
            binding=binding,
            artifact_dir=artifact_dir,
            artifacts=artifacts,
            refined=False,
            error="refine verification failed; annotated candidate written for review",
            verify_status=verify_report.status,
            apply_report=apply_report,
            normalization_report=normalization_report,
        )

    return _execution_result(
        output_path=output_path,
        binding=binding,
        artifact_dir=artifact_dir,
        artifacts=artifacts,
        refined=True,
        error=None,
        verify_status=verify_report.status,
        apply_report=apply_report,
        normalization_report=normalization_report,
    )


def _annotate_refine_warnings(
    refined_text: str,
    apply_report: PatchApplyReport,
    verify_report: RefineVerifyReport,
) -> str:
    """Inject refine review fields into the paper's YAML frontmatter.

    Uses the existing ``---`` / ``---`` block when present; otherwise creates one.
    Injected fields use a ``refine_review_`` prefix so they stay namespaced and
    do not collide with paper metadata.
    """
    review_fields: list[str] = []
    review_fields.append(f'refine_review_status: "{verify_report.status}"')

    parts: list[str] = []

    check_warnings = [
        c for c in verify_report.checks if c.get("status") != "pass"
    ]
    for c in check_warnings:
        name = c.get("name", "?")
        raw = c.get("raw_count")
        ref = c.get("refined_count")
        if name == "length_ratio":
            parts.append(f'{name}={c.get("ratio", "?")}')
        elif isinstance(raw, int) and isinstance(ref, int):
            parts.append(f'{name}({ref - raw:+d})')
        else:
            parts.append(f'{name}:{c.get("status", "?")}')
    if parts:
        review_fields.append(f'refine_review_checks: "{"; ".join(parts)}"')

    rejected = apply_report.rejected_patches
    if rejected:
        rj_parts = []
        for item in rejected:
            patch = item.get("patch", {})
            reason = item.get("reason", "?")
            start = patch.get("start_line", "?")
            end = patch.get("end_line", "?")
            issue_id = patch.get("issue_id", "?")
            rj_parts.append(f'{reason} @{start}-{end} ({issue_id})')
        review_fields.append(f'refine_review_rejected: "{"; ".join(rj_parts)}"')

    review_items = apply_report.review_items
    if review_items:
        ri_parts = []
        for item in review_items:
            start = item.get("start_line", "?")
            end = item.get("end_line", "?")
            issue_id = item.get("issue_id", "?")
            ri_parts.append(f'{issue_id} @{start}-{end}')
        review_fields.append(f'refine_review_items: "{"; ".join(ri_parts)}"')

    review_fields.append('refine_review_artifact: "refine/verify.json"')

    lines = refined_text.splitlines()
    if len(lines) >= 2 and lines[0].strip() == "---":
        end_index = next(
            (
                index
                for index, line in enumerate(lines[1:], start=1)
                if line.strip() == "---"
            ),
            None,
        )
        if end_index is not None:
            existing = [
                line
                for line in lines[1:end_index]
                if not line.startswith("refine_review_")
            ]
            annotated = [lines[0], *existing, *review_fields, *lines[end_index:]]
            return "\n".join(annotated).rstrip() + "\n"

    return "\n".join(["---", *review_fields, "---", "", refined_text.rstrip()]) + "\n"


def _artifact_paths(artifact_dir: Path) -> dict[str, Path]:
    return {
        "line_index": artifact_dir / "line_index.json",
        "diagnosis": artifact_dir / "diagnosis.json",
        "patches": artifact_dir / "patches.json",
        "patch_apply_report": artifact_dir / "patch_apply_report.json",
        "deterministic_normalization": artifact_dir / "deterministic_normalization.json",
        "skill_context": artifact_dir / "skill_context.json",
        "verify": artifact_dir / "verify.json",
    }


def _build_verify_context(
    *,
    raw_text: str,
    refined_text: str,
    line_index: Any,
    apply_report: PatchApplyReport,
    normalization_report: DeterministicNormalizationReport,
) -> str:
    lines = [
        "# Refine Verification Context",
        f"source_hash: {apply_report.source_hash}",
        f"output_hash: {apply_report.output_hash}",
        f"raw_chars: {len(raw_text)}",
        f"refined_chars: {len(refined_text)}",
        f"line_count: {line_index.line_count}",
        f"changed: {str(apply_report.changed).lower()}",
        f"applied_patch_count: {len(apply_report.applied_patch_ids)}",
        f"rejected_patch_count: {len(apply_report.rejected_patches)}",
        f"deterministic_changed: {str(normalization_report.changed).lower()}",
        f"deterministic_operation_count: {normalization_report.operation_count}",
        f"review_item_count: {len(apply_report.review_items)}",
        "",
        (
            "The complete raw/refined Markdown is intentionally not repeated here. "
            "The deterministic verifier receives the full texts locally and checks "
            "citations, numbers, formulas, image links, and length preservation."
        ),
    ]
    if not apply_report.changed:
        lines.append("No LLM patch changed the Markdown body.")
    if normalization_report.changed:
        lines.append("Deterministic normalization changed Markdown structure.")
    return "\n".join(lines)


def _failed_result(
    markdown_path: Path,
    output_path: Path,
    skill_key: str,
    error: str,
) -> RefineExecutionResult:
    return RefineExecutionResult(
        markdown_path=markdown_path,
        refined=False,
        error=error,
        llm_run_id=None,
        skill_key=skill_key,
        instruction_key="",
        feature="",
        artifact_dir=output_path.parent / "refine",
        artifacts={},
        verify_status="fail",
        applied_patch_count=0,
        rejected_patch_count=0,
        deterministic_operation_count=0,
    )


def _execution_result(
    *,
    output_path: Path,
    binding: ResolvedSkillBinding,
    artifact_dir: Path,
    artifacts: dict[str, Path],
    refined: bool,
    error: str | None,
    verify_status: str,
    apply_report: PatchApplyReport,
    normalization_report: DeterministicNormalizationReport,
) -> RefineExecutionResult:
    return RefineExecutionResult(
        markdown_path=output_path,
        refined=refined,
        error=error,
        llm_run_id=f"llm_{uuid4().hex}" if refined else None,
        skill_key=binding.skill_key,
        instruction_key=binding.instruction_key,
        feature=binding.feature,
        artifact_dir=artifact_dir,
        artifacts={key: str(path) for key, path in artifacts.items()},
        verify_status=verify_status,
        applied_patch_count=len(apply_report.applied_patch_ids),
        rejected_patch_count=len(apply_report.rejected_patches),
        deterministic_operation_count=normalization_report.operation_count,
    )


def refine_markdown(
    *,
    markdown_path: Path,
    output_path: Path,
    skill_key: str,
    instruction: str,
    llm_client: LLMGenerateClient = llm_registry,
    metadata: dict[str, Any] | None = None,
) -> RefineExecutionResult:
    return asyncio.run(
        _refine_markdown_async(
            markdown_path=markdown_path,
            output_path=output_path,
            skill_key=skill_key,
            instruction=instruction,
            llm_client=llm_client,
            metadata=metadata,
        )
    )


__all__ = [
    "DEFAULT_REFINE_SKILL_KEY",
    "RefineExecutionResult",
    "apply_refine_patches",
    "build_line_index",
    "build_line_numbered_markdown",
    "refine_markdown",
    "resolve_skill_binding",
]
