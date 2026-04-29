from __future__ import annotations

import json
from pathlib import Path

from core.config import reset_settings
from core.services.llm.schemas import LLMMessage, LLMRequest, LLMResponse
from core.services.papers.models import PaperRecord, utc_now
from core.services.papers.repository import _rewrite_section_image_links
from core.services.papers.refine import normalize_markdown_structure, refine_markdown
from core.services.papers.refine.patch import apply_refine_patches, build_local_verify_report
from core.services.papers.refine.parsing import (
    RefinePatch,
    build_line_index,
    build_line_numbered_markdown,
)
from core.services.papers.split import (
    split_canonical_sections,
    split_sections_deterministically,
)
from core.services.papers.note import collect_figure_evidence, generate_paper_note


class SequenceLLM:
    def __init__(self, responses: list[dict]) -> None:
        self.responses = list(responses)
        self.requests: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        payload = self.responses.pop(0)
        return LLMResponse(
            feature=request.feature or "",
            model_key="fake_refine_runtime",
            platform="fake",
            provider="fake",
            model="fake-model",
            message=LLMMessage(role="assistant", content=json.dumps(payload)),
        )


class BadJsonLLM:
    def __init__(self) -> None:
        self.requests: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return LLMResponse(
            feature=request.feature or "",
            model_key="bad_json",
            platform="fake",
            provider="fake",
            model="fake-model",
            message=LLMMessage(role="assistant", content='{"source_hash": "unterminated'),
        )


def test_refine_runtime_applies_structured_patch_and_writes_artifacts(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.md"
    output_path = tmp_path / "refined.md"
    raw_path.write_text(
        "\n".join(
            [
                "# Demo Paper",
                "",
                "1 Introduction",
                "The method improves accuracy by 95% [1].",
                "",
                "Figure 1. Overview.",
            ]
        ),
        encoding="utf-8",
    )
    fake_llm = SequenceLLM(
        [
            {
                "source_hash": "",
                "issues": [
                    {
                        "issue_id": "issue_001",
                        "type": "heading_ambiguous",
                        "start_line": 3,
                        "end_line": 3,
                        "severity": "medium",
                        "confidence": 0.91,
                        "description": "The introduction heading lacks Markdown syntax.",
                        "suggested_action": "normalize_heading",
                        "needs_pdf_context": False,
                    }
                ],
            },
            {
                "source_hash": "",
                "patches": [
                    {
                        "patch_id": "patch_001",
                        "issue_id": "issue_001",
                        "op": "replace_span",
                        "start_line": 3,
                        "end_line": 3,
                        "replacement": "## 1 Introduction",
                        "confidence": 0.95,
                        "rationale": "Normalize section heading.",
                    }
                ],
            },
            {
                "source_hash": "",
                "status": "pass",
                "summary": "The patch preserves the paper content.",
                "blocking_issues": [],
                "review_items": [],
            },
        ]
    )

    reset_settings()
    result = refine_markdown(
        markdown_path=raw_path,
        output_path=output_path,
        skill_key="paper_refine_parse",
        instruction="Keep citation markers intact.",
        llm_client=fake_llm,
    )

    assert result.refined is True
    assert result.applied_patch_count == 1
    assert result.verify_status == "pass"
    assert [request.feature for request in fake_llm.requests] == [
        "paper_refine_parse_diagnose",
        "paper_refine_parse_repair",
        "paper_refine_parse_verify",
    ]
    assert "## 1 Introduction" in output_path.read_text(encoding="utf-8")
    assert "95% [1]" in output_path.read_text(encoding="utf-8")
    assert (tmp_path / "refine" / "line_index.json").exists()
    assert (tmp_path / "refine" / "deterministic_normalization.json").exists()
    assert (tmp_path / "refine" / "patch_apply_report.json").exists()
    assert (tmp_path / "refine" / "verify.json").exists()


def test_refine_runtime_blocks_patch_that_drops_citation(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.md"
    output_path = tmp_path / "refined.md"
    raw_path.write_text(
        "# Demo Paper\n\nThe method improves accuracy by 95% [1].\n",
        encoding="utf-8",
    )
    fake_llm = SequenceLLM(
        [
            {
                "source_hash": "",
                "issues": [
                    {
                        "issue_id": "issue_001",
                        "type": "ocr_artifact",
                        "start_line": 3,
                        "end_line": 3,
                        "severity": "high",
                        "confidence": 0.9,
                        "description": "Fake destructive patch.",
                        "suggested_action": "replace_span",
                    }
                ],
            },
            {
                "source_hash": "",
                "patches": [
                    {
                        "patch_id": "patch_001",
                        "issue_id": "issue_001",
                        "op": "replace_span",
                        "start_line": 3,
                        "end_line": 3,
                        "replacement": "The method improves accuracy.",
                        "confidence": 0.95,
                    }
                ],
            },
            {
                "source_hash": "",
                "status": "pass",
                "summary": "Fake verifier missed the issue.",
                "blocking_issues": [],
                "review_items": [],
            },
        ]
    )

    reset_settings()
    result = refine_markdown(
        markdown_path=raw_path,
        output_path=output_path,
        skill_key="paper_refine_parse",
        instruction="",
        llm_client=fake_llm,
    )

    assert result.refined is False
    assert result.verify_status == "fail"
    assert output_path.exists()
    annotated = output_path.read_text(encoding="utf-8")
    assert 'refine_review_status: "fail"' in annotated
    assert "refine_review_checks" in annotated
    verify_payload = json.loads((tmp_path / "refine" / "verify.json").read_text(encoding="utf-8"))
    assert any(check["name"] == "citations" and check["status"] == "fail" for check in verify_payload["checks"])


def test_refine_verify_ignores_front_matter_metadata_artifacts() -> None:
    raw_text = "\n".join(
        [
            "# Demo Paper",
            "",
            r"Ning Wang \dag ^ {1}",
            "School of AI, Wuxi 214121",
            "",
            "## Abstract",
            r"The method improves accuracy by 95% [1] with $Z ^ {0}$.",
        ]
    )
    patch = RefinePatch(
        patch_id="patch_001",
        issue_id="issue_001",
        op="replace_span",
        start_line=3,
        end_line=4,
        replacement="Authors: Ning Wang\nInstitutions: School of AI",
        confidence=0.95,
    )
    refined_text, apply_report = apply_refine_patches(
        markdown_text=raw_text,
        source_hash="demo",
        patches=[patch],
    )

    report = build_local_verify_report(
        raw_text=raw_text,
        refined_text=refined_text,
        source_hash="demo",
        apply_report=apply_report,
        llm_verdict={"status": "pass"},
    )

    assert report.status == "pass"
    assert {check["name"]: check["status"] for check in report.checks}["numbers"] == "pass"
    assert {check["name"]: check["status"] for check in report.checks}["formula_markers"] == "pass"


def test_refine_verify_warns_on_duplicate_number_cleanup() -> None:
    raw_text = "\n".join(
        [
            "# Demo Paper",
            "",
            "## Abstract",
            "The method improves accuracy by 95% [1].",
            "Figure 1. Overview.",
            "Figure 1. Overview.",
        ]
    )
    patch = RefinePatch(
        patch_id="patch_001",
        issue_id="issue_001",
        op="delete_span",
        start_line=6,
        end_line=6,
        replacement="",
        confidence=0.95,
    )
    refined_text, apply_report = apply_refine_patches(
        markdown_text=raw_text,
        source_hash="demo",
        patches=[patch],
    )

    report = build_local_verify_report(
        raw_text=raw_text,
        refined_text=refined_text,
        source_hash="demo",
        apply_report=apply_report,
        llm_verdict={"status": "pass"},
    )

    assert report.status == "warning"
    assert {check["name"]: check["status"] for check in report.checks}["numbers"] == "warning"


def test_refine_runtime_uses_structural_evidence_for_large_markdown(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.md"
    output_path = tmp_path / "refined.md"
    raw_lines = [
        "# Demo Paper",
        "",
        "# ABSTRACT",
        "This paper studies a robust parsing workflow.",
        "",
        "# 1 INTRODUCTION",
        *[f"Body paragraph {index}. " + ("x" * 180) for index in range(500)],
        "# REFERENCES",
        "Author. Title. 2024.",
    ]
    raw_text = "\n".join(raw_lines) + "\n"
    raw_path.write_text(raw_text, encoding="utf-8")
    fake_llm = SequenceLLM(
        [
            {
                "source_hash": "",
                "issues": [],
            }
        ]
    )

    reset_settings()
    result = refine_markdown(
        markdown_path=raw_path,
        output_path=output_path,
        skill_key="paper_refine_parse",
        instruction="Use compact structural evidence.",
        llm_client=fake_llm,
    )

    full_line_numbered = build_line_numbered_markdown(build_line_index(raw_path, raw_text))
    diagnose_prompt = fake_llm.requests[0].messages[0].content
    assert result.refined is True
    assert [request.feature for request in fake_llm.requests] == ["paper_refine_parse_diagnose"]
    assert "Only selected structural windows are shown." in diagnose_prompt
    assert len(diagnose_prompt) < len(full_line_numbered) // 2
    refined_text = output_path.read_text(encoding="utf-8")
    assert "## Abstract" in refined_text
    assert "## 1 INTRODUCTION" in refined_text
    assert "## References" in refined_text


def test_refine_runtime_still_normalizes_structure_when_llm_returns_bad_json(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.md"
    output_path = tmp_path / "refined.md"
    raw_text = "\n".join(
        [
            "# LORA: LOW-RANK ADAPTATION OF LARGE LAN-GUAGE MODELS",
            "Edward J . Hu, Y e l o n g Shen",
            "",
            "# ABSTRACT",
            "The method preserves 95% accuracy [1].",
            "",
            "# 5 EMPIRICAL EXPERIMENTS",
            "We evaluate the method.",
            "",
            "# 5.1 METHOD DETAILS",
            "This child heading should stay under section 5.",
            "",
        ]
    )
    raw_path.write_text(raw_text, encoding="utf-8")
    bad_llm = BadJsonLLM()

    reset_settings()
    result = refine_markdown(
        markdown_path=raw_path,
        output_path=output_path,
        skill_key="paper_refine_parse",
        instruction="Preserve raw text if control JSON is invalid.",
        llm_client=bad_llm,
        metadata={"title": "LoRA: Low-Rank Adaptation of Large Language Models"},
    )

    diagnosis_payload = json.loads((tmp_path / "refine" / "diagnosis.json").read_text(encoding="utf-8"))
    verify_payload = json.loads((tmp_path / "refine" / "verify.json").read_text(encoding="utf-8"))
    assert result.refined is True
    assert result.verify_status == "warning"
    assert [request.feature for request in bad_llm.requests] == ["paper_refine_parse_diagnose"]
    assert result.deterministic_operation_count > 0
    refined_text = output_path.read_text(encoding="utf-8")
    assert "# LoRA: Low-Rank Adaptation of Large Language Models" in refined_text
    assert "Edward J. Hu, Yelong Shen" in refined_text
    assert "## Abstract" in refined_text
    assert "## 5 EMPIRICAL EXPERIMENTS" in refined_text
    assert "### 5.1 METHOD DETAILS" in refined_text
    assert diagnosis_payload["warnings"][0]["stage"] == "diagnose"
    assert verify_payload["llm_verdict"]["status"] == "warning"
    normalization_payload = json.loads(
        (tmp_path / "refine" / "deterministic_normalization.json").read_text(encoding="utf-8")
    )
    assert normalization_payload["operation_count"] == result.deterministic_operation_count


def test_deterministic_split_keeps_numbered_child_heading_under_parent() -> None:
    content = "\n".join(
        [
            "# Demo Paper",
            "",
            "## 4 OUR METHOD",
            "Method overview.",
            "",
            "### 4.1 LOW-RANK PARAMETRIZATION",
            "Method details.",
            "",
            "## 5 EMPIRICAL EXPERIMENTS",
            "Experiment overview.",
            "",
            "### 5.1 METHOD DETAILS FOR EVALUATION",
            "This is an experiment child section, not the canonical method section.",
            "",
            "## 6 RELATED WORKS",
            "Prior work.",
            "",
            "## 8 CONCLUSION AND FUTURE WORK",
            "Conclusion.",
        ]
    )

    blocks, report = split_sections_deterministically(content)

    assert report["status"] == "pass"
    assert "LOW-RANK PARAMETRIZATION" in blocks["method"]
    assert "METHOD DETAILS FOR EVALUATION" in blocks["experiment"]
    assert "METHOD DETAILS FOR EVALUATION" not in blocks["method"]
    assert set(blocks) == {
        "introduction",
        "related_work",
        "method",
        "experiment",
        "conclusion",
    }
    assert "Demo Paper" in blocks["introduction"]


def test_deterministic_split_does_not_infer_related_view_from_introduction() -> None:
    content = "\n".join(
        [
            "# Demo Paper",
            "",
            "## 1 Introduction",
            "We study robust adaptation.",
            "",
            (
                "Existing methods [1, 2] usually update all parameters. However, these "
                "prior works fail to support efficient deployment."
            ),
            "",
            "Our method addresses this gap.",
            "",
            "## 2 Method",
            "The proposed adapter freezes the backbone.",
        ]
    )

    blocks, report = split_sections_deterministically(content)

    assert "Existing methods [1, 2]" in blocks["introduction"]
    assert "related_work" not in blocks
    assert "The proposed adapter" in blocks["method"]
    assert "secondary_related_range_count" not in report


def test_normalization_keeps_appendix_child_heading_under_letter_parent() -> None:
    content = "\n".join(
        [
            "# Demo",
            "",
            "## F ADDITIONAL EMPIRICAL EXPERIMENTS",
            "Appendix experiment overview.",
            "",
            "# F.1 ADDITIONAL EXPERIMENTS ON GPT-2",
            "Additional child details.",
            "",
        ]
    )

    normalized, report = normalize_markdown_structure(content, source_hash="hash")
    blocks, split_report = split_sections_deterministically(
        normalized
        + "\n## 5 EMPIRICAL EXPERIMENTS\nMain experiments.\n"
        + "\n### 5.1 EVALUATION DETAILS\nChild experiment details.\n"
    )

    assert "## F ADDITIONAL EMPIRICAL EXPERIMENTS" in normalized
    assert "### F.1 ADDITIONAL EXPERIMENTS ON GPT-2" in normalized
    assert "\n# F.1 ADDITIONAL EXPERIMENTS ON GPT-2" not in normalized
    assert any(
        operation.before == "# F.1 ADDITIONAL EXPERIMENTS ON GPT-2"
        and operation.after == "### F.1 ADDITIONAL EXPERIMENTS ON GPT-2"
        for operation in report.operations
    )
    appendix_heading = next(
        heading for heading in split_report["headings"] if heading["number"] == "f.1"
    )
    assert appendix_heading["is_major"] is False
    assert "ADDITIONAL EXPERIMENTS ON GPT-2" not in blocks["experiment"]
    assert "ADDITIONAL EXPERIMENTS ON GPT-2" in blocks["appendix"]


def test_normalization_restores_known_technical_term_case() -> None:
    content = "\n".join(
        [
            "# Demo",
            "Fine-tuning and Low-Rank Adaptation stay as written.",
            "LoRA is used throughout the paper.",
            "The mAP metric must not rewrite a feature map.",
            "",
            "### 4.2 Applying Lora to Transformer",
        ]
    )

    normalized, report = normalize_markdown_structure(content, source_hash="hash")

    assert "### 4.2 Applying LoRA to Transformer" in normalized
    assert "Fine-tuning and Low-Rank Adaptation stay as written." in normalized
    assert "feature map" in normalized
    assert "feature mAP" not in normalized
    assert any(
        operation.operation_type.endswith("restore_term_case")
        for operation in report.operations
    )


def test_normalization_formats_captions_and_marks_missing_caption() -> None:
    content = "\n".join(
        [
            "# Demo",
            "",
            "## 2 Method",
            "![](figures/figure_1.png)",
            "",
            "Figure 1: Method overview.",
            "",
            "![](figures/figure_2.png)",
            "",
            "Method text after an image without a caption.",
            "",
            "Table 1: Dataset statistics.",
            "<table><tr><td>A</td></tr></table>",
            "",
            "![](figures/figure_a1.png)",
            "> **图注**：Figure A.1: Appendix detail.",
        ]
    )

    normalized, report = normalize_markdown_structure(content, source_hash="hash")

    assert "![](figures/figure_1.png)\n> Figure 1: Method overview." in normalized
    assert ">[!warning]" in normalized
    assert "> No reliable caption was matched near this image; verify against the source PDF." in normalized
    assert "> Table 1: Dataset statistics." in normalized
    assert "> Figure A.1: Appendix detail." in normalized
    assert any(
        operation.operation_type == "format_float_caption_blockquote"
        for operation in report.operations
    )
    assert any(
        operation.operation_type == "mark_image_caption_needs_review"
        for operation in report.operations
    )


def test_normalization_converts_mineru_formula_wrappers() -> None:
    content = "\n".join(
        [
            "# Demo",
            "",
            "> **图注**：Figure 1: We train equation_inline A text and equation_inline B text.",
            "> **图注**：Figure 2: Input equation_inline I_{t} text uses equation_inline \\Phi_{\\mathrm{ENC}} text.",
            "> **图注**：Figure 3: Baseline equation_inline ( r = 0 text ) and equation_inline 30 \\% text.",
        ]
    )

    normalized, report = normalize_markdown_structure(content, source_hash="hash")

    assert "equation_inline" not in normalized
    assert "> Figure 1: We train $A$ and $B$." in normalized
    assert "> Figure 2: Input $I_{t}$ uses $\\Phi_{\\mathrm{ENC}}$." in normalized
    assert "> Figure 3: Baseline $( r = 0 )$ and $30 \\%$." in normalized
    assert any(
        "normalize_formula_wrapper" in operation.operation_type
        for operation in report.operations
    )


def test_normalization_repairs_front_matter_and_moves_interrupted_figure() -> None:
    content = "\n".join(
        [
            "# Demo Paper",
            "",
            "- Parser: `MinerU`",
            "",
            "A. Author B. Writer",
            "",
            "Demo University",
            "",
            "author@example.com",
            "",
            "## Abstract",
            "",
            "Existing methods",
            "",
            "![](figures/figure_1.png)",
            "> **图注**：Figure 1: Overview.",
            "",
            "often add latency.",
        ]
    )

    normalized, report = normalize_markdown_structure(content, source_hash="hash")

    assert "Authors: A. Author, B. Writer" in normalized
    assert "Institutions: Demo University" in normalized
    assert "author@example.com" not in normalized
    assert "Existing methods often add latency.\n\n![](figures/figure_1.png)" in normalized
    assert "> Figure 1: Overview." in normalized
    assert any(
        operation.operation_type == "normalize_author_institution_metadata"
        for operation in report.operations
    )
    assert any(
        operation.operation_type == "move_interrupted_image_block"
        for operation in report.operations
    )


def test_normalization_removes_split_email_fragments_from_front_matter() -> None:
    content = "\n".join(
        [
            "# Demo Paper",
            "",
            "A. Author B. Writer",
            "",
            "Demo University",
            "",
            "{author, writer,",
            "",
            "writer}@demo.edu",
            "",
            "## Abstract",
            "",
            "Body.",
        ]
    )

    normalized, _ = normalize_markdown_structure(content, source_hash="hash")

    assert "Authors: A. Author, B. Writer" in normalized
    assert "Institutions: Demo University" in normalized
    front_matter = normalized.split("## Abstract", maxsplit=1)[0]
    assert "{" not in front_matter
    assert "@" not in front_matter
    assert "demo.edu" not in normalized


def test_normalization_preserves_author_when_email_is_inline() -> None:
    content = "\n".join(
        [
            "# Demo Paper",
            "",
            "A. Author author@example.com",
            "",
            "Demo University",
            "",
            "## Abstract",
            "",
            "Body.",
        ]
    )

    normalized, _ = normalize_markdown_structure(content, source_hash="hash")

    assert "Authors: A. Author" in normalized
    assert "Institutions: Demo University" in normalized
    assert "author@example.com" not in normalized


def test_patch_engine_rejects_truncated_evidence_replacements() -> None:
    raw_text = "Table 1: Metrics.\n<table><tr><td>1</td></tr></table>\n"
    patches = [
        RefinePatch(
            patch_id="patch_001",
            issue_id="issue_001",
            op="replace_span",
            start_line=1,
            end_line=2,
            replacement=(
                "> Table 1: Metrics.\n"
                "<table><tr><td>1</td></tr> ... [truncated chars=80 sha256=abcdef1234567890]</table>"
            ),
            confidence=0.9,
        )
    ]

    refined, report = apply_refine_patches(
        markdown_text=raw_text,
        source_hash="hash",
        patches=patches,
    )

    assert refined == raw_text
    assert report.rejected_patches[0]["reason"] == "replacement_contains_truncated_evidence"


def test_patch_engine_rejects_caption_replacements_that_drop_numbers() -> None:
    raw_text = "Table 2: Results from Houlsby et al. (2019).\n"
    patches = [
        RefinePatch(
            patch_id="patch_001",
            issue_id="issue_001",
            op="replace_span",
            start_line=1,
            end_line=1,
            replacement="> Table 2: Results from Houlsby et al.",
            confidence=0.9,
        )
    ]

    refined, report = apply_refine_patches(
        markdown_text=raw_text,
        source_hash="hash",
        patches=patches,
    )

    assert refined == raw_text
    assert report.rejected_patches[0]["reason"] == "caption_replacement_drops_numbers"


def test_patch_engine_rejects_image_replacements_that_drop_links() -> None:
    raw_text = "![](figures/figure_1.png)\n>[!Caution]\n"
    patches = [
        RefinePatch(
            patch_id="patch_001",
            issue_id="issue_001",
            op="replace_span",
            start_line=1,
            end_line=2,
            replacement=">[!warning]\n> Caption needs review.",
            confidence=0.9,
        )
    ]

    refined, report = apply_refine_patches(
        markdown_text=raw_text,
        source_hash="hash",
        patches=patches,
    )

    assert refined == raw_text
    assert report.rejected_patches[0]["reason"] == "replacement_drops_image_links"


def test_patch_engine_allows_caption_insert_after_image() -> None:
    raw_text = "![](figures/figure_1.png)\n"
    patches = [
        RefinePatch(
            patch_id="patch_001",
            issue_id="issue_001",
            op="insert_after",
            start_line=1,
            end_line=1,
            replacement="> Figure 1: Overview.",
            confidence=0.9,
        )
    ]

    refined, report = apply_refine_patches(
        markdown_text=raw_text,
        source_hash="hash",
        patches=patches,
    )

    assert refined == "![](figures/figure_1.png)\n> Figure 1: Overview.\n"
    assert report.applied_patch_ids == ["patch_001"]
    assert report.rejected_patches == []


def test_patch_engine_rejects_unlabeled_front_matter_replacements() -> None:
    raw_text = "A. Author\nDemo University\nauthor@example.com\n"
    patches = [
        RefinePatch(
            patch_id="patch_001",
            issue_id="issue_001",
            op="replace_span",
            start_line=1,
            end_line=3,
            replacement="A. Author\nDemo University",
            confidence=0.9,
        )
    ]

    refined, report = apply_refine_patches(
        markdown_text=raw_text,
        source_hash="hash",
        patches=patches,
    )

    assert refined == raw_text
    assert report.rejected_patches[0]["reason"] == "metadata_replacement_missing_front_matter_labels"


def test_local_verify_allows_omitted_email_numbers() -> None:
    raw_text = "Authors: A\nh.wang3@uva.nl\nNumber 42 is preserved.\n"
    refined_text = "Authors: A\nNumber 42 is preserved.\n"
    _, apply_report = apply_refine_patches(
        markdown_text=raw_text,
        source_hash="hash",
        patches=[],
    )

    report = build_local_verify_report(
        raw_text=raw_text,
        refined_text=refined_text,
        source_hash="hash",
        apply_report=apply_report,
        llm_verdict={"status": "pass"},
    )

    assert report.status == "pass"


def test_llm_section_split_fallback_uses_audited_line_ranges() -> None:
    content = "\n".join(
        [
            "# Demo Paper",
            "",
            "## 1 Introduction",
            "Context.",
            "## 2 Proposed Framework",
            "Method body.",
            "## 3 Results",
            "Experiment body.",
            "## 4 Final Remarks",
            "Conclusion body.",
        ]
    )
    fake_llm = SequenceLLM(
        [
            {
                "sections": [
                    {
                        "section_key": "introduction",
                        "start_line": 1,
                        "end_line": 4,
                        "confidence": 0.9,
                        "rationale": "Title and Introduction are the front matter.",
                    },
                    {
                        "section_key": "method",
                        "start_line": 5,
                        "end_line": 6,
                        "confidence": 0.9,
                        "rationale": "Proposed Framework is the method section.",
                    },
                    {
                        "section_key": "experiment",
                        "start_line": 7,
                        "end_line": 8,
                        "confidence": 0.9,
                        "rationale": "Results is the empirical section.",
                    },
                    {
                        "section_key": "conclusion",
                        "start_line": 9,
                        "end_line": 10,
                        "confidence": 0.9,
                        "rationale": "Final Remarks is the conclusion.",
                    },
                ]
            }
        ]
    )

    result = split_canonical_sections(content, llm_client=fake_llm)

    assert result.report["used_llm"] is True
    assert result.report["strategy"] == "llm_semantic"
    assert fake_llm.requests[0].feature == "paper_sectioning_default"
    assert "Demo Paper" in result.blocks["introduction"]
    assert "Proposed Framework" in result.blocks["method"]
    assert "Results" in result.blocks["experiment"]


def test_llm_section_split_allows_multi_section_line_ranges() -> None:
    content = "\n".join(
        [
            "# Demo Paper",
            "",
            "## 3 Model and Training",
            "The architecture and training protocol are defined together.",
        ]
    )
    fake_llm = SequenceLLM(
        [
            {
                "sections": [
                    {
                        "section_key": "method",
                        "start_line": 3,
                        "end_line": 4,
                        "confidence": 0.9,
                        "rationale": "The range defines model architecture.",
                    },
                    {
                        "section_key": "experiment",
                        "start_line": 3,
                        "end_line": 4,
                        "confidence": 0.9,
                        "rationale": "The same range defines the training protocol.",
                    },
                ]
            }
        ]
    )

    result = split_canonical_sections(content, llm_client=fake_llm)

    assert "Model and Training" in result.blocks["method"]
    assert "Model and Training" in result.blocks["experiment"]
    assert result.report["llm"]["rejected"] == []


def test_llm_section_split_fills_uncovered_non_reference_lines_and_images() -> None:
    content = "\n".join(
        [
            "# Demo Paper",
            "",
            "## 1 Introduction",
            "Intro text.",
            "![](images/figure_1.png)",
            "> Figure 1: Intro overview.",
            "## 2 Related Work",
            "Prior work evidence.",
            "## References",
            "[1] Reference text should be removed.",
        ]
    )
    fake_llm = SequenceLLM(
        [
            {
                "sections": [
                    {
                        "section_key": "introduction",
                        "start_line": 1,
                        "end_line": 4,
                        "confidence": 0.9,
                        "rationale": "The LLM selected the intro text but missed the figure and related work.",
                    }
                ]
            }
        ]
    )

    result = split_canonical_sections(content, llm_client=fake_llm)

    assert "![](images/figure_1.png)" in result.blocks["introduction"]
    assert "> Figure 1: Intro overview." in result.blocks["introduction"]
    assert "Prior work evidence." in result.blocks["related_work"]
    assert "Reference text should be removed" not in "\n".join(result.blocks.values())
    assert result.report["llm"]["coverage"]["initial_uncovered_line_count"] > 0
    assert result.report["llm"]["coverage"]["filled_range_count"] > 0
    assert result.report["llm"]["coverage"]["final_uncovered_line_count"] == 0


def test_llm_section_split_uses_related_view_from_intro_when_llm_selects_it() -> None:
    content = "\n".join(
        [
            "# Demo Paper",
            "",
            "## 1 Introduction",
            "We study efficient adaptation for large models.",
            "",
            (
                "Existing approaches [1, 2] fine-tune all parameters. However, these "
                "previous methods require extensive storage and lack deployment efficiency."
            ),
            "",
            "## 2 Method",
            "Our method trains a compact adapter.",
        ]
    )
    fake_llm = SequenceLLM(
        [
            {
                "sections": [
                    {
                        "section_key": "introduction",
                        "start_line": 1,
                        "end_line": 6,
                        "confidence": 0.9,
                        "rationale": "The LLM selected Introduction as the primary section.",
                    },
                    {
                        "section_key": "related_work",
                        "start_line": 6,
                        "end_line": 6,
                        "confidence": 0.9,
                        "rationale": "The LLM selected the intro paragraph as prior-work discussion.",
                    },
                    {
                        "section_key": "method",
                        "start_line": 8,
                        "end_line": 9,
                        "confidence": 0.9,
                        "rationale": "Method section.",
                    },
                ]
            }
        ]
    )

    result = split_canonical_sections(content, llm_client=fake_llm)

    assert "Existing approaches [1, 2]" in result.blocks["introduction"]
    assert "Existing approaches [1, 2]" in result.blocks["related_work"]
    assert any(
        record["section_key"] == "related_work" and record["source"] == "llm"
        for record in result.report["llm"]["accepted"]
    )


def test_llm_section_split_merges_background_excludes_references_and_keeps_appendix() -> None:
    content = "\n".join(
        [
            "# Demo Paper",
            "",
            "## 1 Introduction",
            "Intro motivation.",
            "![Intro](figures/figure_1.png)",
            "> **图注**：Figure 1: Problem overview.",
            "## 2 Related Work",
            "Prior work evidence.",
            "## 3 Model Architecture",
            "Method body.",
            "## 4 Evaluation",
            "Experiment body.",
            "## 5 Conclusion",
            "Conclusion body.",
            "## References",
            "[1] Reference text should be removed.",
            "## A Additional Experiments",
            "Appendix experiment body.",
            "![Appendix](figures/figure_a1.png)",
            "> **图注**：Figure A.1: Appendix figure.",
        ]
    )
    fake_llm = SequenceLLM(
        [
            {
                "sections": [
                    {
                        "section_key": "introduction",
                        "start_line": 3,
                        "end_line": 6,
                        "confidence": 0.95,
                        "rationale": "Introduction is front matter and motivation.",
                    },
                    {
                        "section_key": "background",
                        "start_line": 7,
                        "end_line": 8,
                        "confidence": 0.95,
                        "rationale": "Related Work is merged into background.",
                    },
                    {
                        "section_key": "method",
                        "start_line": 9,
                        "end_line": 10,
                        "confidence": 0.9,
                        "rationale": "Model Architecture is the method.",
                    },
                    {
                        "section_key": "experiment",
                        "start_line": 11,
                        "end_line": 12,
                        "confidence": 0.9,
                        "rationale": "Evaluation is the experiment.",
                    },
                    {
                        "section_key": "experiment",
                        "start_line": 17,
                        "end_line": 20,
                        "confidence": 0.9,
                        "rationale": "Appendix contains additional experiments.",
                    },
                    {
                        "section_key": "conclusion",
                        "start_line": 13,
                        "end_line": 14,
                        "confidence": 0.9,
                        "rationale": "Conclusion section.",
                    },
                    {
                        "section_key": "appendix",
                        "start_line": 15,
                        "end_line": 20,
                        "confidence": 0.9,
                        "rationale": "Appendix after references remains paper content.",
                    },
                ]
            }
        ]
    )

    result = split_canonical_sections(content, llm_client=fake_llm)

    assert result.report["used_llm"] is True
    assert "Intro motivation." in result.blocks["introduction"]
    assert "Prior work evidence." in result.blocks["related_work"]
    assert "Reference text should be removed" not in result.blocks["appendix"]
    assert "Appendix experiment body." in result.blocks["appendix"]
    assert "Appendix experiment body." in result.blocks["experiment"]
    assert "figures/figure_a1.png" in result.blocks["appendix"]


def test_note_generation_renders_llm_list_blocks_as_markdown_bullets() -> None:
    fake_llm = SequenceLLM(
        [
            {
                "blocks": {
                    "research_question": "Why efficient adaptation matters.",
                    "core_method": "LoRA freezes W0 and trains low-rank adapters.",
                    "main_contributions": [
                        "Reduces trainable parameters.",
                        "Keeps inference latency unchanged.",
                    ],
                    "experiment_summary": "Evaluated on GLUE and generation tasks.",
                    "limitations": "Task batching with merged weights is non-trivial.",
                }
            }
        ]
    )
    now = utc_now()
    paper = PaperRecord(
        paper_id=1,
        asset_id=1,
        title="Demo Paper",
        authors=["A. Author"],
        year=2024,
        venue="arXiv",
        venue_short="arXiv",
        doi="",
        source_url="",
        pdf_url="",
        category_id=None,
        tags=[],
        paper_stage="parsed",
        download_status="succeeded",
        parse_status="succeeded",
        refine_status="succeeded",
        review_status="pending",
        note_status="empty",
        assets={},
        created_at=now,
        updated_at=now,
    )

    result = generate_paper_note(
        paper=paper,
        sections=[{"title": "Method", "section_key": "method", "content": "Method evidence."}],
        llm_client=fake_llm,
    )

    assert result.source == "llm"
    assert "- Reduces trainable parameters." in result.content
    assert "- Keeps inference latency unchanged." in result.content
    assert "['Reduces trainable parameters." not in result.content


def test_note_generation_deduplicates_renderer_owned_headings() -> None:
    fake_llm = SequenceLLM(
        [
            {
                "blocks": {
                    "paper_overview": "## 文章摘要\n\n### 文章摘要\nOverview body.",
                    "method": "## 本文方法\n\n## Module\nMethod body.",
                }
            }
        ]
    )
    now = utc_now()
    paper = PaperRecord(
        paper_id=1,
        asset_id=1,
        title="Heading Paper",
        authors=["A. Author"],
        year=2024,
        venue="arXiv",
        venue_short="arXiv",
        doi="",
        source_url="",
        pdf_url="",
        category_id=None,
        tags=[],
        paper_stage="parsed",
        download_status="succeeded",
        parse_status="succeeded",
        refine_status="succeeded",
        review_status="pending",
        note_status="empty",
        assets={},
        created_at=now,
        updated_at=now,
    )

    result = generate_paper_note(
        paper=paper,
        sections=[{"title": "Method", "section_key": "method", "content": "Method evidence."}],
        llm_client=fake_llm,
    )

    assert result.content.count("## 文章摘要") == 1
    assert result.content.count("## 本文方法") == 1
    assert "### 方法总览" in result.content
    assert "### Module" in result.content
    assert "\n## Module" not in result.content


def test_note_generation_enforces_method_overview_scaffold() -> None:
    fake_llm = SequenceLLM(
        [
            {
                "blocks": {
                    "paper_overview": "Overview.",
                    "terminology_guide": "Terms.",
                    "background_motivation": "Background.",
                    "experimental_setup": "Setup.",
                    "method": (
                        "### Encoder\n"
                        "The encoder builds contextual token representations.\n\n"
                        "### Decoder\n"
                        "The decoder generates output tokens autoregressively."
                    ),
                    "experimental_results": "Results.",
                }
            }
        ]
    )
    now = utc_now()
    paper = PaperRecord(
        paper_id=1,
        asset_id=1,
        title="Transformer Paper",
        authors=["A. Author"],
        year=2017,
        venue="NeurIPS",
        venue_short="NeurIPS",
        doi="",
        source_url="",
        pdf_url="",
        category_id=None,
        tags=[],
        paper_stage="parsed",
        download_status="succeeded",
        parse_status="succeeded",
        refine_status="succeeded",
        review_status="pending",
        note_status="empty",
        assets={},
        created_at=now,
        updated_at=now,
    )

    result = generate_paper_note(
        paper=paper,
        sections=[{"title": "Method", "section_key": "method", "content": "Method evidence."}],
        llm_client=fake_llm,
    )
    method_block = result.content.split("## 本文方法", 1)[1].split("## 实验结果", 1)[0]

    assert method_block.lstrip().startswith("### 方法总览")
    assert "Encoder、Decoder" in method_block
    assert "### Encoder" in method_block


def test_section_markdown_rewrites_figure_paths_for_sections() -> None:
    markdown = "\n".join(
        [
            "## Method",
            "![Overview](images/figure_1.png)",
            "![Local](./images/local.png)",
            "![External](https://example.com/figure.png)",
        ]
    )

    rewritten = _rewrite_section_image_links(markdown)

    assert "![Overview](../images/figure_1.png)" in rewritten
    assert "![Local](../images/local.png)" in rewritten
    assert "![External](https://example.com/figure.png)" in rewritten


def test_note_generation_embeds_resolved_figure_evidence(tmp_path: Path) -> None:
    figure_dir = tmp_path / "parsed" / "images"
    figure_dir.mkdir(parents=True)
    (figure_dir / "figure_1.png").write_bytes(b"fake-image")
    note_path = tmp_path / "note.md"
    fake_llm = SequenceLLM(
        [
            {
                "blocks": {
                    "paper_overview": "Overview.",
                    "terminology_guide": "Not stated in the parsed paper.",
                    "background_motivation": "Background.",
                    "experimental_setup": "Setup.",
                    "method": "Method.\n\n### 图表解读\nFigure 1 shows the method pipeline.",
                    "experimental_results": "Results.",
                }
            }
        ]
    )
    now = utc_now()
    paper = PaperRecord(
        paper_id=1,
        asset_id=1,
        title="Visual Paper",
        authors=["A. Author"],
        year=2024,
        venue="arXiv",
        venue_short="arXiv",
        doi="",
        source_url="",
        pdf_url="",
        category_id=None,
        tags=[],
        paper_stage="sectioned",
        download_status="succeeded",
        parse_status="succeeded",
        refine_status="succeeded",
        review_status="confirmed",
        note_status="empty",
        assets={},
        created_at=now,
        updated_at=now,
    )
    sections = [
        {
            "title": "Method",
            "section_key": "method",
            "content": "\n".join(
                [
                    "## Method",
                    "![](images/figure_1.png)",
                    "Figure 1: Overview of the proposed method.",
                ]
            ),
        }
    ]

    figures = collect_figure_evidence(
        sections,
        note_path=note_path,
        image_base_dirs=[figure_dir],
    )
    result = generate_paper_note(
        paper=paper,
        sections=sections,
        llm_client=fake_llm,
        note_path=note_path,
        image_base_dirs=[figure_dir],
    )

    assert figures[0].image_path == "parsed/images/figure_1.png"
    assert figures[0].role_hint == "method"
    assert result.figure_count == 1
    assert "### 方法总览" in result.content
    assert "![Figure 1](parsed/images/figure_1.png)" in result.content
    assert "> **图注**：Figure 1: Overview of the proposed method." in result.content
    assert "> **阅读角色**：方法主线/架构图" in result.content
    assert "Figure 1 shows the method pipeline." in result.content
    assert "## 关键图表与视觉证据" not in result.content


def test_note_generation_marks_missing_caption_for_review(tmp_path: Path) -> None:
    figure_dir = tmp_path / "parsed" / "images"
    figure_dir.mkdir(parents=True)
    (figure_dir / "figure_1.png").write_bytes(b"fake-image")
    note_path = tmp_path / "note.md"
    sections = [
        {
            "title": "Method",
            "section_key": "method",
            "content": "\n".join(["## Method", "![](images/figure_1.png)"]),
        }
    ]

    figures = collect_figure_evidence(
        sections,
        note_path=note_path,
        image_base_dirs=[figure_dir],
    )

    assert figures[0].caption == "No caption detected in the parsed section."
    assert "图注" in figures[0].review_notes[0]

    rendered = generate_paper_note(
        paper=PaperRecord(
            paper_id=1,
            asset_id=1,
            title="Caption Review Paper",
            authors=["A. Author"],
            year=2024,
            venue="arXiv",
            venue_short="arXiv",
            doi="",
            source_url="",
            pdf_url="",
            category_id=None,
            tags=[],
            paper_stage="sectioned",
            download_status="succeeded",
            parse_status="succeeded",
            refine_status="succeeded",
            review_status="confirmed",
            note_status="empty",
            assets={},
            created_at=utc_now(),
            updated_at=utc_now(),
        ),
        sections=sections,
        llm_client=SequenceLLM([]),
        note_path=note_path,
        image_base_dirs=[figure_dir],
    ).content

    assert ">[!Caution]" in rendered
    assert "> 解析结果没有在图片附近找到可靠图注，需要人工核对原 PDF。" in rendered
