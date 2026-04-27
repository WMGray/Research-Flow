# Paper 链路测试方案

## 目标

验证 Paper 主链路在本地回归、离线 smoke、真实联网探针三类场景下满足功能契约，并保证每个关键阶段都有可追溯的数据产物。

主链路范围：

```text
create paper -> download PDF -> parse PDF -> refine parsed markdown -> split sections -> generate note -> extract knowledge/datasets
```

## 测试分层

| 层级 | 目标 | 覆盖范围 | 通过标准 |
| --- | --- | --- | --- |
| pytest 回归 | 验证 API、状态流转、前置条件、artifact 与 pipeline run 记录 | paper API、download API、PDF parser、refine runtime | 相关测试全部通过 |
| 离线 smoke | 在无外部网络和 API key 场景下跑通主链路 | fallback download、parse、refine、split、note、用户手写 note 合并 | pipeline succeeded，手写内容不丢失 |
| 静态检查 | 避免语法和 lint 回归 | Paper service/API/schema/tests | `compileall` 与 `ruff check` 通过 |
| 真实联网探针 | 验证外部依赖、真实 PDF、MinerU、LLM provider | arXiv/gPaper、MinerU、LLM refine/split/note | 阶段成功，质量门禁逐项记录 |
| extract 补充 | 覆盖主链路末端能力 | `extract-knowledge`、`extract-datasets` | job 成功，输出 JSON 存在 |

## 功能契约

| 契约 | 验证点 |
| --- | --- |
| Paper 创建 | 支持 URL/DOI/标题元数据入库，初始化 stage/status 正确 |
| PDF 获取 | 下载或挂接后注册 `source_pdf` artifact，文件大小和 MIME 合理 |
| 原始解析 | MinerU 或 fallback parser 生成 raw markdown，并保留图表路径 |
| refine | 生成 refined markdown，登记 diagnosis/patch/verify/normalization 等审计文件 |
| section split | 生成 canonical sections，并登记 split report |
| note generate | 生成 managed blocks，保留用户手写内容，图表引用指向后处理路径 |
| extract | 生成 knowledge/datasets JSON，后续应纳入 pipeline run 与 artifact 审计 |
| 可追溯性 | 每个主阶段都能从 DB run、artifact 表和文件系统定位到底层产物 |

## 推荐命令

本地回归：

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_papers_api.py tests\test_paper_download_api.py tests\test_pdf_parser_pipeline.py tests\test_paper_refine_runtime.py -q --basetemp .pytest-paper-chain
```

离线 smoke：

```powershell
.\.venv\Scripts\python.exe tests\run_paper_pipeline_smoke.py
```

静态检查：

```powershell
.\.venv\Scripts\python.exe -m compileall core\services\papers app\api\papers.py app\schemas\papers.py tests
.\.venv\Scripts\python.exe -m ruff check core\services\papers app\api\papers.py app\schemas\papers.py tests
```

真实联网探针：

```powershell
.\.venv\Scripts\python.exe tests\run_real_paper_network_probe.py
```

## 报告与数据位置

长期测试方案放在 `docs/02_backend/`。

人工可读的测试报告放在：

```text
reports/paper/
```

机器生成的 JSON 报告放在：

```text
backend/data/tmp/test_reports/
```

真实联网探针的底层运行数据放在：

```text
backend/data/tmp/real_paper_network_probe/
```

## 质量门禁

真实联网报告至少记录以下检查：

- 真实网络下载成功，PDF 大小大于 50KB。
- MinerU 解析实际启用。
- raw/refined markdown 中图表路径可访问。
- refine 产物包含 deterministic normalization 或 LLM patch 审计文件。
- sections artifact 已登记。
- note artifact 已登记，正文长度合理。
- note 中没有 block-level LLM 解析失败；如有失败，必须记录 fallback block、原始错误和影响范围。
- extract 输出文件存在；若仍是 placeholder，需要在报告中标注能力限制。
