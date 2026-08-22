from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from repoauditor.auditor.grok_cli import ANALYZE_TIMEOUT, EXPLORE_MAX_TURNS
from repoauditor.dates import parse_as_of
from repoauditor.auditor.run import cmd_analyze, cmd_pack, unfinished_reports
from repoauditor.pipeline import (
    cmd_discover,
    cmd_extract,
    cmd_flag,
    cmd_rank,
    cmd_scan,
    parse_as_of_arg,
    _write_report,
)


def _add_headless_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--as-of", default=None)
    parser.add_argument("--grok-bin", default=None)
    parser.add_argument(
        "--timeout",
        type=int,
        default=ANALYZE_TIMEOUT,
        help="seconds to wait for each grok process (wall clock, not turns; default 86400)",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=EXPLORE_MAX_TURNS,
        help="grok --max-turns per repo (each tool call counts; default 512)",
    )
    parser.add_argument(
        "--json-schema",
        action="store_true",
        help="pass grok --json-schema (off by default; large cold prompt)",
    )
    parser.add_argument(
        "--no-json-schema",
        action="store_true",
        help="ignored; schema is off unless --json-schema",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="grok --model for analyze (use a JSON-capable model if the local one cannot)",
    )
    parser.add_argument(
        "--subagents",
        action="store_true",
        help="allow mapper/investigator child agents (cloud only; fights a local GPU)",
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="repoauditor",
        description="Scan a local git repo or a folder of clones.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_disc = sub.add_parser("discover", help="list git repos under a directory")
    p_disc.add_argument("input_dir")

    p_ex = sub.add_parser("extract", help="write the raw commit fact table")
    p_ex.add_argument("input_dir")
    p_ex.add_argument("--out", required=True)
    p_ex.add_argument(
        "--since",
        default=None,
        help="UTC start date YYYY-MM-DD; drop older commits (fork cutoff)",
    )

    p_rank = sub.add_parser("rank", help="rank from persisted raw (no git)")
    p_rank.add_argument("scan")
    p_rank.add_argument("--as-of", default=None)

    p_flag = sub.add_parser("flag", help="flag founding patterns from persisted raw")
    p_flag.add_argument("scan")
    p_flag.add_argument("--as-of", required=True)

    p_scan = sub.add_parser(
        "scan",
        help="deterministic collect + per-repo Grok inspect (use --no-analyze only for harness)",
    )
    p_scan.add_argument("input_dir")
    p_scan.add_argument("--out", required=True)
    p_scan.add_argument("--as-of", default=None)
    p_scan.add_argument(
        "--since",
        default=None,
        help="UTC start date YYYY-MM-DD; drop older commits (fork cutoff)",
    )
    p_scan.add_argument(
        "--no-analyze",
        action="store_true",
        help="skip Grok (tests/harness only). Product scan always analyzes.",
    )
    p_scan.add_argument("--grok-bin", default=None)
    p_scan.add_argument(
        "--timeout",
        type=int,
        default=ANALYZE_TIMEOUT,
        help="seconds to wait for each grok process (wall clock, not turns; default 86400)",
    )
    p_scan.add_argument(
        "--max-turns",
        type=int,
        default=EXPLORE_MAX_TURNS,
        help="grok --max-turns per repo (each tool call counts; default 512)",
    )
    p_scan.add_argument(
        "--json-schema",
        action="store_true",
        help="pass grok --json-schema (off by default; large cold prompt)",
    )
    p_scan.add_argument(
        "--no-json-schema",
        action="store_true",
        help="ignored; schema is off unless --json-schema",
    )
    p_scan.add_argument(
        "--model",
        default=None,
        help="grok --model for analyze (use a JSON-capable model if the local one cannot)",
    )
    p_scan.add_argument(
        "--subagents",
        action="store_true",
        help="allow mapper/investigator child agents (cloud only; fights a local GPU)",
    )
    p_scan.add_argument(
        "--force",
        action="store_true",
        help="re-run Grok even when a finished report already exists",
    )

    p_pack = sub.add_parser("pack", help="write auditor evidence packs from a scan")
    p_pack.add_argument("scan")

    p_an = sub.add_parser("analyze", help="run headless grok on packs (grok --prompt-file)")
    p_an.add_argument("scan")
    _add_headless_flags(p_an)
    p_an.add_argument(
        "--force",
        action="store_true",
        help="re-run Grok even when a finished report already exists",
    )

    p_rep = sub.add_parser(
        "report",
        help="rebuild HTML from existing analyze JSON (no Grok)",
    )
    p_rep.add_argument("scan")
    p_rep.add_argument("--as-of", default=None)

    p_retry = sub.add_parser(
        "retry",
        help="re-run Grok only on repos with no finished inspector report",
    )
    p_retry.add_argument("scan")
    _add_headless_flags(p_retry)
    p_retry.add_argument(
        "--list",
        action="store_true",
        help="print unfinished repo ids and exit (no Grok)",
    )

    args = parser.parse_args(argv)
    if args.cmd == "discover":
        print(json.dumps(cmd_discover(Path(args.input_dir)), indent=2))
        return 0
    if args.cmd == "extract":
        print(
            json.dumps(
                cmd_extract(
                    Path(args.input_dir),
                    Path(args.out),
                    since=parse_as_of(args.since) if args.since else None,
                ),
                indent=2,
            )
        )
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
                    since=parse_as_of(args.since) if args.since else None,
                    grok_bin=args.grok_bin,
                    timeout=args.timeout,
                    max_turns=args.max_turns,
                    json_schema=args.json_schema,
                    model=args.model,
                    subagents=args.subagents,
                    force=args.force,
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
        reports = cmd_analyze(
            out,
            grok_bin=args.grok_bin,
            timeout=args.timeout,
            max_turns=args.max_turns,
            json_schema=args.json_schema,
            model=args.model,
            subagents=args.subagents,
            force=args.force,
        )
        _write_report(out, parse_as_of_arg(args.as_of), reports)
        print(json.dumps({"analyzed": len(reports)}, indent=2))
        return 0
    if args.cmd == "report":
        out = Path(args.scan)
        path = _write_report(out, parse_as_of_arg(args.as_of), None)
        print(json.dumps({"report": str(path)}, indent=2))
        return 0
    if args.cmd == "retry":
        out = Path(args.scan)
        pending = unfinished_reports(out)
        if args.list:
            print(json.dumps({"unfinished": pending, "count": len(pending)}, indent=2))
            return 0
        print(f"retry {len(pending)} unfinished", file=sys.stderr, flush=True)
        for row in pending:
            print(f"retry {row['repo_id']} ({row['reason']})", file=sys.stderr, flush=True)
        reports = cmd_analyze(
            out,
            grok_bin=args.grok_bin,
            timeout=args.timeout,
            max_turns=args.max_turns,
            json_schema=args.json_schema,
            model=args.model,
            subagents=args.subagents,
        )
        path = _write_report(out, parse_as_of_arg(args.as_of), reports)
        leftover = unfinished_reports(out)
        print(
            json.dumps(
                {
                    "retried": len(pending),
                    "still_unfinished": [row["repo_id"] for row in leftover],
                    "report": str(path),
                },
                indent=2,
            )
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
