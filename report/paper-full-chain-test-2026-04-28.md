# Paper 全链路测试报告

测试日期：2026-04-28

## 结论

Paper 本地全链路测试通过。文件能够生成，数据库写入、重复 DOI 拦截、软删除、删除后同 DOI 重新写入、索引与完整性检查均正常。

本次测试使用本地 stub 代替外部网络、MinerU 在线解析和真实 LLM。由于 Paper skills 仍在迭代，本报告只验证链路、文件、格式和数据库行为，不评价生成内容质量。

## 测试范围

- Skill 独立样例：`assets/examples/*.json` 格式解析。
- 后端编译：Paper service、API schema、核心配置。
- Lint：Paper service、API、核心测试。
- Pytest：Paper runtime 与 Paper API 核心用例。
- Paper 全链路：
  - 创建 Paper
  - 重复 DOI 写入拦截
  - download
  - parse
  - refine-parse
  - split-sections
  - generate-note
  - extract-knowledge
  - extract-datasets
  - artifact 文件生成检查
  - pipeline run 记录检查
  - SQLite `integrity_check`
  - SQLite `foreign_key_check`
  - 删除 Paper
  - 删除后使用相同 DOI 重新创建

## 执行结果

| 项目 | 结果 |
|---|---|
| Skill 样例 JSON 解析 | 通过 |
| `compileall` | 通过 |
| `ruff check` | 通过 |
| `pytest tests/test_paper_refine_runtime.py tests/test_papers_api.py` | 通过，`37 passed` |
| `tests/run_paper_pipeline_smoke.py` | 通过 |
| Paper 详细全链路验证 | 通过 |
| `git diff --check` | 通过 |

说明：pytest 首次在沙箱内运行时触发 Windows `basetemp` 清理权限错误；使用外部权限重跑后 `37 passed`。这是测试临时目录权限问题，不是业务测试失败。

## Paper 全链路明细

详细验证 run id：

```text
c08e3b280e614deea315e17400c5ade6
```

Pipeline jobs：

```text
paper_download
paper_parse
paper_refine_parse
paper_split_sections
paper_generate_note
```

Pipeline stages：

```text
download
parse
refine
split
summarize
```

最终业务状态：

| 字段 | 值 |
|---|---|
| pipeline status | `succeeded` |
| paper stage after extract | `completed` |
| note status | `clean_generated` |
| note size | `1288` chars |
| duplicate DOI rejected | `true` |
| delete then recreate same DOI | `true` |

## 文件生成检查

已确认以下 artifact 文件在测试时生成且非空：

- `source_pdf`
- `raw_markdown`
- `refined_markdown`
- `refine_line_index`
- `refine_diagnosis`
- `refine_patches`
- `refine_patch_apply_report`
- `refine_deterministic_normalization`
- `refine_skill_context`
- `refine_verify`
- `section_related_work`
- `section_method`
- `section_experiment`
- `section_appendix`
- `section_conclusion`
- `section_split_report`
- `note_markdown`

额外生成文件：

- `extracted/knowledge.json`
- `extracted/datasets.json`

备注：本次 `knowledge.json` 与 `datasets.json` 仍是占位格式输出，符合“skill 仍在迭代，不要求内容质量”的测试前提。

## 数据库检查

SQLite 检查结果：

| 检查项 | 结果 |
|---|---|
| `PRAGMA integrity_check` | `ok` |
| `PRAGMA foreign_key_check` | `0` violations |
| Paper 写入 | 正常 |
| 重复 DOI 拦截 | 正常，返回 409 |
| Paper 删除 | 正常，删除后 GET 返回 404 |
| 删除后同 DOI 重新写入 | 正常 |

索引检查覆盖表：

- `asset_registry`
- `biz_paper`
- `biz_doc_layout`
- `biz_paper_artifact`
- `biz_paper_pipeline_run`

关键索引存在：

- `idx_asset_registry_deleted`
- `idx_asset_registry_type`
- `idx_biz_paper_doi`
- `idx_biz_paper_stage`
- `idx_biz_paper_category`
- `idx_biz_doc_layout_parent`
- `idx_biz_paper_artifact_key`
- `idx_biz_paper_artifact_paper`
- `idx_biz_paper_pipeline_stage`
- `idx_biz_paper_pipeline_paper`

## 发现与处理

测试过程中发现详细验证脚本的 fake refine repair 输出没有保留原始 DOI / Year 数字，导致本地 verify 的数字保留检查失败。该问题属于测试桩构造问题，不是项目代码问题。已调整测试桩，使其保留原始数字 metadata 后重跑，全链路通过。

## 剩余风险

- 本次未跑真实网络下载、真实 MinerU、真实 LLM provider。
- `paper-knowledge-mining` 与 `paper-dataset-mining` 后端仍是 placeholder 输出，只验证文件与格式生成。
- Skill 内容质量需要后续单独迭代。
