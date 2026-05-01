from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class NoteBlockSpec:
    block_id: str
    title: str
    min_chars: int
    max_tokens: int
    section_keys: frozenset[str]
    instruction: str


NOTE_BLOCK_SPECS: tuple[NoteBlockSpec, ...] = (
    NoteBlockSpec(
        block_id="paper_overview",
        title="摘要信息",
        min_chars=600,
        max_tokens=3500,
        section_keys=frozenset({"introduction", "related_work", "conclusion"}),
        instruction=(
            "This is the abstract-information block: start with paper identity, then rewrite "
            "the abstract in Chinese. Include title, authors, year, venue/journal full name "
            "and abbreviation, DOI, and domain positioning. Use the format "
            "`大领域 > 细分领域` for domain positioning. The abstract rewrite should cover "
            "research problem, core method, experimental conclusion, and main contribution, "
            "while staying under 80% of the original abstract length."
        ),
    ),
    NoteBlockSpec(
        block_id="terminology_guide",
        title="术语",
        min_chars=1200,
        max_tokens=4500,
        section_keys=frozenset({"introduction", "related_work", "method", "experiment"}),
        instruction=(
            "Organize terms into task definitions, model/architecture terms, feature "
            "representations, and evaluation metrics. Each term explanation must be at "
            "least 50 Chinese characters. Explain only terms explicitly used by the paper "
            "or general concepts needed for reading. List terms in first-appearance order "
            "to prepare later background, method, and experiment discussion."
        ),
    ),
    NoteBlockSpec(
        block_id="background_motivation",
        title="背景动机",
        min_chars=1600,
        max_tokens=5000,
        section_keys=frozenset({"introduction", "related_work"}),
        instruction=(
            "Use Introduction, Background, and Related Work to explain research status, "
            "representative prior routes, their limitations, and the paper's motivation. "
            "Then provide a Markdown table mapping pain points to the paper's entry point, "
            "implementation technique, and achieved effect."
        ),
    ),
    NoteBlockSpec(
        block_id="method",
        title="方法",
        min_chars=2600,
        max_tokens=6500,
        section_keys=frozenset({"method", "appendix"}),
        instruction=(
            "Start with `### 方法总览`: one paragraph listing all module names, data-flow "
            "relationships, module roles, and key method figure IDs. Place the architecture "
            "overview `<!-- figure -->` marker after the overview. Organize each module as "
            "`#### N. 中文名（English Name）`, then `##### 0. 背景` -> `##### 1. 原理内容`. "
            "For each sub-component, use four elements: Chinese narrative "
            "(what/input/output/concrete numbers) -> verbatim formula (`$$...$$`) -> "
            "symbol-by-symbol variable explanation (meaning/dimension/physical significance) "
            "-> linkage to the next step. Analyze each method/problem figure with the "
            "three-part rule: what it shows -> how to read it -> why it matters. Include "
            "appendix method supplements, proofs, and implementation details under the "
            "corresponding method headings."
        ),
    ),
    NoteBlockSpec(
        block_id="experimental_results",
        title="实验/结果",
        min_chars=2200,
        max_tokens=5500,
        section_keys=frozenset({"experiment", "appendix"}),
        instruction=(
            "Follow the paper's original experiment section order. Cover experiment setup, "
            "main results, ablations, and appendix experiments. The setup must include "
            "datasets, input features, training settings, hyperparameters, hardware, and "
            "implementation details. Result analysis must cite accurate Table/Figure IDs "
            "and exact metric changes. Integrate appendix hyperparameters, extra settings, "
            "and supplementary experiments under matching internal headings; do not promote "
            "appendix subsections to top-level note blocks."
        ),
    ),
    NoteBlockSpec(
        block_id="conclusion_limitations",
        title="结论局限",
        min_chars=1000,
        max_tokens=3500,
        section_keys=frozenset({"experiment", "appendix", "conclusion"}),
        instruction=(
            "Synthesize the paper's Conclusion, Discussion, Limitations, Future Work, and "
            "experiment-backed final findings. Output core findings, contribution boundary, "
            "explicit limitations, failure modes, applicable conditions, and future work. "
            "Conclusions must be grounded in paper evidence; when direct evidence is absent, "
            "write `解析内容未提供直接证据。`."
        ),
    ),
)
NOTE_BLOCK_ORDER: tuple[tuple[str, str], ...] = tuple(
    (spec.block_id, spec.title) for spec in NOTE_BLOCK_SPECS
)
LEGACY_BLOCK_MAP: dict[str, str] = {
    "paper_overview": "research_question",
    "method": "core_method",
    "background_motivation": "main_contributions",
    "experimental_results": "experiment_summary",
    "conclusion_limitations": "limitations",
}
_SPEC_BY_ID = {spec.block_id: spec for spec in NOTE_BLOCK_SPECS}


def note_block_spec(block_id: str) -> NoteBlockSpec:
    return _SPEC_BY_ID[block_id]


def note_block_section_keys(block_id: str) -> frozenset[str]:
    spec = _SPEC_BY_ID.get(block_id)
    return spec.section_keys if spec else frozenset()


def note_block_max_tokens(block_id: str) -> int:
    spec = _SPEC_BY_ID.get(block_id)
    return spec.max_tokens if spec else 3500


__all__ = [
    "LEGACY_BLOCK_MAP",
    "NOTE_BLOCK_ORDER",
    "NOTE_BLOCK_SPECS",
    "NoteBlockSpec",
    "note_block_max_tokens",
    "note_block_section_keys",
    "note_block_spec",
]
