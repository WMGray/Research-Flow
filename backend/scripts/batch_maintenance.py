from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.core.config import get_settings
from backend.core.services.papers import PaperService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Research-Flow batch maintenance helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    restore_parser = subparsers.add_parser("restore", help="Restore candidates.json for a batch")
    restore_parser.add_argument("--batch-id", required=True)

    cleanup_parser = subparsers.add_parser("cleanup-empty", help="Delete batches with zero pending candidates")
    cleanup_parser.add_argument("--batch-id")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    service = PaperService(data_root=get_settings().data_root)

    if args.command == "restore":
        candidates = service.restore_batch_candidates(args.batch_id)
        print(
            json.dumps(
                {
                    "batch_id": args.batch_id,
                    "restored": len(candidates),
                    "candidates": candidates,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.command == "cleanup-empty":
        if args.batch_id:
            removed = [args.batch_id] if service.cleanup_batch(args.batch_id) else []
        else:
            removed = service.cleanup_batches()
        print(json.dumps({"removed": removed}, ensure_ascii=False, indent=2))
        return 0

    parser.error("Unsupported command")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
