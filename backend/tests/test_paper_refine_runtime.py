from __future__ import annotations

import json
from pathlib import Path

from core.config import reset_settings
from core.services.llm.schemas import LLMMessage, LLMRequest, LLMResponse
from core.services.papers.models import PaperRecord, utc_now
from core.services.papers.repository import _rewrite_section_image_links
from core.services.papers.refine import normalize_markdown_structure, refine_markdown
from core.services.papers.refine.parsing import build_line_index, build_line_numbered_markdown
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
        "pdf_markdown_refine_diagnose",
        "pdf_markdown_refine_repair",
        "pdf_markdown_refine_verify",
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
    assert not output_path.exists()
    verify_payload = json.loads((tmp_path / "refine" / "verify.json").read_text(encoding="utf-8"))
    assert any(check["name"] == "citations" and check["status"] == "fail" for check in verify_payload["checks"])


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
    assert [request.feature for request in fake_llm.requests] == ["pdf_markdown_refine_diagnose"]
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
    assert [request.feature for request in bad_llm.requests] == ["pdf_markdown_refine_diagnose"]
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
    assert set(blocks) == {"related_work", "method", "experiment", "conclusion"}


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
            "",
            "### 4.2 Applying Lora to Transformer",
        ]
    )

    normalized, report = normalize_markdown_structure(content, source_hash="hash")

    assert "### 4.2 Applying LoRA to Transformer" in normalized
    assert "Fine-tuning and Low-Rank Adaptation stay as written." in normalized
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
        ]
    )

    normalized, report = normalize_markdown_structure(content, source_hash="hash")

    assert "![](figures/figure_1.png)\n> **图注**：Figure 1: Method overview." in normalized
    assert ">[!Caution]" in normalized
    assert "> 解析结果没有在图片附近找到可靠图注，需要人工核对原 PDF。" in normalized
    assert any(
        operation.operation_type == "format_figure_caption_blockquote"
        for operation in report.operations
    )
    assert any(
        operation.operation_type == "mark_image_caption_needs_review"
        for operation in report.operations
    )


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
    assert fake_llm.requests[0].feature == "paper_section_splitter"
    assert "Proposed Framework" in result.blocks["method"]
    assert "Results" in result.blocks["experiment"]


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
                        "section_key": "related_work",
                        "start_line": 3,
                        "end_line": 6,
                        "confidence": 0.95,
                        "rationale": "Introduction belongs to background.",
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
    assert "Intro motivation." in result.blocks["related_work"]
    assert "Prior work evidence." in result.blocks["related_work"]
    assert "Reference text should be removed" not in result.blocks["appendix"]
    assert "Appendix experiment body." in result.blocks["appendix"]
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
            "![Overview](figures/figure_1.png)",
            "![External](https://example.com/figure.png)",
        ]
    )

    rewritten = _rewrite_section_image_links(markdown)

    assert "![Overview](../figures/figure_1.png)" in rewritten
    assert "![External](https://example.com/figure.png)" in rewritten


def test_note_generation_embeds_resolved_figure_evidence(tmp_path: Path) -> None:
    figure_dir = tmp_path / "parsed" / "figures"
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
                    "![](figures/figure_1.png)",
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

    assert figures[0].image_path == "parsed/figures/figure_1.png"
    assert figures[0].role_hint == "method"
    assert result.figure_count == 1
    assert "### 方法总览" in result.content
    assert "![Figure 1](parsed/figures/figure_1.png)" in result.content
    assert "> **图注**：Figure 1: Overview of the proposed method." in result.content
    assert "> **阅读角色**：方法主线/架构图" in result.content
    assert "Figure 1 shows the method pipeline." in result.content
    assert "## 关键图表与视觉证据" not in result.content


def test_note_generation_marks_missing_caption_for_review(tmp_path: Path) -> None:
    figure_dir = tmp_path / "parsed" / "figures"
    figure_dir.mkdir(parents=True)
    (figure_dir / "figure_1.png").write_bytes(b"fake-image")
    note_path = tmp_path / "note.md"
    sections = [
        {
            "title": "Method",
            "section_key": "method",
            "content": "\n".join(["## Method", "![](figures/figure_1.png)"]),
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
