#!/usr/bin/env python3.12
"""Unified scrape entry point. Routes by file extension."""

import argparse
import json
import os
import sys


_EXTRACTORS = {
    ".pptx": "scrape_pptx",
    ".docx": "scrape_docx",
    ".xlsx": "scrape_xlsx",
    ".pdf": "scrape_pdf",
}


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Scrape Office documents into flat JSON.",
    )
    parser.add_argument("input", help="Input file (.docx, .pptx)")
    parser.add_argument(
        "-o", "--output", help="Output .json (default: stdout)",
    )
    args = parser.parse_args()

    ext = os.path.splitext(args.input)[1].lower()
    module_name = _EXTRACTORS.get(ext)
    if module_name is None:
        print(f"Unsupported format: {ext}", file=sys.stderr)
        sys.exit(1)

    module = __import__(module_name)
    result = module.extract(args.input)
    out = json.dumps(result, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(out)
    else:
        print(out)


if __name__ == "__main__":
    main()
