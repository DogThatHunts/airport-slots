#!/usr/bin/env python3
"""Entrypoint for the local cron / Claude Code routine.

    python run.py            # run the pipeline, write state/last_run.json
    python run.py --summary  # print the last run summary (for the phone routine)

Exit code 2 signals "needs attention" so a wrapper/routine can decide to notify.
"""
from __future__ import annotations

import json
import sys

import yaml

from src.pipeline import STATE, run


def main() -> int:
    if "--summary" in sys.argv:
        try:
            with open(STATE) as f:
                print(f.read())
        except FileNotFoundError:
            print("{}")
        return 0

    with open("config/sources.yaml") as f:
        cfg = yaml.safe_load(f)

    summary = run(cfg)
    print(json.dumps(summary, indent=2))
    return 2 if summary["needs_attention"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
