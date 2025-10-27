#!/usr/bin/env -S uv run -q
# /// script
# requires-python = ">=3.10"
# dependencies = ["requests"]
# ///
"""
stoat-wh: Manage and send messages via Stoat webhooks

Usage:
  stoat-wh get <url> | <id> <token> [--json]
  stoat-wh edit <url> | <id> <token> [--name <name>]
  stoat-wh delete <url> | <id> <token>
  stoat-wh send <url> | <id> <token> [options]

Options for 'send':
  -c, --content TEXT         Message content (overridden by stdin if piped)
  --username NAME            Masquerade display name
  --avatar URL               Masquerade avatar URL
  --flags INT                Message flag bitfield
  --reply ID [ID ...]        Message IDs to reply to
  --embed PATH|JSON [...]    Embed JSON string or file path (only one supported)
  --interactions PATH|JSON   Interactions JSON string or file path
  --debug                    Show raw API output and full error JSON

Environment:
  STOAT_API                  Override base API endpoint (default: https://stoat.chat/api/webhooks)

License:
  MIT License (c) 2025 bjornmorten
"""

import argparse
import json
import os
import sys
import uuid
from pathlib import Path
from typing import Any

import requests

BASE_URL = os.getenv("STOAT_API", "https://stoat.chat/api/webhooks")
TIMEOUT = 15

PROJECT_URL = "https://github.com/bjornmorten/stoat-wh"
USER_AGENT = f"stoat-wh/1.0 (+{PROJECT_URL})"


def parse_webhook_source(args: list[str]) -> str:
    """Return normalized webhook URL from <id> <token> or <url>."""
    if len(args) == 1:
        arg = args[0]
        if arg.startswith("http"):
            return arg.rstrip("/")
        print("Error: single argument must be a full webhook URL.", file=sys.stderr)
        sys.exit(1)
    elif len(args) == 2:
        wid, token = args
        return f"{BASE_URL}/{wid}/{token}"
    print("Error: provide either <url> or <id> <token>.", file=sys.stderr)
    sys.exit(1)


def safe_request(
    method: str, url: str, *, debug: bool = False, **kwargs: Any
) -> requests.Response:
    """Perform HTTP request and handle errors."""
    try:
        headers = {"User-Agent": USER_AGENT, **kwargs.pop("headers", {})}
        resp = requests.request(method, url, headers=headers, timeout=TIMEOUT, **kwargs)
        if not resp.ok:
            handle_error(resp, debug)
        else:
            if debug:
                print(json.dumps(resp.json(), indent=2, sort_keys=True))
        return resp
    except requests.RequestException as exc:
        print(f"Network error: {exc}", file=sys.stderr)
        sys.exit(2)


def handle_error(resp: requests.Response, debug: bool) -> None:
    """Decode and show friendly Stoat API error messages."""
    try:
        data = resp.json()
    except json.JSONDecodeError:
        print(f"HTTP {resp.status_code}: {resp.text}", file=sys.stderr)
        sys.exit(resp.status_code)
    if debug:
        print(json.dumps(data, indent=2), file=sys.stderr)
        sys.exit(resp.status_code)
    etype = data.get("type")
    msg = {
        "NotAuthenticated": "Invalid webhook token",
        "NotFound": "Webhook not found - check if it exists and if the ID is correct",
        "FailedValidation": f"Validation failed: {data.get('error', 'unknown reason')}.",
    }.get(etype, f"HTTP {resp.status_code}: {etype or resp.reason}")
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(resp.status_code)


def read_stdin() -> str | None:
    """Read text piped to stdin, if any."""
    if sys.stdin.isatty():
        return None
    text = sys.stdin.read().strip()
    return text or None


def maybe_json(value: str | None) -> Any:
    """Parse JSON or read from file path if exists."""
    if not value:
        return None
    p = Path(value)
    if p.exists():
        with p.open() as f:
            return json.load(f)
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise ValueError(f"{value!r} is neither a JSON file nor valid JSON: {e.msg}")


def cmd_get(url: str, *, json_output: bool, debug: bool) -> None:
    resp = safe_request("GET", url, debug=debug)
    data = resp.json()
    if json_output:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        print(f"Webhook ID : {data.get('id')}")
        print(f"Name       : {data.get('name')}")
        print(f"Creator    : {data.get('creator_id')}")
        print(f"Channel    : {data.get('channel_id')}")
        print(f"Permissions: {data.get('permissions')}")
        if "token" in data:
            print(f"Token      : {data['token']}")


def cmd_edit(url: str, *, name: str | None, debug: bool) -> None:
    payload = {"name": name} if name else {}
    safe_request("PATCH", url, json=payload, debug=debug)
    print("Webhook updated.")


def cmd_delete(url: str, *, debug: bool) -> None:
    safe_request("DELETE", url, debug=debug)
    print("Webhook deleted.")


def cmd_send(
    url: str,
    *,
    content: str | None,
    username: str | None,
    avatar: str | None,
    flags: int | None,
    replies: list[str] | None,
    embeds: list[str] | None,
    interactions: str | None,
    debug: bool,
) -> None:
    """Send a message via Stoat webhook."""
    text = read_stdin() or content
    if not text and not embeds:
        print("Error: need content, stdin, or embeds.", file=sys.stderr)
        sys.exit(6)

    data: dict[str, Any] = {}
    if text:
        data["content"] = text
    if flags is not None:
        data["flags"] = flags
    if replies:
        data["replies"] = [{"id": r, "mention": False} for r in replies]
    if embeds:
        try:
            embed_data = [maybe_json(e) for e in embeds]
        except ValueError as err:
            print(f"Error parsing embed: {err}", file=sys.stderr)
            sys.exit(5)
        data["embeds"] = embed_data
    if interactions:
        data["interactions"] = maybe_json(interactions)

    if username or avatar:
        data["masquerade"] = {}
        if username:
            data["masquerade"]["name"] = username
        if avatar:
            data["masquerade"]["avatar"] = avatar

    headers = {"Idempotency-Key": str(uuid.uuid4())}
    safe_request("POST", url, json=data, headers=headers, debug=debug)
    print("Message sent.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="stoat-wh", description="Stoat webhook CLI.")
    parser.add_argument("--debug", action="store_true", help="Show raw JSON responses.")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def common(s: argparse.ArgumentParser) -> None:
        s.add_argument("args", nargs="+", help="Either <url> or <id> <token>.")

    g = sub.add_parser("get", help="Fetch webhook info.")
    common(g)
    g.add_argument("--json", action="store_true")

    e = sub.add_parser("edit", help="Edit webhook.")
    common(e)
    e.add_argument("--name")

    d = sub.add_parser("delete", help="Delete webhook.")
    common(d)

    s = sub.add_parser("send", help="Send a message.")
    common(s)
    s.add_argument("--content", "-c", help="Message text (stdin overrides this).")
    s.add_argument("--username", help="Masquerade name.")
    s.add_argument("--avatar", help="Masquerade avatar URL.")
    s.add_argument("--flags", type=int, help="Message flags integer.")
    s.add_argument("--reply", nargs="*", help="Message IDs to reply to.")
    s.add_argument("--embed", nargs="*", help="Embed JSON string or file path.")
    s.add_argument("--interactions", help="Interactions JSON string or file path.")

    return parser


def main() -> None:
    parser = build_parser()
    ns = parser.parse_args()
    url = parse_webhook_source(ns.args)

    match ns.cmd:
        case "get":
            cmd_get(url, json_output=ns.json, debug=ns.debug)
        case "edit":
            cmd_edit(url, name=ns.name, debug=ns.debug)
        case "delete":
            cmd_delete(url, debug=ns.debug)
        case "send":
            cmd_send(
                url,
                content=ns.content,
                username=ns.username,
                avatar=ns.avatar,
                flags=ns.flags,
                replies=ns.reply,
                embeds=ns.embed,
                interactions=ns.interactions,
                debug=ns.debug,
            )
        case _:
            parser.print_help()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
