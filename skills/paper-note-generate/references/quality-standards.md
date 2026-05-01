# Note Quality Standards

Per-block minimums, required items, and forbidden patterns for the paper-style note architecture.

## Contents

- 1. paper_overview / 摘要信息
- 2. terminology_guide / 术语
- 3. background_motivation / 背景动机
- 4. method / 方法
- 5. experimental_results / 实验/结果
- 6. conclusion_limitations / 结论局限
- General Rules

## 1. paper_overview / 摘要信息 (minimum 600 characters)

**Required:**
- Paper identity information: title, authors, year, venue full name and abbreviation, DOI
- Domain positioning: `大领域 > 细分领域`, supported by paper content
- Abstract rewritten in Chinese, covering problem, method, results, and contribution
- Explicit gap notes when venue full name, DOI, or abstract evidence is missing

**Forbidden:**
- Repeating `## 摘要信息`
- Copying the abstract verbatim without reorganization
- Writing a full-paper section-by-section summary instead of identity + abstract

## 2. terminology_guide / 术语 (minimum 1200 characters)

**Required:**
- Organized by four categories: task definitions, model and architecture terms, feature representations, evaluation metrics
- Each term explained in at least 50 Chinese characters
- Terms listed in first-appearance order in the paper
- Clear distinction between general concepts and paper-specific constructs

**Forbidden:**
- Explaining a paper-invented module as if it were a general concept
- Padding word count when evidence is insufficient

## 3. background_motivation / 背景动机 (minimum 1600 characters)

**Required:**
- Research status and positioning before motivation mapping
- At least three prior works or representative methods discussed, each at least 50 Chinese characters
- Pain-point mapping table: `| 核心痛点 | 本文切入点 | 对应实现技术 | 实现效果 |`
- Integration of Introduction and Related Work instead of separate shallow summaries

**Forbidden:**
- Treating introduction and related_work as unrelated summaries
- Replacing motivation analysis with a generic field description

## 4. method / 方法 (minimum 2600 characters)

**Required:**
- Must begin with `### 方法总览`
- Each module follows: background -> principles -> formulas -> role
- Every formula variable explained one by one with dimensions when provided
- Concrete numbers (dimensions, frame counts, ratios, thresholds, accuracy scores)
- `<!-- figure -->` markers placed at natural embedding points (after overview, after sub-component explanations)
- Every method/problem figure analyzed with the three-part rule (what it shows, how to read it, why it matters)

**Forbidden:**
- Placing formulas without variable explanations
- Summarizing an entire module in one sentence
- Skipping principles and jumping directly to formulas
- Vague phrasing ("achieved good results", "significant improvement" -> write specific numbers)
- Writing `![...](...)` Markdown or `### 关键方法图表` headings in body text

## 5. experimental_results / 实验/结果 (minimum 2200 characters)

**Required:**
- Starts with `### 实验设置`
- Datasets: source, scale, content, split rules; note each missing item explicitly
- Features: input type, extraction method, upstream model, feature type
- Training settings: learning rate, epochs, batch size, optimizer, hardware, seed
- Organized by the paper's original experiment section order and subsection headings
- Main results and ablation studies separated
- Every Table/Figure citation includes accurate numbering and specific numbers
- Ablation: for each subsection, include study object, setup, comparison, result, and author conclusion
- `### 附录证据` for supplementary experiments from appendix

**Forbidden:**
- Omitting hyperparameters present in appendix
- Promoting appendix subsections (e.g. `F.1`) to top-level experiment sections
- Reorganizing experiment categories arbitrarily
- Writing "significant improvement" without metrics

## 6. conclusion_limitations / 结论局限 (minimum 1000 characters)

**Required:**
- `### 结论`: core findings, contributions, and applicable scope grounded in method/result evidence
- `### 局限性`: explicit limitations, assumptions, failure modes, scope constraints, and threats
- `### 未来工作与开放问题`: future work or open questions stated by the paper or directly implied by explicit limitations
- Preserve original `> [!note]` callout format when the parsed conclusion contains note-style limitation text

**Forbidden:**
- Guessing limitations not stated or supported by the paper
- Duplicating the experiment/result section instead of synthesizing final claims
- Ending without explicit limitations or an evidence-gap statement

## General Rules

- Chinese prose throughout; model names, method names, dataset names, metrics, formula numbers remain in English
- Citations, formula blocks, Table/Figure numbers, and dataset names must not be cross-referenced to wrong sections
- When evidence is insufficient, write `解析内容未说明。`
- If uncertainty is due to parse quality, figure-text mismatch, or section disorder, use `>[!Caution]` callout
- Blocks follow the fixed reading order: 摘要信息 -> 术语 -> 背景动机 -> 方法 -> 实验/结果 -> 结论局限
