# claude-scholar 与 AI-paper-reading 参考分析

## 本次实际参考范围

- `claude-scholar`: `paper-miner`, `ml-paper-writing`, `zotero-obsidian-bridge`, `zotero-notes`, paper note schema, section checklist。
- `AI-paper-reading`: CLI README, parser/orchestrator/planner/selector/explainer/composer/model schema。

## 可迁移设计

1. `claude-scholar` 的核心价值不是 PDF 修复，而是 durable research memory：一篇论文只产生一个 canonical note，笔记稳定分为 research question、method、evidence、limitations、relations 等块。
2. `paper-miner` 的可借鉴点是 source-attributed extraction：只抽取可复用结构与写作模式，不把未验证内容写入长期记忆。
3. `AI-paper-reading` 的核心路径是 PDF -> layout blocks -> figure/table candidates -> LLM selection/planning/explanation -> Markdown composition。LLM 不直接接管解析，而是在结构化证据上做选择、规划和解释。
4. 两者共同点是 schema-first：让 LLM 输出 JSON/ranges/blocks，后端负责应用、验证、持久化和拒绝。

## 对 Research-Flow 的落地取舍

- 当前不引入整套 layout vision pipeline，避免把已有 MinerU + refine runtime 变重。
- 保留 MinerU `full.md` 作为源 artifact，LLM 只做诊断、补丁、验证、section range、note block 生成。
- prompt 明确处理三类真实问题：章节层级错误、图文混层、章节错乱。
- section split 不再被描述为 batch；它基于论文 outline 和行号范围。
- note generation 采用 evidence-grounded schema，缺证据时显式写 `Not stated in the parsed paper.`，不补脑。

## 本次已同步到项目

- `skills/paper-refine-parse/references/paper-reading-patterns.md`
- `backend/config/prompts/paper_refine.md`
- `backend/config/prompts/paper_section_split.md`
- `backend/config/prompts/paper_note_generate.md`
