# PDF Refine Runtime 雏形

## 当前落地范围

本雏形把 MinerU `full.md` 优化从“LLM 直接重写整篇 Markdown”改为“LLM 诊断与产出补丁，后端确定性应用补丁”：

```text
parsed/raw.md
  -> parsed/refine/line_index.json
  -> parsed/refine/diagnosis.json
  -> parsed/refine/patches.json
  -> parsed/refine/patch_apply_report.json
  -> parsed/refine/prompt_context.json
  -> parsed/refine/verify.json
  -> parsed/refined.md
```

## 运行时模块

- `backend/core/services/papers/refine_runtime.py`：编排 diagnose / repair / verify。
- `backend/core/services/papers/refine_parsing.py`：line index、issue/patch/report 数据结构、LLM JSON 解析、结构证据窗口、payload 归一化。
- `backend/core/services/papers/refine_patch.py`：patch apply engine 与本地 preservation checks。

## Prompt 与 Skill Binding

- `backend/config/skill_bindings.toml` 将 `paper_refine_parse` 拆为：
  - `paper_refine_parse.diagnose`
  - `paper_refine_parse.repair`
  - `paper_refine_parse.verify`
- `backend/config/prompt_templates.toml` 注册对应 prompt 文件。
- `backend/config/prompts/paper_refine.md` 合并保存 `diagnose`、`repair`、`verify`、`default` 四个 section。
- legacy `pdf_parser.markdown_refine` 默认也通过 `prompt_template_key = "paper_refine_parse.default"` 读取同一个 prompt 文件；`prompt` 字段只作为显式覆盖入口。
- `skills/paper-refine-parse/` 固化后续维护这条链路的 Codex skill。

## 安全边界

- 后端只在 verifier 未失败时写入 `parsed/refined.md`。
- 本地检查会拦截 citation、number、formula、image link、长度比例等明显破坏。
- LLM `pass` 不能覆盖本地 preservation check 的 `fail`。
- 低置信度、重叠、越界、空 replacement、未知 op 的 patch 会被拒绝并进入 apply report。
- LLM 控制 JSON 解析失败时执行 warning/no-op：保留 raw markdown，不应用不可信 patch，并把 warning 写入 refine artifacts。

## 已验证

- `compileall` 通过新增后端模块。
- 直接 smoke 覆盖：
  - heading patch 成功应用并写出 artifacts。
  - 破坏 citation/number 的 patch 即使 LLM verifier 返回 `pass`，也会被本地检查阻断。
- `ruff` 在 backend venv 中通过目标文件检查。
- `skill-creator` 的 `quick_validate.py` 验证 `skills/paper-refine-parse` 通过。
- 真实网络探针已跑通 gPaper/arXiv 下载、MinerU 云解析、DeepSeek refine warning/no-op、canonical split 和 LLM note。

## 当前限制

- API 仍是同步 job placeholder，不是真正异步队列。
- patch engine 暂不支持复杂 `move_span`，遇到读序大错乱应先 `mark_needs_review`。
- DeepSeek/Kimi 都可能返回非严格 JSON；后续应接入 JSON mode / schema enforcement / repair-on-invalid。
- pytest 在当前 Windows 环境的 basetemp 清理阶段仍触发 `PermissionError`，需要单独处理测试临时目录权限。
