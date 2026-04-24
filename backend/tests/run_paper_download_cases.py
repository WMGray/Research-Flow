from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.schemas.paper_download import PaperDownloadRequest, PaperResolveRequest
from core.services.paper_download.service import PaperDownloadService


# 内置几个代表性案例，用来人工验证不同 gPaper 解析路径的返回情况。
DEFAULT_CASES: dict[str, dict[str, Any]] = {
    "direct_pdf": {
        "description": "直接 PDF URL，覆盖 gPaper 的 direct PDF + final probe 路径。",
        "request": {
            "url": "https://arxiv.org/pdf/1706.03762.pdf",
            "title": "Attention Is All You Need",
            "year": "2017",
            "venue": "NeurIPS",
        },
    },
    "arxiv_url": {
        "description": "arXiv 摘要页 URL，覆盖 arXiv -> metadata -> official/fallback 路径。",
        "request": {
            "url": "https://arxiv.org/abs/1706.03762",
            "title": "Attention Is All You Need",
            "year": "2017",
            "venue": "NeurIPS",
        },
    },
    "arxiv_doi": {
        "description": "arXiv DOI，覆盖 DOI 标准化和 arXiv DOI 处理路径。",
        "request": {
            "doi": "10.48550/arXiv.1706.03762",
            "title": "Attention Is All You Need",
            "year": "2017",
            "venue": "NeurIPS",
        },
    },
    "title_search": {
        "description": "仅标题查询，覆盖 gPaper title search fallback 链。",
        "request": {
            "name": "Attention Is All You Need",
            "year": "2017",
            "venue": "NeurIPS",
        },
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "通过 Research-Flow 的 paper_download 适配层，手工运行 gPaper 集成检查。"
            "除 --list-cases 外，其余模式都会发起真实网络请求。"
        )
    )
    parser.add_argument(
        "--case",
        action="append",
        choices=sorted(DEFAULT_CASES),
        help="要运行的案例，可重复传入；默认运行全部案例。",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="在 resolve 之外继续执行真实 PDF 下载。",
    )
    parser.add_argument(
        "--output-dir",
        default="data/paper_download_test",
        help="开启 --download 时使用的输出目录。",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="开启 --download 时覆盖已有文件。",
    )
    parser.add_argument(
        "--trace-limit",
        type=int,
        default=8,
        help="每个案例最多打印多少条 probe_trace；0 表示全部打印。",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="输出 JSON 格式摘要，便于做人工比对或存档。",
    )
    parser.add_argument(
        "--list-cases",
        action="store_true",
        help="只列出内置案例，不发起网络请求。",
    )
    return parser.parse_args()


def row_to_dict(row: Any) -> dict[str, Any]:
    if is_dataclass(row):
        return asdict(row)
    if hasattr(row, "model_dump"):
        return row.model_dump(mode="json")
    if isinstance(row, dict):
        return row
    keys = (
        "raw_input",
        "title",
        "year",
        "venue",
        "doi",
        "resolve_method",
        "source",
        "status",
        "pdf_url",
        "landing_url",
        "final_url",
        "http_status",
        "content_type",
        "detail",
        "error_code",
        "metadata_source",
        "metadata_confidence",
        "suggested_filename",
        "target_path",
        "probe_trace",
    )
    return {key: getattr(row, key, "") for key in keys}


def print_cases() -> None:
    print("Available paper_download gPaper cases:")
    for name, case in DEFAULT_CASES.items():
        print(f"- {name}: {case['description']}")
        print(f"  request={case['request']}")


def build_request(
    case: dict[str, Any],
    args: argparse.Namespace,
) -> PaperResolveRequest | PaperDownloadRequest:
    request_data = dict(case["request"])
    if args.download:
        request_data["output_dir"] = args.output_dir
        request_data["overwrite"] = args.overwrite
        return PaperDownloadRequest.model_validate(request_data)
    return PaperResolveRequest.model_validate(request_data)


def summarize_case(
    *,
    name: str,
    description: str,
    row: Any,
    download_result: dict[str, Any] | None,
    trace_limit: int,
) -> dict[str, Any]:
    payload = row_to_dict(row)
    trace = list(payload.get("probe_trace") or [])
    visible_trace = trace if trace_limit == 0 else trace[:trace_limit]
    summary = {
        "case": name,
        "description": description,
        "status": payload.get("status", ""),
        "title": payload.get("title", ""),
        "year": payload.get("year", ""),
        "venue": payload.get("venue", ""),
        "doi": payload.get("doi", ""),
        "source": payload.get("source", ""),
        "resolve_method": payload.get("resolve_method", ""),
        "metadata_source": payload.get("metadata_source", ""),
        "metadata_confidence": payload.get("metadata_confidence", ""),
        "http_status": payload.get("http_status", ""),
        "content_type": payload.get("content_type", ""),
        "pdf_url": payload.get("pdf_url", ""),
        "landing_url": payload.get("landing_url", ""),
        "detail": payload.get("detail", ""),
        "error_code": payload.get("error_code", ""),
        "suggested_filename": payload.get("suggested_filename", ""),
        "target_path": payload.get("target_path", ""),
        "probe_trace_count": len(trace),
        "probe_trace": visible_trace,
    }
    if download_result is not None:
        summary["download"] = download_result
    return summary


def print_human_summary(summary: dict[str, Any]) -> None:
    print("\n" + "=" * 88)
    print(f"[{summary['case']}] {summary['description']}")
    print("-" * 88)
    print(f"status             : {summary['status']}")
    print(f"title              : {summary['title']}")
    print(f"year / venue       : {summary['year'] or '-'} / {summary['venue'] or '-'}")
    print(f"doi                : {summary['doi'] or '-'}")
    print(f"source             : {summary['source'] or '-'}")
    print(f"resolve_method     : {summary['resolve_method'] or '-'}")
    print(
        "metadata           : "
        f"{summary['metadata_source'] or '-'} ({summary['metadata_confidence'] or '-'})"
    )
    print(
        f"http/content       : {summary['http_status'] or '-'} / "
        f"{summary['content_type'] or '-'}"
    )
    print(f"pdf_url            : {summary['pdf_url'] or '-'}")
    print(f"landing_url        : {summary['landing_url'] or '-'}")
    print(f"error_code         : {summary['error_code'] or '-'}")
    print(f"detail             : {summary['detail'] or '-'}")
    print(f"suggested_filename : {summary['suggested_filename'] or '-'}")
    print(f"target_path        : {summary['target_path'] or '-'}")
    if "download" in summary:
        print(f"download           : {summary['download']}")
    print(f"probe_trace        : {summary['probe_trace_count']} step(s)")
    for index, step in enumerate(summary["probe_trace"], start=1):
        print(f"  {index}. {step}")
    if summary["probe_trace_count"] > len(summary["probe_trace"]):
        hidden = summary["probe_trace_count"] - len(summary["probe_trace"])
        print(f"  ... {hidden} more step(s); rerun with --trace-limit 0 to show all")


def run_case(name: str, args: argparse.Namespace) -> dict[str, Any]:
    case = DEFAULT_CASES[name]
    service = PaperDownloadService()
    request = build_request(case, args)
    if args.download:
        row, download_result = service.download(request)
    else:
        row = service.resolve(request)
        download_result = None
    return summarize_case(
        name=name,
        description=case["description"],
        row=row,
        download_result=download_result,
        trace_limit=args.trace_limit,
    )


def main() -> int:
    args = parse_args()
    if args.list_cases:
        print_cases()
        return 0

    selected_cases = args.case or list(DEFAULT_CASES)
    summaries: list[dict[str, Any]] = []
    failures = 0
    for case_name in selected_cases:
        try:
            summary = run_case(case_name, args)
            summaries.append(summary)
            if not summary["status"]:
                failures += 1
        except Exception as exc:
            failures += 1
            summaries.append(
                {
                    "case": case_name,
                    "description": DEFAULT_CASES[case_name]["description"],
                    "status": "script_error",
                    "detail": str(exc),
                    "error_code": exc.__class__.__name__,
                    "probe_trace": [],
                    "probe_trace_count": 0,
                }
            )

    if args.json:
        print(json.dumps(summaries, ensure_ascii=False, indent=2))
    else:
        for summary in summaries:
            print_human_summary(summary)
        print("\n" + "=" * 88)
        print(f"Completed {len(summaries)} case(s), script failures: {failures}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
