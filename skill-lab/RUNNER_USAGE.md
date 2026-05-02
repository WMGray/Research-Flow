# Skill Lab Runner 使用命令

本文件用于本地回放 Paper skills。推荐顺序是：

```text
refine-parse -> sectioning -> note-generate -> knowledge-mining
                            \-> dataset-mining
```

`dataset-mining` 在 `sectioning` 后即可运行；`knowledge-mining` 必须等 `note-generate` 成功后运行。

## 1. 前提准备

```powershell
cd C:\Users\WMGray\Desktop\Research-Flow
$env:PYTHONUTF8='1'
[Console]::OutputEncoding=[System.Text.Encoding]::UTF8
```

确认本地已配置联网 LLM：

```powershell
Get-Content backend\.env
Get-Content backend\config\settings.toml
```

## 2. 变量设置

```powershell
$cases = @(
  'uploaded-paper-20260429',
  'lora-title-artifact-mineru',
  'iccv2023-ovvis-mineru',
  'cvpr2025-bimc-mineru'
)

$stamp = Get-Date -Format 'yyyyMMddHHmmss'
```

## 3. 批量 refine-parse

批量联网 parse，并把成功输出迁移到 `sources/01-paper-refine-parse/<case>/refined.md`：

```powershell
foreach ($case in $cases) {
  $runDir = "skill-lab\runs\paper-refine-parse\$case\$stamp"
  New-Item -ItemType Directory -Force $runDir | Out-Null

  $result = python skill-lab\runner\run_refine_parse.py `
    --input "skill-lab\sources\01-paper-refine-parse\$case\raw.md" `
    --output "$runDir\refined.md" `
    --source-output "skill-lab\sources\01-paper-refine-parse\$case\refined.md"

  $result | Set-Content -Encoding UTF8 "$runDir\run_summary.json"
}
```

校验 refine-parse：

```powershell
$rows = @()

foreach ($case in $cases) {
  $sourcePath = "skill-lab\sources\01-paper-refine-parse\$case\refined.md"
  $latest = Get-ChildItem -Directory "skill-lab\runs\paper-refine-parse\$case" |
    Sort-Object Name -Descending |
    Select-Object -First 1
  $summary = Get-Content -Raw -Encoding UTF8 "$($latest.FullName)\run_summary.json" | ConvertFrom-Json

  $rows += [PSCustomObject]@{
    Case = $case
    Refined = $summary.refined
    SourceExists = Test-Path $sourcePath
    SourceChars = if (Test-Path $sourcePath) { (Get-Content -Raw -Encoding UTF8 $sourcePath).Length } else { 0 }
    RunDir = $latest.FullName
  }
}

$rows | Format-Table -AutoSize
```

## 4. 批量 sectioning

批量 section，并把输出写入 `sources/02-paper-sectioning/<case>/sections/`：

```powershell
foreach ($case in $cases) {
  $runDir = "skill-lab\runs\paper-sectioning\$case\$stamp"
  New-Item -ItemType Directory -Force $runDir | Out-Null

  $result = python skill-lab\runner\run_sectioning.py `
    --input "skill-lab\sources\01-paper-refine-parse\$case\refined.md" `
    --output-dir "skill-lab\sources\02-paper-sectioning\$case\sections"

  $result | Set-Content -Encoding UTF8 "$runDir\run_summary.json"
  $result | Set-Content -Encoding UTF8 "skill-lab\sources\02-paper-sectioning\$case\run_summary.json"
}
```

校验 sectioning：

```powershell
$rows = @()

foreach ($case in $cases) {
  $sourceDir = "skill-lab\sources\02-paper-sectioning\$case"
  $sectionsDir = "$sourceDir\sections"
  $summary = Get-Content -Raw -Encoding UTF8 "$sourceDir\run_summary.json" | ConvertFrom-Json
  $report = Get-Content -Raw -Encoding UTF8 "$sectionsDir\split_report.json" | ConvertFrom-Json

  $rows += [PSCustomObject]@{
    Case = $case
    UsedLLM = $summary.used_llm
    Strategy = $summary.strategy
    Status = $report.status
    SectionFiles = (Get-ChildItem "$sectionsDir\0*.md" -ErrorAction SilentlyContinue).Count
    SplitReport = Test-Path "$sectionsDir\split_report.json"
    Images = if (Test-Path "$sourceDir\images") { (Get-ChildItem "$sourceDir\images" -File).Count } else { 0 }
  }
}

$rows | Format-Table -AutoSize
```

## 5. 批量 note-generate

批量联网 note，并把成功输出同步到 `sources/03-paper-note-generate/<case>/`：

```powershell
foreach ($case in $cases) {
  python skill-lab\runner\run_note_generate.py --case $case
}
```

校验 note：

```powershell
$rows = @()

foreach ($case in $cases) {
  $source = "skill-lab\sources\03-paper-note-generate\$case"
  $summary = Get-Content -Raw -Encoding UTF8 "$source\summary.json" | ConvertFrom-Json
  $validation = Get-Content -Raw -Encoding UTF8 "$source\validation.json" | ConvertFrom-Json
  $runSummary = Get-Content -Raw -Encoding UTF8 "$source\run_summary.json" | ConvertFrom-Json

  $rows += [PSCustomObject]@{
    Case = $case
    Source = $summary.source
    Failures = $summary.block_failures.Count
    Blocks = $summary.block_count
    Figures = $summary.figure_count
    HeadingsOK = $validation.expected_top_headings_present
    Synced = $runSummary.source_sync.synced
    RunDir = $runSummary.note_run_dir
  }
}

$rows | Format-Table -AutoSize
```

## 6. 批量 dataset-mining

`dataset-mining` 只依赖 metadata 与 sectioning 输出，不依赖 `note.md`。它使用 `experiment`、`related_work`、`introduction` 三类 section：

```powershell
foreach ($case in $cases) {
  python skill-lab\runner\run_dataset_mining.py `
    --case $case `
    --instruction-key paper_dataset_mining.default `
    --feature default_chat
}
```

校验 dataset：

```powershell
$rows = @()

foreach ($case in $cases) {
  $source = "skill-lab\sources\05-paper-dataset-mining\$case"
  $summary = Get-Content -Raw -Encoding UTF8 "$source\summary.json" | ConvertFrom-Json
  $validation = Get-Content -Raw -Encoding UTF8 "$source\validation.json" | ConvertFrom-Json
  $runSummary = Get-Content -Raw -Encoding UTF8 "$source\run_summary.json" | ConvertFrom-Json

  $rows += [PSCustomObject]@{
    Case = $case
    Source = $summary.source
    Items = $summary.item_count
    MissingRequired = $validation.missing_required.Count
    Synced = $runSummary.source_sync.synced
    RunDir = $runSummary.dataset_run_dir
  }
}

$rows | Format-Table -AutoSize
```

## 7. 批量 knowledge-mining

`knowledge-mining` 依赖 metadata、sectioning 输出与 `note.md`。它使用 `introduction`、`related_work`、`method`、`experiment`、`conclusion` 五类 section，并把 `note.md` 作为候选发现上下文：

```powershell
foreach ($case in $cases) {
  python skill-lab\runner\run_knowledge_mining.py `
    --case $case `
    --instruction-key paper_knowledge_mining.default `
    --feature default_chat
}
```

校验 knowledge：

```powershell
$rows = @()

foreach ($case in $cases) {
  $source = "skill-lab\sources\04-paper-knowledge-mining\$case"
  $summary = Get-Content -Raw -Encoding UTF8 "$source\summary.json" | ConvertFrom-Json
  $validation = Get-Content -Raw -Encoding UTF8 "$source\validation.json" | ConvertFrom-Json
  $runSummary = Get-Content -Raw -Encoding UTF8 "$source\run_summary.json" | ConvertFrom-Json

  $rows += [PSCustomObject]@{
    Case = $case
    Source = $summary.source
    Items = $summary.item_count
    MissingRequired = $validation.missing_required.Count
    Synced = $runSummary.source_sync.synced
    RunDir = $runSummary.knowledge_run_dir
  }
}

$rows | Format-Table -AutoSize
```
