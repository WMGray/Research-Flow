# MiniMax

## 定位

`MiniMax` 作为可选 `LLM Provider` 接入 Research-Flow 后端，用于承担论文解析优化、`note.md` 生成、Knowledge 提炼、LLM 连通性探测与 PPT 草稿生成等模型能力。

## 当前用途

- `paper_refine_parse`
- `paper_generate_note`
- `paper_extract_knowledge`
- `presentation_generate_outline`
- `presentation_generate_slides`
- `llm_connectivity_probe`

## 配置要求

- 模型接入信息通过后端配置或环境变量管理
- 模型选择通过 `AgentProfile` 绑定到具体场景
- Prompt 内容通过 `PromptTemplate` 管理，不直接写死在业务代码中

## 当前边界

- 当前文档仅说明服务定位，不限定必须使用 `MiniMax`
- 若后续引入其他 `LLM Provider`，仍复用统一的 `AgentProfile + PromptTemplate` 配置模型
- 凭证信息不得写入仓库
