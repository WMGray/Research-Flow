from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.core.config import get_settings
from backend.core.services.papers import PaperService, write_text
from backend.core.services.papers.models import GenerateNoteInput, IngestPaperInput, ParsePdfInput


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Research-Flow paper library helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("scan", help="Print dashboard summary as JSON")
    subparsers.add_parser("config-health", help="Print data root and parser health")

    ingest_parser = subparsers.add_parser("ingest", help="Ingest a paper or paper directory")
    ingest_parser.add_argument("--input", required=True)
    ingest_parser.add_argument("--domain")
    ingest_parser.add_argument("--area")
    ingest_parser.add_argument("--topic")
    ingest_parser.add_argument("--target-path")
    ingest_parser.add_argument("--move", action="store_true")

    migrate_parser = subparsers.add_parser("migrate", help="Move a paper directory into Library")
    migrate_parser.add_argument("--input", required=True)
    migrate_parser.add_argument("--domain")
    migrate_parser.add_argument("--area")
    migrate_parser.add_argument("--topic")
    migrate_parser.add_argument("--target-path")

    note_parser = subparsers.add_parser("note-template", help="Render a note template")
    note_parser.add_argument("--title", required=True)
    note_parser.add_argument("--year")
    note_parser.add_argument("--venue")
    note_parser.add_argument("--doi")
    note_parser.add_argument("--domain")
    note_parser.add_argument("--area")
    note_parser.add_argument("--topic")
    note_parser.add_argument("--output")

    parse_parser = subparsers.add_parser("parse-pdf", help="Parse a paper PDF")
    parse_parser.add_argument("--paper-id", required=True)
    parse_parser.add_argument("--force", action="store_true")
    parse_parser.add_argument("--parser", default="auto", choices=["auto", "mineru"])

    mark_parser = subparsers.add_parser("mark-status", help="Mark a paper workflow status")
    mark_parser.add_argument("--paper-id", required=True)
    mark_parser.add_argument("--status", required=True, choices=["processed", "needs-review", "needs-pdf", "parse-failed", "rejected"])

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    settings = get_settings()
    library = PaperService(data_root=settings.data_root, data_layout=settings.data_layout)

    if args.command == "scan":
        print(json.dumps(library.dashboard_home(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "config-health":
        print(json.dumps(library.config_health(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "ingest":
        record = library.ingest(
            IngestPaperInput(
                source=Path(args.input),
                domain=args.domain,
                area=args.area,
                topic=args.topic,
                target_path=args.target_path,
                move=args.move,
            )
        )
        print(json.dumps(record.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "migrate":
        record = library.migrate(
            IngestPaperInput(
                source=Path(args.input),
                domain=args.domain,
                area=args.area,
                topic=args.topic,
                target_path=args.target_path,
                move=True,
            )
        )
        print(json.dumps(record.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "note-template":
        content = library.generate_note_template(
            GenerateNoteInput(
                title=args.title,
                year=int(args.year) if args.year else None,
                venue=args.venue or "",
                doi=args.doi or "",
                domain=args.domain or "",
                area=args.area or "",
                topic=args.topic or "",
                tags=["paper"],
            )
        )
        if args.output:
            write_text(Path(args.output), content)
        else:
            print(content)
        return 0

    if args.command == "parse-pdf":
        record = library.parse_pdf(ParsePdfInput(paper_id=args.paper_id, force=args.force, parser=args.parser))
        print(json.dumps(record.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "mark-status":
        if args.status == "needs-review":
            record = library.mark_review(args.paper_id)
        elif args.status == "processed":
            record = library.mark_processed(args.paper_id)
        elif args.status == "rejected":
            record = library.reject_paper(args.paper_id)
        else:
            record = library.repository.mark_status(args.paper_id, args.status)
        print(json.dumps(record.to_dict(), ensure_ascii=False, indent=2))
        return 0

    parser.error("Unsupported command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
