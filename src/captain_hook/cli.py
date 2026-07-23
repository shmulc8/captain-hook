#!/usr/bin/env python3
"""CLI entry point for captain-hook."""

from __future__ import annotations

import argparse
import sys

from .engine import Engine

VERSION = "1.0.0"


def main():
    engine = Engine()

    parser = argparse.ArgumentParser(
        description="captain-hook: Universal lifecycle hooks dispatcher for AI coding agents."
    )
    subparsers = parser.add_subparsers(dest="subcommand")

    # init
    init_parser = subparsers.add_parser("init", help="Initialize agent hook configurations.")
    init_parser.add_argument(
        "--agent",
        choices=["all", "cursor", "windsurf", "claude", "aider", "antigravity"],
        default="all",
        help="Target coding agent to generate hooks for (default: all)",
    )

    # dispatch
    dispatch_parser = subparsers.add_parser("dispatch", help="Dispatch a hook event.")
    dispatch_parser.add_argument("event", help="Canonical or agent event name")

    args = parser.parse_args()

    if args.subcommand == "init":
        engine.init_agent_configs(args.agent, ".")
        sys.exit(0)
    elif args.subcommand == "dispatch":
        code = engine.dispatch_from_stdin(args.event)
        sys.exit(code)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
