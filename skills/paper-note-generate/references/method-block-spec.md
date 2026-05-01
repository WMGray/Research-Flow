# Method Block Specification

The `method` block is the most important block in a deep-reading note. It follows a strict recursive structure with figures embedded inline.

## Contents

- Level Structure
- Sub-component Four-Element Rule
- Formula Writing: Correct vs Forbidden
- Inline Figure Embedding
- Figure Analysis (Three-Part Rule)

## Level Structure

- `### 方法总览` — one paragraph listing all modules, their data-flow relationships, what each does, and how key method figures support understanding the framework.
- `#### N. 模块中文名 (English Name)` — per module
  - `##### 0. 背景` — why this module exists, what problem it solves
  - `##### 1. 原理内容` — step-by-step mechanism
    - `###### 子组件名` — each sub-component
  - `##### 2. [optional] validation or ablation evidence`

## Sub-component Four-Element Rule (mandatory, no skipping)

For each sub-component, write in this exact order:

1. **Narrative (Chinese)**: what it does, how it works, inputs and outputs
2. **Formula**: extract the original `$$` block verbatim from the source text — do not change symbols
3. **Variable explanation**: explain every symbol — meaning, dimensions, physical significance
4. **Link**: how the output connects to the next sub-component or module

## Formula Writing: Correct vs Forbidden

```
Correct:
- **降维**：通过下采样矩阵 W_down 将特征维度压缩为原来的 γ 倍（默认 γ=0.5），
  再经 GELU 激活函数 σ 增加非线性。

  $$
  Y^{\prime} = \sigma(YW_{down})
  $$

  其中 Y ∈ R^{L×D} 是上一层 Transformer 的输出，L 为 Token 数量，D 为特征维度；
  W_down ∈ R^{D×γD} 是下采样矩阵；σ 为 GELU 激活函数。降维后 Y′ ∈ R^{L×γD}，
  进入下一步空间卷积。

Forbidden:
  $$
  Y^{\prime} = \sigma(YW_{down})
  $$
  公式通过降维后输出 Y′。  ← 变量未解释，缺少维度和衔接，太模糊
```

## Inline Figure Embedding

Place `<!-- figure -->` markers in the method text where figures should appear:

- After the method overview paragraph, before the first module — if an architecture overview figure exists
- After a sub-component explanation that the figure visualizes
- One marker per figure, in the order figures appear in `{{figure_context}}`

```
### 方法总览
本文方法包含两大核心模块：HOD 数据生成管道负责 X，EgoVideo 模型负责 Y。

<!-- figure -->

#### 1. HOD 数据生成管道 (Hand-Object Dynamics Pipeline)
...
```

## Figure Analysis (Three-Part Rule)

For each method/problem figure, write the analysis before or after the `<!-- figure -->` marker:

1. **What it shows** (1-2 sentences): figure type and core components
2. **How to read it** (2-3 sentences): data flow direction, key symbols/arrows, module connections
3. **Why it matters** (1-2 sentences): relationship to the core contribution

If a figure's caption is missing, append `>[!Caution]` at the end of the analysis.

See also: `references/figure-handling.md` for the complete figure collection, role classification, and inline embedding pipeline.
