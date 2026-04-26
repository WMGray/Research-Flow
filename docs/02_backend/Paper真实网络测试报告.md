# Paper 真实网络测试报告

测试日期：2026-04-26

## 结论

真实网络端到端流程已跑通：`download -> parse -> refine -> split -> summarize` 全部成功，最终 Paper 状态为 `noted`。

本轮重点验证 `refine` 是否真实生效。结果确认：`refined.md` 不再是 raw no-op，真实 LoRA 论文上执行了 123 条 deterministic normalization，并注册完整审计 artifacts。

## 记录说明

本次真实网络探针曾生成 `backend/data/tmp/test_reports/real_paper_network_probe_20260426T143211Z.json`，随后按“清空测试记录”要求删除临时记录。以下为保留在文档中的最终结果摘要。

## 真实输入

- 论文：LoRA: Low-Rank Adaptation of Large Language Models
- arXiv：`https://arxiv.org/abs/2106.09685`
- PDF：`https://arxiv.org/pdf/2106.09685`
- DOI：`10.48550/arXiv.2106.09685`

## 结果摘要

| Stage | 结果 | 关键证据 |
| --- | --- | --- |
| download | succeeded | gPaper/arXiv，PDF `1,609,513` bytes |
| parse | succeeded | MinerU，raw Markdown `103,266` bytes |
| refine | succeeded | `deterministic_operation_count=123`，`refined_chars=102,148` |
| split | succeeded | 生成 related_work/method/experiment/conclusion 四个 canonical sections |
| summarize | succeeded | LLM note generated，`paper_stage=noted` |

## Refine 行为

本次 DeepSeek 没有产出可安全应用的 LLM patch：

```text
applied_patch_count=0
rejected_patch_count=0
verify_status=warning
```

但 deterministic normalization 生效：

```text
deterministic_operation_count=123
artifact=refine_deterministic_normalization
```

已确认的实际优化包括：

- `# ABSTRACT` -> `## Abstract`
- `# 1 INTRODUCTION` -> `## 1 INTRODUCTION`
- `# 5.1 BASELINES` -> `### 5.1 BASELINES`
- `# 7.1 ...` / `# 7.2 ...` / `# 7.3 ...` 从错误顶级 heading 降为子节层级
- title 使用 Paper metadata 安全修正 OCR hyphenation
- image/caption 邻接和多余空白规范化

本地 preservation checks 保持通过，未丢 citations、numbers、image links 或 formula markers。

## Split 行为

本次 split 使用 deterministic strategy：

```text
split_strategy=deterministic
used_llm=false
section_count=4
artifact=section_split_report
```

原因：refine 后 heading hierarchy 已足够清晰，deterministic rules 能识别四个 canonical sections，不需要 LLM split 兜底。

## 外部服务情况

真实网络测试期间 Semantic Scholar 出现 HTTP 429，下载器按 retry 策略等待后成功；这是外部速率限制，不影响最终链路。
