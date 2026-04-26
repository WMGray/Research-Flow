from __future__ import annotations

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


DEFAULT_MARKDOWN_REFINE_TEMPLATE_KEY = "paper_refine_parse.default"


class MarkdownRefineConfig(BaseModel):
    """LLM-based Markdown formatting stage before section splitting."""

    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("enabled", "PDF_PARSER_MARKDOWN_REFINE_ENABLED"),
    )
    feature: str = Field(
        default="pdf_markdown_refiner",
        validation_alias=AliasChoices("feature", "PDF_PARSER_MARKDOWN_REFINE_FEATURE"),
    )
    prompt_template_key: str = Field(
        default=DEFAULT_MARKDOWN_REFINE_TEMPLATE_KEY,
        validation_alias=AliasChoices(
            "prompt_template_key",
            "PDF_PARSER_MARKDOWN_REFINE_PROMPT_TEMPLATE_KEY",
        ),
    )
    prompt: str = Field(
        default="",
        validation_alias=AliasChoices("prompt", "PDF_PARSER_MARKDOWN_REFINE_PROMPT"),
    )
    max_input_chars: int | None = Field(
        default=None,
        validation_alias=AliasChoices("max_input_chars", "PDF_PARSER_MARKDOWN_REFINE_MAX_INPUT_CHARS"),
    )
    output_filename: str = Field(
        default="LLM.refined.md",
        validation_alias=AliasChoices("output_filename", "PDF_PARSER_MARKDOWN_REFINE_OUTPUT_FILENAME"),
    )
    fail_open: bool = Field(
        default=True,
        validation_alias=AliasChoices("fail_open", "PDF_PARSER_MARKDOWN_REFINE_FAIL_OPEN"),
    )


class PDFParserConfig(BaseModel):
    """Configuration for the full PDF parsing pipeline."""

    model_config = ConfigDict(populate_by_name=True)

    markdown_refine: MarkdownRefineConfig = Field(default_factory=MarkdownRefineConfig)
