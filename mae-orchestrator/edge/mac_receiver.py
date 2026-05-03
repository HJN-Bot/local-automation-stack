#!/usr/bin/env python3
"""
Mac-side receiver for the tiny EC2 Discord edge.

Endpoints:
  GET  /health
  POST /submit
  GET  /result?message_id=...
"""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from pyairtable import Api

from edge.common import append_event, load_dotenv_file, load_state, now_ms, save_state


MAE_TABLE = "tblvaXhvNxZgKE4SQ"
MAX_CONTENT_BYTES = 64 * 1024


def _table():
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    table_id = os.getenv("AIRTABLE_TABLE_ID", MAE_TABLE)
    if not api_key or not base_id:
        raise RuntimeError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID are required")
    return Api(api_key).table(base_id, table_id)


def _secret() -> str:
    value = os.getenv("EDGE_SHARED_SECRET")
    if not value:
        raise RuntimeError("EDGE_SHARED_SECRET is required")
    return value


def _json_response(handler: BaseHTTPRequestHandler, status: int, payload: dict) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length <= 0:
        return {}
    if length > MAX_CONTENT_BYTES:
        raise ValueError("request body too large")
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


def _authorized(handler: BaseHTTPRequestHandler) -> bool:
    expected = f"Bearer {_secret()}"
    return handler.headers.get("Authorization") == expected


def submit_task(payload: dict) -> dict:
    message_id = str(payload.get("message_id") or "").strip()
    task_type = str(payload.get("task_type") or "research").strip()
    content = str(payload.get("content") or "").strip()
    channel_id = str(payload.get("channel_id") or "").strip()
    author = str(payload.get("author") or "").strip()

    if not message_id:
        raise ValueError("message_id is required")
    if not content:
        raise ValueError("content is required")

    edge_header = (
        "[Discord Edge]\n"
        f"message_id: {message_id}\n"
        f"channel_id: {channel_id or '-'}\n"
        f"author: {author or '-'}\n\n"
    )

    record = _table().create(
        {
            "Task Type": task_type,
            "Content": edge_header + content,
            "Status": "pending",
        }
    )
    task_id = record["id"]
    state = load_state()
    state.setdefault("messages", {})[message_id] = {
        "task_id": task_id,
        "task_type": task_type,
        "channel_id": channel_id,
        "author": author,
        "received_at_ms": now_ms(),
    }
    save_state(state)
    append_event("submit", message_id=message_id, task_id=task_id, task_type=task_type)
    return {"ok": True, "message_id": message_id, "task_id": task_id, "status": "accepted"}


def result_for(message_id: str) -> dict:
    state = load_state()
    entry = state.get("messages", {}).get(message_id)
    if not entry:
        return {"ok": False, "message_id": message_id, "status": "unknown"}

    task_id = entry["task_id"]
    row = _table().get(task_id)
    fields = row.get("fields", {})
    status = fields.get("Status", "unknown")
    payload = {
        "ok": True,
        "message_id": message_id,
        "task_id": task_id,
        "status": status,
    }
    if status == "done":
        payload["result"] = fields.get("Result", "")
    elif status == "failed":
        payload["error"] = fields.get("Error", "")
    return payload


class EdgeHandler(BaseHTTPRequestHandler):
    server_version = "MAEEdgeReceiver/0.1"

    def log_message(self, fmt: str, *args) -> None:
        append_event("http", client=self.client_address[0], message=fmt % args)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            _json_response(self, 200, {"ok": True, "service": "mae-edge-receiver", "ts_ms": now_ms()})
            return

        if parsed.path == "/result":
            if not _authorized(self):
                _json_response(self, 401, {"ok": False, "error": "unauthorized"})
                return
            message_id = parse_qs(parsed.query).get("message_id", [""])[0]
            _json_response(self, 200, result_for(message_id))
            return

        _json_response(self, 404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/submit":
            _json_response(self, 404, {"ok": False, "error": "not_found"})
            return
        if not _authorized(self):
            _json_response(self, 401, {"ok": False, "error": "unauthorized"})
            return
        try:
            payload = _read_json(self)
            _json_response(self, 202, submit_task(payload))
        except Exception as exc:
            append_event("submit_error", error=f"{type(exc).__name__}: {exc}")
            _json_response(self, 400, {"ok": False, "error": str(exc)})


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MAE Mac-side Discord edge receiver")
    parser.add_argument("--host", default=os.getenv("EDGE_RECEIVER_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("EDGE_RECEIVER_PORT", "18888")))
    args = parser.parse_args()

    load_dotenv_file()
    _secret()
    server = ThreadingHTTPServer((args.host, args.port), EdgeHandler)
    append_event("receiver_start", host=args.host, port=args.port)
    print(f"[edge-receiver] listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()

