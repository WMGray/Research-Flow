# Figure Handling — Note Generation

Defines the full chain from figure collection to inline note.md embedding, and the LLM analysis rules for each figure role.

Chinese text in code blocks and examples shows the expected LLM output format (the note body is Chinese). The surrounding prose is English.

## Contents

- Backend Pipeline — collection, role classification, sorting, inline embedding
- LLM Figure Analysis Rules — marker placement, three-part analysis, citation format

## Backend Pipeline (implemented in `visuals.py`)

### Collection

`collect_figure_evidence()` scans all six sections for `![...](...)` Markdown image links. Each figure records: `figure_id`, `section_key`, `image_path`, `caption`, `role_hint`, `review_notes`.

### Role Classification

`_figure_role_hint()` assigns one of four roles based on keywords in section, caption, and alt text:

| Role | Trigger Keywords | Destination Block |
|------|-----------------|-------------------|
| `method` | overview, pipeline, framework, architecture, model, module, workflow | `method` |
| `problem` | problem, task, motivation, setting | `method` |
| `result` | accuracy, result, experiment, evaluation, benchmark, ablation, performance, comparison | `experimental_results` / 实验/结果 |
| `support` | (default when no keywords match) | `experimental_results` / 实验/结果 |

### Sorting and Limit

Figures are sorted by priority: `method > problem > result > support`. Maximum 8 figures are retained (`MAX_FIGURE_EVIDENCE`).

### Inline Embedding

`_embed_figures_inline()` replaces `<!-- figure -->` markers in LLM-generated text with the next available figure for that block. Each figure is rendered as inline Markdown:

```
![Figure X](relative/path)

> **图注**：caption text
> **来源章节**：section title
> **阅读角色**：role description
```

If the LLM text has no `<!-- figure -->` markers, figures are appended at block-end (backward compatible). Markers in excess of available figures are removed silently.

### Missing Caption Handling

`_figure_review_notes()` automatically generates `>[!Caution]` when:
- No caption is found within 3 lines of the image in the source section
- The image path cannot be resolved to a local file

## LLM Figure Analysis Rules

### `<!-- figure -->` Marker Placement

The LLM controls where figures appear by placing markers:

- **method block**: one marker after the method overview paragraph (for architecture overview figures), and one marker after each sub-component explanation that a figure illustrates.
- **experimental_results block (实验/结果)**: one marker before or after the analysis paragraph discussing that figure.
- Skip the marker entirely if the figure content cannot be understood — the backend will append it at block-end.
- One marker per figure, in the order figures appear in `{{figure_context}}`.

### Method Block — Three-Part Analysis

For each method/problem figure, write the three-part analysis around the `<!-- figure -->` marker:

1. **What it shows** (1-2 sentences)
   - Figure type: architecture diagram / flowchart / module diagram / comparison chart
   - Core components or information dimensions visible
   - Example: "图 2 展示了 EgoVideo 的整体架构，包含视觉编码器、运动适配器和文本编码器三条分支。"

2. **How to read it** (2-3 sentences)
   - Data flow direction (input -> processing -> output)
   - Key symbols, colors, arrow meanings
   - Connection relationships between modules
   - Example: "左侧为低帧率主干路径（4 帧输入），右侧为高帧率适配器路径（16 帧输入）。箭头表示特征流向：视觉编码器输出分两路，分别进入主干和适配器，最终通过拼接融合为统一的视觉表示。"

3. **Why it matters** (1-2 sentences)
   - Relationship to the paper's core contribution
   - What readers would struggle to understand without this figure
   - Example: "此图是理解 EgoVideo 双分支协同训练策略的唯一可视化入口，清楚展示了模型如何以低帧率主干配合高帧率适配器兼顾领域适应与细节捕捉。"

### Experimental Results Block (实验/结果) — Figure Analysis

For each result/support figure, placed around a `<!-- figure -->` marker:
1. State the Table/Figure number accurately.
2. Explain metric changes with specific numbers (not "significantly improved").
3. State the experimental conditions (dataset, setup, comparison target).
4. If from an Ablation Study, explain the ablation target and conclusion.

### Missing Caption

When the figure evidence shows `caption: "No caption detected..."`:
- Append at the end of the figure analysis:
  ```
  >[!Caution] 此图图注缺失，以上分析基于图片内容和上下文章节推断，需要人工核对原 PDF 确认图表准确含义。
  ```
- If the figure content cannot be understood at all, skip the `<!-- figure -->` marker for that figure.

### Citation Format

- In body text: `（图 N）` or `（见图 N）`
- Do not write `![...](...)` image Markdown — the renderer inserts it
- Do not write `### 关键方法图表` or `### 实验与附录图表证据` headings — the renderer handles placement
- Figures arrive sorted by role priority (method > problem > result > support); place markers in that order
