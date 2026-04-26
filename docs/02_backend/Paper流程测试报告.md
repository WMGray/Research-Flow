# Paper 流程测试报告

测试日期：2026-04-26

## 结论

本轮 Paper 主链路通过本地回归与真实网络探针。`refine` 已从“LLM JSON 失败时 warning/no-op”调整为“LLM patch + deterministic normalization”，因此即使 LLM patch 未应用，`refined.md` 仍会执行可审计的结构优化。

## 已验证修复

- `5` / `5.1` heading hierarchy：major heading 保持 `##`，子节如 `5.1`、`7.1` 规范为更深层级，避免和父章节同级。
- Title metadata：可用 Paper 元数据对高置信标题 OCR 错误做安全修正，例如 `LAN-GUAGE` -> `Language`。
- Author metadata：prompt 明确要求只修可见 spacing/punctuation artifacts，不凭空补造作者。
- Section split：先用 deterministic major-heading rules；当覆盖不足时才调用 LLM 返回 line-range split plan，并拒绝低置信、重叠、未知 section key。
- Artifacts：新增 `refine_deterministic_normalization` 与 `section_split_report`，可审计每次结构改动和拆分策略。
- 代码精简：抽出 `prompt_runtime.py`，删除 repository 内旧 splitter，压缩 `section_split_runtime.py`，避免 prompt/TOML 加载逻辑重复。

## 本地回归

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_paper_refine_runtime.py tests\test_papers_api.py tests\test_llm.py -q --basetemp data\tmp\pytest_slim_iter2
```

结果：

```text
34 passed in 14.09s
```

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q --basetemp data\tmp\pytest_full_slim
```

结果：

```text
58 passed in 15.36s
```

静态检查：

```text
ruff check: passed
compileall: passed
skill quick_validate: passed
git diff --check: only CRLF warnings
```

## 真实网络探针

报告文件：

```text
backend/data/tmp/test_reports/real_paper_network_probe_20260426T143211Z.json
```

真实输入：

- Paper：LoRA: Low-Rank Adaptation of Large Language Models
- PDF：`https://arxiv.org/pdf/2106.09685`
- MinerU：真实云解析
- LLM：配置中的真实 DeepSeek/SiliconFlow provider

关键结果：

| Stage | 结果 | 证据 |
| --- | --- | --- |
| download | succeeded | `download_mode=gpaper`，PDF `1,609,513` bytes |
| parse | succeeded | `parse_mode=mineru`，raw Markdown `103,266` bytes |
| refine | succeeded | `deterministic_operation_count=123`，`applied_patch_count=0`，`verify_status=warning` |
| split | succeeded | `section_count=4`，`split_strategy=deterministic`，注册 `section_split_report` |
| summarize | succeeded | `summary_source=llm`，最终 `paper_stage=noted` |

本次 warning 的含义：LLM patch 未被安全应用，但 deterministic normalization 已实际生效，并通过本地 preservation checks；不再是 raw/refined 完全一致的 no-op。

## 测试记录清理

已删除可访问的历史与本轮测试记录目录 21 个，包括 `test_reports`、`real_paper_network_probe`、smoke/probe 目录和本轮 pytest basetemp。

仍有 19 个旧 pytest 临时目录因 Windows ACL 拒绝删除，均位于 workspace 内，主要是历史提升权限运行留下的 `.pytest-*` / `.codex-*` / `tmp_pytest_*` 目录。其中 `backend/data/tmp` 下还剩 2 个 ACL 受限目录。当前代码和报告不依赖这些旧目录。

## 剩余边界

- LLM split 是兜底，不是默认路径；只有 deterministic split 覆盖不足或可疑时才调用。
- DeepSeek 仍可能输出非严格 JSON；当前策略是拒绝不可信 patch，保留 deterministic normalization。
- 作者字段的自动修正保持保守：只修 spacing/punctuation，不凭 Paper metadata 生成缺失作者列表。
