"""app 与 worker 共享的 Celery 任务名契约。

`app.tasks` 只使用这些常量发布任务；`worker.tasks` 使用同名常量注册任务。
这样可以避免投递端和执行端任务名漂移。
"""

# Paper 主链路任务。
PAPER_DOWNLOAD = "worker.tasks.papers.paper_download"
PAPER_PARSE = "worker.tasks.papers.parse"
PAPER_REFINE = "worker.tasks.papers.refine"
PAPER_SPLIT = "worker.tasks.papers.split"
PAPER_GENERATE_NOTE = "worker.tasks.papers.generate_note"
PAPER_EXTRACT_KNOWLEDGE = "worker.tasks.papers.extract_knowledge"
PAPER_EXTRACT_DATASETS = "worker.tasks.papers.extract_datasets"
PAPER_CONFIRM_PIPELINE = "worker.tasks.papers.confirm_pipeline"
PAPER_IMPORT_PIPELINE = "worker.tasks.papers.import_pipeline"

# Project 模块生成与刷新任务。
PROJECT_GENERATE_RELATED_WORK = "worker.tasks.projects.generate_related_work"
PROJECT_GENERATE_METHOD = "worker.tasks.projects.generate_method"
PROJECT_GENERATE_EXPERIMENT = "worker.tasks.projects.generate_experiment"
PROJECT_GENERATE_CONCLUSION = "worker.tasks.projects.generate_conclusion"
PROJECT_GENERATE_MANUSCRIPT = "worker.tasks.projects.generate_manuscript"
PROJECT_REFRESH_OVERVIEW = "worker.tasks.projects.refresh_overview"

# Knowledge 归一化任务。
KNOWLEDGE_NORMALIZE = "worker.tasks.knowledge.normalize"

# Feed 与会议相关定时任务。
FEED_FETCH_AND_SCORE = "worker.tasks.feed.fetch_and_score"
FEED_DAILY_PUSH = "worker.tasks.feed.daily_push"

CONFERENCE_REFRESH_ALL = "worker.tasks.conference.refresh_all"
CONFERENCE_CHECK_DEADLINES = "worker.tasks.conference.check_deadlines"

# Presentation 生成与导出任务。
PRESENTATION_GENERATE_OUTLINE = "worker.tasks.presentation.generate_outline"
PRESENTATION_GENERATE_SLIDES = "worker.tasks.presentation.generate_slides"
PRESENTATION_EXPORT = "worker.tasks.presentation.export"

# 全量任务名集合，用于后续 contract test 检查重复和注册完整性。
ALL_TASK_NAMES: tuple[str, ...] = (
    PAPER_DOWNLOAD,
    PAPER_PARSE,
    PAPER_REFINE,
    PAPER_SPLIT,
    PAPER_GENERATE_NOTE,
    PAPER_EXTRACT_KNOWLEDGE,
    PAPER_EXTRACT_DATASETS,
    PAPER_CONFIRM_PIPELINE,
    PAPER_IMPORT_PIPELINE,
    PROJECT_GENERATE_RELATED_WORK,
    PROJECT_GENERATE_METHOD,
    PROJECT_GENERATE_EXPERIMENT,
    PROJECT_GENERATE_CONCLUSION,
    PROJECT_GENERATE_MANUSCRIPT,
    PROJECT_REFRESH_OVERVIEW,
    KNOWLEDGE_NORMALIZE,
    FEED_FETCH_AND_SCORE,
    FEED_DAILY_PUSH,
    CONFERENCE_REFRESH_ALL,
    CONFERENCE_CHECK_DEADLINES,
    PRESENTATION_GENERATE_OUTLINE,
    PRESENTATION_GENERATE_SLIDES,
    PRESENTATION_EXPORT,
)
