"""JSON-only command line boundary.

Copyright 2026 Theo Georgiev (Naevum). SPDX-License-Identifier: Apache-2.0
"""

import argparse
import json
from pathlib import Path
import sys

from .model import MAX_BYTES, ScenarioError, identifier, load_scenario
from .service_export import completed_records, dumps_jsonl
from .simulator import InvariantError, simulate


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Bounded synthetic cluster simulation (unverified)")
    parser.add_argument("scenario", help="JSON file, or - for standard input")
    parser.add_argument("--export-jsonl", metavar="NEW_FILE", help="write synthetic completed service to a new file")
    parser.add_argument("--run-id", help="bounded caller-assigned run identity; required with export")
    args = parser.parse_args(argv)
    try:
        if bool(args.export_jsonl) != bool(args.run_id):
            raise ScenarioError("--export-jsonl and --run-id must be supplied together")
        if args.run_id is not None:
            identifier(args.run_id)
        if args.export_jsonl == "-":
            raise ScenarioError("export requires a new file path; stdout carries the run report")
        if args.scenario == "-":
            data = sys.stdin.buffer.read(MAX_BYTES + 1)
        else:
            with Path(args.scenario).open("rb") as stream:
                data = stream.read(MAX_BYTES + 1)
        result = simulate(load_scenario(data))
        if args.export_jsonl:
            text = dumps_jsonl(completed_records(result, args.run_id))
            # Exclusive creation preserves scenarios and existing exports.
            with Path(args.export_jsonl).open("x", encoding="utf-8") as stream:
                stream.write(text)
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return 1 if result["findings"] else 0
    except InvariantError as exc:
        print(json.dumps({"version": 1, "error": "invariant_failure", "detail": str(exc)}), file=sys.stderr)
        return 1
    except (ScenarioError, OSError) as exc:
        print(json.dumps({"version": 1, "error": "malformed_input_or_io", "detail": str(exc)}), file=sys.stderr)
        return 2
    except Exception:
        # Avoid leaking environment paths, data or a misleading partial result.
        print(json.dumps({"version": 1, "error": "internal_failure"}), file=sys.stderr)
        return 2
