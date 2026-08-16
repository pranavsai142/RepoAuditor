from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from repoauditor.auditor.run import cmd_analyze, cmd_pack
from repoauditor.pipeline import (
    cmd_discover,
    cmd_extract,
    cmd_flag,
    cmd_rank,
    cmd_scan,
    parse_as_of_arg,
    _write_report,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="repoauditor",
        description="Scan a directory of local git repos. Git is not a timesheet.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_disc = sub.add_parser("discover", help="list git repos under a directory")
    p_disc.add_argument("input_dir")

    p_ex = sub.add_parser("extract", help="write the raw commit fact table")
    p_ex.add_argument("input_dir")
    p_ex.add_argument("--out", required=True)

    p_rank = sub.add_parser("rank", help="rank from persisted raw (no git)")
    p_rank.add_argument("scan")
    p_rank.add_argument("--as-of", default=None)

    p_flag = sub.add_parser("flag", help="flag founding patterns from persisted raw")
    p_flag.add_argument("scan")
    p_flag.add_argument("--as-of", required=True)

    p_scan = sub.add_parser(
        "scan",
        help="deterministic collect + headless Grok executive summary (use --no-analyze only for harness)",
    )
    p_scan.add_argument("input_dir")
    p_scan.add_argument("--out", required=True)
    p_scan.add_argument("--as-of", default=None)
    p_scan.add_argument(
        "--no-analyze",
        action="store_true",
        help="skip Grok (tests/harness only). Product scan always analyzes.",
    )
    p_scan.add_argument("--grok-bin", default=None)

    p_pack = sub.add_parser("pack", help="write auditor evidence packs from a scan")
    p_pack.add_argument("scan")

    p_an = sub.add_parser("analyze", help="run headless grok on packs (grok --prompt-file)")
    p_an.add_argument("scan")
    p_an.add_argument("--as-of", default=None)
    p_an.add_argument("--grok-bin", default=None)

    args = parser.parse_args(argv)
    if args.cmd == "discover":
        print(json.dumps(cmd_discover(Path(args.input_dir)), indent=2))
        return 0
    if args.cmd == "extract":
        print(json.dumps(cmd_extract(Path(args.input_dir), Path(args.out)), indent=2))
        return 0
    if args.cmd == "rank":
        print(json.dumps(cmd_rank(Path(args.scan), parse_as_of_arg(args.as_of)), indent=2))
        return 0
    if args.cmd == "flag":
        print(json.dumps(cmd_flag(Path(args.scan), parse_as_of_arg(args.as_of)), indent=2))
        return 0
    if args.cmd == "scan":
        print(
            json.dumps(
                cmd_scan(
                    Path(args.input_dir),
                    Path(args.out),
                    parse_as_of_arg(args.as_of),
                    analyze=not args.no_analyze,
                    grok_bin=args.grok_bin,
                ),
                indent=2,
            )
        )
        return 0
    if args.cmd == "pack":
        packs = cmd_pack(Path(args.scan))
        print(json.dumps({"packs": len(packs)}, indent=2))
        return 0
    if args.cmd == "analyze":
        out = Path(args.scan)
        reports = cmd_analyze(out, grok_bin=args.grok_bin)
        _write_report(out, parse_as_of_arg(args.as_of), reports)
        print(json.dumps({"analyzed": len(reports)}, indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
