#!/usr/bin/env python3.12
"""Unified patch entry point. Routes by file extension."""

import argparse
import importlib
import json
import os
import sys


_PATCHERS = {
    ".docx": "docx.patch",
}


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Patch Office documents via JSON instructions.",
    )
    parser.add_argument("input", help="Input file (.docx)")
    parser.add_argument(
        "instructions", help="Instructions JSON file",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file (default: overwrite input)",
    )
    args = parser.parse_args()

    ext = os.path.splitext(args.input)[1].lower()
    module_name = _PATCHERS.get(ext)
    if module_name is None:
        print(f"Unsupported format: {ext}", file=sys.stderr)
        sys.exit(1)

    with open(args.instructions, encoding="utf-8") as f:
        instructions = json.load(f)

    module = importlib.import_module(module_name)
    count = module.patch(args.input, instructions, args.output)
    out = args.output or args.input
    print(f"Applied {count} instructions → {out}")


if __name__ == "__main__":
    main()
