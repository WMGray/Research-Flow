from __future__ import annotations

import argparse
import json
from pathlib import Path

from backend.app.library import PaperLibrary, write_json, write_text
from backend.app.settings import get_settings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Research-Flow paper library helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("scan", help="Print dashboard summary as JSON")

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

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    library = PaperLibrary(get_settings().data_root)

    if args.command == "scan":
        print(json.dumps(library.dashboard_home(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "ingest":
        record = library.ingest(
            Path(args.input),
            domain=args.domain,
            area=args.area,
            topic=args.topic,
            target_path=args.target_path,
            move=args.move,
        )
        print(json.dumps(record.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "migrate":
        record = library.migrate(
            Path(args.input),
            domain=args.domain,
            area=args.area,
            topic=args.topic,
            target_path=args.target_path,
        )
        print(json.dumps(record.to_dict(), ensure_ascii=False, indent=2))
        return 0

    if args.command == "note-template":
        metadata = {
            "title": args.title,
            "year": args.year,
            "venue": args.venue,
            "doi": args.doi,
            "domain": args.domain,
            "area": args.area,
            "topic": args.topic,
            "status": "draft",
            "tags": ["paper"],
        }
        content = library.generate_note_template(metadata)
        if args.output:
            write_text(Path(args.output), content)
        else:
            print(content)
        return 0

    parser.error("Unsupported command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

