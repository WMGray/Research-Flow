# Paper 端到端流程与表设计

## 目标

Paper 主链路覆盖：

```text
create/import
  -> download/attach PDF
  -> parse MinerU full.md to parsed/raw.md
  -> refine parsed/raw.md with diagnose/repair/verify
  -> split canonical sections
  -> summarize to note.md
  -> extract knowledge/datasets
```

设计原则：

- `biz_paper` 只保存论文业务状态和元信息。
- `asset_registry` / `physical_item` 保存文件级资产。
- `biz_doc_layout` 保存用户可编辑文档，例如 `note.md` 与 `parsed/refined.md`。
- `biz_paper_artifact` 保存 pipeline 每一步的机器产物，例如 `paper.pdf`、`raw.md`、refine JSON、sections。
- `biz_paper_pipeline_run` 保存每次 stage 执行记录，关联 job、输入产物、输出产物、指标和错误。

## API 主链路

| Stage | API | 输入 | 输出 |
| --- | --- | --- | --- |
| create | `POST /api/v1/papers` | title/doi/url/pdf_url/tags | `biz_paper` + 默认 `note/refined` doc |
| download | `POST /api/v1/papers/{paper_id}/download` | Paper 元信息 | `paper.pdf` + `source_pdf` artifact |
| parse | `POST /api/v1/papers/{paper_id}/parse` | `paper.pdf` 或本地 MinerU `full.md` | `parsed/raw.md` + `raw_markdown` artifact |
| refine | `POST /api/v1/papers/{paper_id}/refine-parse` | `parsed/raw.md` | `parsed/refined.md` + refine artifacts |
| review | `submit-review / confirm-review` | refined doc | 人工确认 checkpoint |
| split | `POST /api/v1/papers/{paper_id}/split-sections` | `parsed/refined.md` | `parsed/sections/*.md` |
| summarize | `POST /api/v1/papers/{paper_id}/generate-note` | sections | `note.md` |
| extract | `extract-knowledge / extract-datasets` | note/sections | extraction JSON |

新增便捷入口：

- `POST /api/v1/papers/{paper_id}/pipeline`：按依赖顺序同步推进 `download -> parse -> refine -> split -> summarize`，返回本次串行执行的 job 列表、最终 Paper 状态和停止点。
- `GET /api/v1/papers/{paper_id}/artifacts`：查看 `biz_paper_artifact` 中登记的产物。
- `GET /api/v1/papers/{paper_id}/pipeline-runs`：查看 `biz_paper_pipeline_run` 中的 stage 审计记录。

## 表设计

### `biz_paper`

论文核心状态表。

| 字段 | 说明 |
| --- | --- |
| `asset_id` | Paper 的 asset id，主键 |
| `title/authors/pub_year/venue/doi/source_url/pdf_url/tags` | 论文元信息 |
| `paper_stage` | 当前业务阶段 |
| `download_status` | 下载状态 |
| `parse_status` | 解析状态 |
| `refine_status` | refine 状态 |
| `review_status` | 人工 review 状态 |
| `note_status` | note 生成/修改状态 |

### `biz_doc_layout`

用户可编辑 Markdown 文档映射。

当前 Paper 默认有：

- `doc_role=note` -> `note.md`
- `doc_role=refined` -> `parsed/refined.md`

这些文档支持 `base_version` 乐观锁。

### `biz_paper_artifact`

Paper pipeline 产物表。每个 `paper_id + artifact_key` 唯一，重复生成会更新版本。

| 字段 | 说明 |
| --- | --- |
| `artifact_id` | 产物记录主键 |
| `paper_id` | 关联 `biz_paper.asset_id` |
| `asset_id` | 关联 `asset_registry.asset_id` |
| `artifact_key` | 稳定产物 key，例如 `source_pdf`、`raw_markdown` |
| `artifact_type` | `pdf`、`markdown`、`json` 等 |
| `stage` | `download`、`parse`、`refine`、`split`、`summarize` |
| `storage_path` | 当前产物路径 |
| `content_hash` | 文件 hash |
| `file_size` | 文件大小 |
| `version` | 产物版本 |
| `metadata` | JSON 字符串，保存模式、warning、prompt、统计信息 |

当前 artifact key：

- `source_pdf`
- `raw_markdown`
- `refined_markdown`
- `refine_line_index`
- `refine_diagnosis`
- `refine_patches`
- `refine_patch_apply_report`
- `refine_prompt_context`
- `refine_verify`
- `section_related_work`
- `section_method`
- `section_experiment`
- `section_conclusion`
- `note_markdown`

### `biz_paper_pipeline_run`

每次 pipeline stage 的运行记录。

| 字段 | 说明 |
| --- | --- |
| `run_id` | pipeline run id |
| `paper_id` | Paper id |
| `job_id` | 对应 `jobs.job_id` |
| `stage` | `download/parse/refine/split/summarize` |
| `status` | `succeeded/failed/...` |
| `input_artifacts` | JSON array |
| `output_artifacts` | JSON array |
| `metrics` | JSON object，例如 char count、section count、verify status |
| `error` | 失败时的结构化错误 |

## 下载策略

Paper API 的 download stage 支持三种模式：

- `attached_local_pdf`：`pdf_url` 或 `source_url` 指向本地 PDF，直接复制到 `paper.pdf`。
- `gpaper`：设置 `RFLOW_ENABLE_NETWORK_PAPER_DOWNLOAD=1` 后调用 `PaperDownloadService` / gPaper 下载。
- `metadata_stub`：开发环境没有网络或未启用下载时生成最小 PDF stub，使后续 pipeline 可被本地 smoke 测试覆盖。

真实生产下载应启用 `RFLOW_ENABLE_NETWORK_PAPER_DOWNLOAD=1`，并配置 gPaper 所需 API key / email。

## 解析策略

parse stage 的优先级：

1. 使用本地已有 MinerU Markdown：
   - `parsed/mineru/full.md`
   - `mineru/full.md`
   - `parsed/full.md`
   - `full.md`
2. 如果存在 `paper.pdf` 且 MinerU token 已配置，调用 `PDFParserService.extract_raw_markdown()`。
3. 否则生成 `metadata_fallback` raw markdown，保证开发环境可跑通状态机。

parse 只产出 `parsed/raw.md`，不做总结，不直接拆 section，不让 LLM 重写整篇论文。

## Refine 策略

refine stage 使用：

- `paper_refine_parse.diagnose`
- `paper_refine_parse.repair`
- `paper_refine_parse.verify`

对应产物写入：

```text
parsed/refine/line_index.json
parsed/refine/diagnosis.json
parsed/refine/patches.json
parsed/refine/patch_apply_report.json
parsed/refine/prompt_context.json
parsed/refine/verify.json
parsed/refined.md
```

本地 preservation checks 会拦截 citation、number、formula、image link 和异常长度变化。LLM verifier 的 `pass` 不能覆盖本地失败。LLM 控制 JSON 解析失败时，refine 会进入 warning/no-op：保留 raw markdown、不应用不可信 patch、写入 warning artifacts，并允许后续 split / summarize 继续。

## Summary 策略

summarize stage 使用 `paper_note_summarizer` prompt：

note 写回策略：

- `note_status=empty/clean_generated`：直接写入新的 managed blocks。
- `note_status=user_modified/merged`：只替换已有 RF managed blocks，缺失 block 追加到文末，保留用户手写内容。
- `note_status=conflict_pending`：拒绝覆盖，返回 failed job。
- 若尚未执行 `split-sections`，`generate-note` 返回 `PAPER_SECTIONS_MISSING`，避免基于空 sections 生成虚假总结。

- 输入 Paper metadata 与 canonical sections。
- LLM 必须返回 JSON blocks。
- 后端渲染为带 `RF:BLOCK_START/END` 的 `note.md`。
- LLM 不可用时使用 deterministic fallback，仍保持 managed block 结构。

对应 prompt：

- `backend/config/prompts/paper_note_generate.md`

## 当前限制

- Paper API job 仍是同步执行并立即落库，不是真正异步 worker。
- `metadata_stub` 与 `metadata_fallback` 是开发 fallback，不代表真实论文内容。
- 复杂 reading-order 修复尚未支持 `move_span` 自动应用，应先进入 review。
- Knowledge/Dataset extraction 当前仍是占位 JSON，后续应接 LLM extraction prompt 与结构化表。
