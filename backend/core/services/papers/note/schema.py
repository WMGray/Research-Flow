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
        title="文章摘要",
        min_chars=600,
        max_tokens=3500,
        section_keys=frozenset({"related_work", "method", "experiment", "conclusion"}),
        instruction=(
            "覆盖文章摘要、题名、作者、年份、会议/期刊全称与缩写、领域定位。"
            "领域定位使用“大领域 > 细分领域”格式；无法确认时保守说明。"
        ),
    ),
    NoteBlockSpec(
        block_id="terminology_guide",
        title="缩写与术语解释",
        min_chars=1200,
        max_tokens=4500,
        section_keys=frozenset({"related_work", "method", "experiment"}),
        instruction=(
            "按任务定义类、模型与架构类、特征表征类、评价指标类组织术语。"
            "每个术语不少于 50 字，只解释原文明确出现或通用且必要的术语。"
        ),
    ),
    NoteBlockSpec(
        block_id="background_motivation",
        title="深度背景与动机分析",
        min_chars=1600,
        max_tokens=5000,
        section_keys=frozenset({"related_work", "conclusion"}),
        instruction=(
            "结合 Introduction、Background、Related Work 梳理研究现状，"
            "再用表格给出痛点、本文切入点、实现技术与实现效果的映射。"
        ),
    ),
    NoteBlockSpec(
        block_id="experimental_setup",
        title="实验设置",
        min_chars=900,
        max_tokens=3500,
        section_keys=frozenset({"experiment", "appendix"}),
        instruction=(
            "提取数据集、输入特征、训练设置、超参数、硬件与实现细节。"
            "Appendix 中的超参数和额外设置应整合到本节小标题中。"
        ),
    ),
    NoteBlockSpec(
        block_id="method",
        title="本文方法",
        min_chars=2600,
        max_tokens=6500,
        section_keys=frozenset({"method", "appendix"}),
        instruction=(
            "必须以 `### 方法总览` 开头，先用总-分结构概括本文方法包含哪些模块、"
            "模块之间的数据流/逻辑关系、每个模块的作用，以及关键 Figure 如何帮助理解整体框架。"
            "随后按模块展开，模块名必须和总览一致；每个模块包含背景、原理内容、公式解析和作用。"
            "原理内容要解释背景、核心思想、流程和步骤关系，不能只围绕公式。"
            "若 Appendix 中有方法补充、证明或实现细节，也作为本节小标题纳入。"
        ),
    ),
    NoteBlockSpec(
        block_id="experimental_results",
        title="实验结果",
        min_chars=2200,
        max_tokens=5000,
        section_keys=frozenset({"experiment", "appendix", "conclusion"}),
        instruction=(
            "严格遵循原文实验章节、子章节标题、术语与顺序。"
            "主实验、消融实验、附录实验、局限性和未来工作都放在本节内部小标题中，"
            "不得把 Appendix 子节提升为顶层 note 章节。"
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
    "limitations": "limitations",
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
