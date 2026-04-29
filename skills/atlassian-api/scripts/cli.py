#!/usr/bin/env python3.12
"""Atlassian token management and resource access.

Usage:
    cli.py fetch <url> [--format text|json|html] [--refresh]
    cli.py page <domain> <pageId> [--format text|json|html] [--refresh]
    cli.py issue <domain> <issueKey> [--format text|json]
    cli.py search <query> [--domain <d>] [--title-only] [--limit N]
    cli.py sync <domain> <spaceKey>
    cli.py token {list|set|remove|test}

For detailed help on any subcommand, run:
    cli.py <command> --help
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Sequence

# Make sibling modules importable when this file is run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent))

import auth      # noqa: E402
import confluence  # noqa: E402
import jira      # noqa: E402
import urls      # noqa: E402


def _die(msg: str, code: int = 1) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return code


# --- token ---


def _cmd_token_list(_args: argparse.Namespace) -> int:
    rows = auth.list_tokens()
    if not rows:
        print("(no tokens stored)")
        return 0
    width = max(len(r.domain) for r in rows)
    print(f"{'DOMAIN':<{width}}  STATUS      LAST_TESTED")
    for r in rows:
        print(
            f"{r.domain:<{width}}  "
            f"{(r.status or 'unknown'):<10}  "
            f"{r.last_tested or '-'}"
        )
    return 0


def _cmd_token_set(args: argparse.Namespace) -> int:
    auth.set_token(args.domain, args.pat)
    print(f"Token stored for {auth.normalise_domain(args.domain)}")
    return 0


def _cmd_token_remove(args: argparse.Namespace) -> int:
    domain = auth.normalise_domain(args.domain)
    if auth.remove_token(args.domain):
        print(f"Removed token for {domain}")
        return 0
    return _die(f"No token stored for {domain}")


def _cmd_token_test(args: argparse.Namespace) -> int:
    try:
        status = auth.test_token(args.domain)
    except KeyError as exc:
        return _die(str(exc))
    domain = auth.normalise_domain(args.domain)
    print(f"{domain}: {status}")
    return 0 if status == "ok" else 1


# --- fetch / page / issue ---


def _print_page(page: confluence.Page, fmt: str) -> None:
    if fmt == "json":
        print(page.as_json())
    elif fmt == "html":
        print(page.body_html)
    else:
        print(page.as_text())


def _print_issue(issue: jira.JiraIssue, fmt: str, *, full: bool = False) -> None:
    if fmt == "json":
        print(issue.as_json())
    else:
        print(issue.as_text(max_comments=None if full else 10))


def _cmd_fetch(args: argparse.Namespace) -> int:
    resource = urls.classify(args.url)
    if resource.kind == "confluence_page":
        if not resource.page_id:
            return _die(
                f"Could not extract a page id from {args.url!r}; "
                "use 'page <domain> <pageId>' directly."
            )
        if not resource.host:
            return _die(f"URL has no host: {args.url!r}")
        page = confluence.fetch_page(
            resource.host, resource.page_id, refresh=args.refresh
        )
        _print_page(page, args.format)
        return 0
    if resource.kind == "jira_issue":
        if not resource.issue_key or not resource.host:
            return _die(f"Malformed Jira URL: {args.url!r}")
        if args.format == "html":
            return _die("--format html is not supported for Jira issues")
        issue = jira.fetch_issue(resource.host, resource.issue_key)
        _print_issue(
            issue,
            args.format if args.format != "html" else "text",
            full=getattr(args, "full", False),
        )
        return 0
    return _die(
        f"Unrecognised Atlassian URL: {args.url!r}. "
        "Supported path patterns: Confluence /pages/, /display/, /wiki/; "
        "Jira /browse/<KEY>-<N>."
    )


def _cmd_page(args: argparse.Namespace) -> int:
    page = confluence.fetch_page(args.domain, args.page_id, refresh=args.refresh)
    _print_page(page, args.format)
    return 0


def _cmd_issue(args: argparse.Namespace) -> int:
    issue = jira.fetch_issue(args.domain, args.issue_key)
    _print_issue(issue, args.format, full=args.full)
    return 0


def _cmd_search(args: argparse.Namespace) -> int:
    results = confluence.search_pages(
        args.query,
        domain=args.domain,
        title_only=args.title_only,
        limit=args.limit,
    )
    if not results:
        print("(no results)")
        return 0
    for p in results:
        print(f"{p.domain}  {p.page_id:>10}  {p.title}")
    return 0


def _cmd_sync(args: argparse.Namespace) -> int:
    count = confluence.sync_space(args.domain, args.space_key)
    print(f"Synced {count} page(s) from space {args.space_key} on {args.domain}")
    return 0


# --- parser ---


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="atlassian-api",
        description=(
            "Atlassian token manager, Confluence page cache, and Jira"
            " issue fetcher. For writes, JQL, CQL, and other operations,"
            " write Python against atlassian-python-api directly."
        ),
    )
    sub = p.add_subparsers(dest="command", required=True)

    # fetch
    f = sub.add_parser(
        "fetch",
        help="Fetch a Confluence page or Jira issue by URL",
        description=(
            "Classify an Atlassian URL and dispatch to the right handler."
            " Confluence pages go through the cache; Jira issues are"
            " fetched live every time."
        ),
    )
    f.add_argument("url")
    f.add_argument(
        "--format",
        choices=["text", "json", "html"],
        default="text",
        help="Output format (html is Confluence-only)",
    )
    f.add_argument(
        "--refresh",
        action="store_true",
        help="Force re-fetch Confluence body even if the cache looks fresh",
    )
    f.add_argument(
        "--full",
        action="store_true",
        help="Print all Jira comments (default shows only the last 10)",
    )
    f.set_defaults(func=_cmd_fetch)

    # page
    pg = sub.add_parser(
        "page",
        help="Fetch a Confluence page by (domain, pageId)",
    )
    pg.add_argument("domain")
    pg.add_argument("page_id")
    pg.add_argument(
        "--format", choices=["text", "json", "html"], default="text"
    )
    pg.add_argument("--refresh", action="store_true")
    pg.set_defaults(func=_cmd_page)

    # issue
    iss = sub.add_parser(
        "issue",
        help="Fetch a Jira issue by (domain, issueKey) — no caching",
    )
    iss.add_argument("domain")
    iss.add_argument("issue_key")
    iss.add_argument("--format", choices=["text", "json"], default="text")
    iss.add_argument(
        "--full",
        action="store_true",
        help="Print all comments (default shows only the last 10)",
    )
    iss.set_defaults(func=_cmd_issue)

    # search
    s = sub.add_parser(
        "search",
        help="Full-text search over the cached Confluence pages",
    )
    s.add_argument("query")
    s.add_argument("--domain", help="Limit search to one domain")
    s.add_argument(
        "--title-only",
        action="store_true",
        help="Search titles only (skip body text)",
    )
    s.add_argument("--limit", type=int, default=50)
    s.set_defaults(func=_cmd_search)

    # sync
    sy = sub.add_parser(
        "sync",
        help="Prime title index for a Confluence space",
    )
    sy.add_argument("domain")
    sy.add_argument("space_key")
    sy.set_defaults(func=_cmd_sync)

    # token
    tok = sub.add_parser("token", help="Manage Personal Access Tokens")
    tsub = tok.add_subparsers(dest="token_cmd", required=True)

    tsub.add_parser("list", help="List stored tokens").set_defaults(
        func=_cmd_token_list
    )

    t_set = tsub.add_parser("set", help="Store or update a PAT")
    t_set.add_argument("domain")
    t_set.add_argument("pat")
    t_set.set_defaults(func=_cmd_token_set)

    t_rm = tsub.add_parser("remove", help="Delete a stored PAT")
    t_rm.add_argument("domain")
    t_rm.set_defaults(func=_cmd_token_remove)

    t_test = tsub.add_parser("test", help="Probe a PAT against the server")
    t_test.add_argument("domain")
    t_test.set_defaults(func=_cmd_token_test)

    return p


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
