# PDF 解析与 LLM 优化设计

## 1. 文档目标

本文档定义 Research-Flow 后端中 PDF 解析与 LLM 优化解析的目标架构。当前设计以 MinerU 解析产物 `full.md` 为主要输入，通过受约束的 LLM workflow 修复解析不准确带来的结构问题，最终生成可人工审查、可追溯、可进入章节切分的 `parsed/refined.md`。

本文档重点回答：

- 为什么以 MinerU `full.md` 为主输入，而不是直接从 PDF 或自由 Markdown 重写开始
- LLM 在解析优化中具体负责什么、不负责什么
- 如何处理章节划分不明确、图文混排、章节错乱等通用问题
- 如何让 LLM 优化结果可验证、可回滚、可人工审查
- 如何接入现有 `Agno`、`SkillBinding`、`PromptTemplate`、`Job` 与文件系统产物

## 2. 核心原则

### 2.1 `full.md` 是主输入

MinerU 已经完成了 PDF 到 Markdown 的第一轮解析，`full.md` 通常保留了正文、标题、图表引用、公式、表格和部分布局信息。后续 LLM 优化应优先消费 `full.md`，而不是重新从 PDF 自由生成论文内容。

原因：

- `full.md` 是可读文本，适合 LLM 做结构诊断和局部修复。
- `full.md` 可落盘、可 diff、可 hash，方便审计和版本管理。
- PDF 视觉信息只作为辅助证据，不作为默认主路径。

### 2.2 LLM 不做全文自由重写

LLM 的目标不是“润色论文”，也不是生成新的学术表达，而是：

- 诊断 MinerU 解析中的结构问题
- 提出局部 patch
- 修复 Markdown 层级、段落断裂、caption 混入正文、章节顺序异常等问题
- 标记低置信度区域，进入人工审查

LLM 不应：

- 总结、翻译或扩写论文内容
- 删除 citation、数字、公式、表格、算法步骤
- 凭空补全 MinerU 没有解析出的图表或文字
- 直接输出整篇最终 `refined.md`

### 2.3 程序负责合并与校验

LLM 输出的是结构化诊断和 patch，最终 `refined.md` 由程序根据 patch 应用结果编译生成。

这样做的好处：

- 每个修改都有来源范围和理由
- patch 可回滚、可重跑、可人工确认
- verifier 可以针对修改前后做机械检查
- 避免大模型一次性重写全文带来的内容丢失和 hallucination

## 3. 总体流程

目标流程如下：

```text
paper.pdf
  -> MinerU parse
  -> parsed/raw.md                  # MinerU full.md
  -> parsed/refine/diagnosis.json
  -> parsed/refine/patches.json
  -> parsed/refine/verify.json
  -> parsed/refined.md
  -> human review
  -> parsed/sections/*.md
```

对应语义：

1. `parse`：调用 MinerU，保存 `full.md` 为 `parsed/raw.md`。
2. `diagnose`：LLM 读取 line-numbered `raw.md`，输出结构化问题清单。
3. `repair`：LLM 只针对诊断出的局部 span 生成 patch。
4. `apply`：程序应用 patch，生成 `refined.md`。
5. `verify`：规则和 LLM verifier 检查修改是否破坏原文事实与结构。
6. `review`：用户审查 `refined.md` 和低置信度问题。
7. `split`：确认后再生成 canonical sections。

## 4. 产物布局

建议目录结构：

```text
parsed/
  raw.md
  refined.md
  refine/
    line_index.json
    diagnosis.json
    patches.json
    patch_apply_report.json
    verify.json
    review_items.json
  sections/
    related_work.md
    method.md
    experiment.md
    conclusion.md
```

### 4.1 `line_index.json`

记录 `raw.md` 的行号、内容 hash 和基础统计，供 LLM patch 使用。

关键字段：

- `source_path`
- `source_hash`
- `line_count`
- `char_count`
- `generated_at`

### 4.2 `diagnosis.json`

LLM 诊断结果，不直接修改正文。

建议结构：

```json
{
  "source_hash": "sha256",
  "issues": [
    {
      "issue_id": "issue_001",
      "type": "heading_ambiguous",
      "start_line": 120,
      "end_line": 126,
      "severity": "medium",
      "confidence": 0.78,
      "description": "A likely section heading is formatted as a normal paragraph.",
      "suggested_action": "repair_heading"
    }
  ]
}
```

### 4.3 `patches.json`

LLM 只输出局部 patch。

建议结构：

```json
{
  "source_hash": "sha256",
  "patches": [
    {
      "patch_id": "patch_001",
      "issue_id": "issue_001",
      "op": "replace_span",
      "start_line": 120,
      "end_line": 126,
      "replacement": "## 3 Experiments\n\n...",
      "confidence": 0.84,
      "preservation_checks": {
        "citations_preserved": true,
        "numbers_preserved": true,
        "formula_blocks_preserved": true
      }
    }
  ]
}
```

允许的 patch 类型：

- `replace_span`
- `move_span`
- `merge_paragraphs`
- `split_caption`
- `normalize_heading`
- `mark_needs_review`

默认只自动应用高置信度 patch；低置信度 patch 写入 `review_items.json`。

### 4.4 `verify.json`

记录程序和 LLM verifier 的检查结果。

建议检查项：

- citation 数量是否异常减少
- 数字、百分比、指标是否异常减少
- 公式块、表格块、caption 是否保留
- `refined.md` 是否异常短于 `raw.md`
- heading tree 是否存在明显断裂
- patch 是否越界或重叠
- 是否有低置信度问题需要人工确认

## 5. 通用问题处理策略

### 5.1 章节划分不明确

不要在 parse 阶段强行切 section。LLM 先做 heading 诊断：

- 标记疑似标题
- 给出 heading / subheading / paragraph / ambiguous 判断
- 输出置信度
- 低置信度区域保留原文并进入人工审查

章节切分只在 `refined.md` 通过验证并经人工确认后执行。

### 5.2 图和文字没有明显分层

LLM 可以修复 Markdown 表达，但不应凭空恢复缺失图片。

处理策略：

- 若 caption 混入正文，生成 `split_caption` patch。
- 若 figure/table caption 与正文相邻但归属不清，写入 `review_items.json`。
- 若 MinerU content list 或图片目录中能定位图表，后续可结合 bbox / page image 做增强绑定。
- 若无法确认图文关系，不自动移动大段正文。

### 5.3 章节错乱

章节错乱可能来自 OCR reading order、双栏顺序、caption 插入或标题识别失败。

处理策略：

- LLM 可以提出 `move_span`，但必须给出原始行范围、目标位置和置信度。
- 程序只自动应用高置信度且不重叠的移动。
- 对大范围重排保持保守，优先进入人工审查。
- verifier 检查 heading 编号和主题跳转是否仍异常。

## 6. Agno 接入方式

建议将 `paper_refine_parse` 拆成三个子场景：

| 场景 | 说明 | 输入 | 输出 |
|------|------|------|------|
| `paper_refine_parse.diagnose` | 诊断 `raw.md` 结构问题 | line-numbered Markdown | `diagnosis.json` |
| `paper_refine_parse.repair` | 针对 issue 生成 patch | issue span + 局部上下文 | `patches.json` |
| `paper_refine_parse.verify` | 检查 patch 后结果 | raw/refined/report 摘要 | `verify.json` |

Agno 的职责：

- 根据 `SkillBinding` 选择 agent profile、provider、prompt template
- 将诊断、修复、验证三个阶段编排为同一个 workflow
- 对每个 LLM 调用记录 `llm_run_id`
- 将失败信息写入 job result 和 `refine_report`

Agno 不直接负责：

- 应用 patch
- 重排全文
- 覆盖人工确认后的文档
- 替代 verifier 的机械一致性检查

## 7. Prompt 设计要求

### 7.1 Diagnose prompt

要求：

- 输入完整 line-numbered `raw.md`
- 只输出 JSON
- 不输出修复后的正文
- issue 必须引用行号范围
- 对低置信度问题使用 `confidence < 0.75`

### 7.2 Repair prompt

要求：

- 输入单个 issue 或少量相关 issue
- 输入局部上下文，不输入全文
- 输出 patch JSON
- replacement 中不得新增原文没有的事实
- 必须声明 citation、数字、公式是否保留

### 7.3 Verify prompt

要求：

- 输入 raw/refined 的摘要、patch 列表和规则检查结果
- 只判断是否存在结构性风险
- 不重写正文
- 给出 `pass / warning / fail`

## 8. 自动应用与人工审查策略

### 8.1 自动应用条件

patch 同时满足以下条件才允许自动应用：

- `confidence >= 0.85`
- patch 行范围没有与其他 patch 冲突
- patch 不删除 citation、公式、表格和关键数字
- patch 后文本长度没有异常缩水
- patch 类型在允许自动应用白名单内

### 8.2 人工审查条件

以下情况必须进入人工审查：

- 大范围 `move_span`
- 图文归属不明确
- heading 判断低置信度
- patch 可能删除内容
- verifier 返回 `fail`
- `refined.md` 与 `raw.md` 差异比例异常

人工审查对象包括：

- `parsed/refined.md`
- `parsed/refine/review_items.json`
- `parsed/refine/verify.json`

## 9. 与 Paper 主链路的关系

目标链路应调整为：

```text
create paper
  -> download / attach PDF
  -> parse PDF to raw.md
  -> LLM diagnose + repair + verify
  -> refined.md waiting_review
  -> user confirm
  -> split sections
  -> generate note
  -> extract Knowledge / Dataset
```

关键约束：

- `split-sections` 的输入必须是人工确认后的 `refined.md`。
- `generate-note` 不应直接消费未确认的 `refined.md`。
- 如果重新执行 `parse` 或 `refine-parse`，下游 `sections`、`note`、Knowledge / Dataset 状态应失效或要求显式确认。

## 10. 当前实现差距

当前代码已有：

- `PDFParserService`
- MinerU 配置与测试
- `paper_refine_parse` skill binding 雏形
- `parsed/raw.md` 与 `parsed/refined.md` 路由
- `submit-review` / `confirm-review`

尚需补齐：

- 将 MinerU `full.md` 真正接入 PaperService 的 `parse`
- `diagnosis.json`、`patches.json`、`verify.json` 产物
- patch apply engine
- verifier
- 低置信度 review item 展示
- `SkillBinding` 拆分为 diagnose / repair / verify
- 状态机前置约束和下游失效策略

## 11. 第一阶段落地建议

第一阶段不追求视觉级 PDF reconstruction，先完成基于 `full.md` 的可靠优化闭环：

1. `parse` 保存 MinerU `full.md` 为 `parsed/raw.md`。
2. 为 raw markdown 生成 line index 和 hash。
3. `diagnose` 输出问题清单。
4. `repair` 只针对问题 span 输出 patch。
5. 程序应用高置信度 patch。
6. verifier 生成报告。
7. `refined.md` 进入人工审查。

若遇到 `full.md` 无法判断的问题，再标记 `needs_pdf_context`，后续结合 content list、bbox 或 page image 扩展。

---

*文档版本：v0.1 | 最后更新：2026-04-26*
