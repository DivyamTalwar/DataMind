#!/usr/bin/env python3
"""Thin Codex MCP adapter for the DataMind v1 runtime."""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

PLUGIN_ROOT = Path(__file__).resolve().parents[1]

def repo_root() -> Path:
    configured = os.environ.get("DATAMIND_REPO_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    marker = PLUGIN_ROOT / ".datamind-repo-root"
    if marker.is_file():
        value = marker.read_text(encoding="utf-8").splitlines()[0].strip()
        if value:
            return Path(value).expanduser().resolve()
    return PLUGIN_ROOT.parents[1].resolve()

ROOT = repo_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SERVER_NAME = "datamind-context"
SERVER_VERSION = "1.0.0"
PROTOCOL_VERSION = "2025-06-18"

TOOLS: dict[str, dict[str, Any]] = {
    "datamind_ask": {
        "description": "Ask DataMind RetrieveAgent to answer from the active profile.",
        "inputSchema": {"type": "object", "required": ["question"], "properties": {
            "question": {"type": "string"}, "profile": {"type": "string", "default": "default"}, "session_id": {"type": "string"}}}},
    "datamind_store": {
        "description": "Ask DataMind StoreAgent to persist information in the active profile.",
        "inputSchema": {"type": "object", "required": ["message"], "properties": {
            "message": {"type": "string"}, "profile": {"type": "string", "default": "default"}, "session_id": {"type": "string"}}}},
    "datamind_use_folder": {
        "description": "Add a file or directory to the active DataMind knowledge base.",
        "inputSchema": {"type": "object", "required": ["path"], "properties": {
            "path": {"type": "string"}, "profile": {"type": "string", "default": "default"}, "recursive": {"type": "boolean", "default": True}}}},
    "datamind_rag_query": {
        "description": "Search the active profile knowledge base with vector RAG.",
        "inputSchema": {"type": "object", "required": ["query"], "properties": {
            "query": {"type": "string"}, "profile": {"type": "string", "default": "default"}, "top_k": {"type": "integer", "minimum": 1, "maximum": 50, "default": 5}}}},
    "datamind_graph_query": {
        "description": "Ask RetrieveAgent to answer a relationship question with graph tools.",
        "inputSchema": {"type": "object", "required": ["query"], "properties": {
            "query": {"type": "string"}, "profile": {"type": "string", "default": "default"}}}},
    "datamind_remember": {
        "description": "Save a durable preference, decision or fact to DataMind memory.",
        "inputSchema": {"type": "object", "required": ["content"], "properties": {
            "content": {"type": "string"}, "kind": {"type": "string", "default": "fact"}, "scope": {"type": "string", "enum": ["global", "profile", "session"], "default": "profile"}, "profile": {"type": "string", "default": "default"}, "session_id": {"type": "string"}}}},
    "datamind_list_profiles": {
        "description": "List profiles in the configured DataMind data root.",
        "inputSchema": {"type": "object", "properties": {}}},
    "datamind_status": {
        "description": "Show the active profile and DataMind capability status.",
        "inputSchema": {"type": "object", "properties": {"profile": {"type": "string", "default": "default"}}}},
}

def profile_name(args: dict[str, Any]) -> str:
    value = str(args.get("profile") or "default").strip()
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-"
    if not value or value in {".", ".."} or any(char not in allowed for char in value):
        raise ValueError("profile must contain only letters, numbers, '.', '_' or '-'")
    return value

async def execute(name: str, args: dict[str, Any]) -> dict[str, Any]:
    from datamind.agent import build_datamind
    from datamind.config import Settings
    from datamind.core.context import RequestContext
    from datamind.core.logging import bind_context

    profile = profile_name(args)
    settings = Settings()
    settings.data.profile = profile
    system = await build_datamind(settings)
    context = RequestContext(
        session_id=str(args.get("session_id") or "codex"),
        profile=profile,
        user_id="codex",
    )
    try:
        with bind_context(context):
            if name == "datamind_ask":
                return await system.query(str(args["question"]))
            if name == "datamind_store":
                return await system.ingest(str(args["message"]))
            if name == "datamind_use_folder":
                spec = system.store.tools.get("kb_add_path")
                return await spec.handler(path=str(args["path"]), recursive=bool(args.get("recursive", True)))
            if name == "datamind_rag_query":
                spec = system.retrieve.tools.get("kb_search")
                return await spec.handler(query=str(args["query"]), top_k=int(args.get("top_k", 5)))
            if name == "datamind_graph_query":
                return await system.query("Answer using the knowledge graph and relationship tools where useful: " + str(args["query"]))
            if name == "datamind_remember":
                spec = system.store.tools.get("memory_save")
                return await spec.handler(content=str(args["content"]), kind=str(args.get("kind", "fact")), scope=str(args.get("scope", "profile")), session_id=args.get("session_id"))
            if name == "datamind_status":
                return {"profile": profile, "data_dir": str(settings.data.data_dir), "storage_dir": str(settings.data.storage_dir), "warmup": await system.warmup()}
            raise ValueError(f"unknown tool: {name}")
    finally:
        await system.aclose()

def list_profiles() -> dict[str, Any]:
    configured = os.environ.get("DATAMIND_DATA_ROOT", "").strip()
    base = Path(configured).expanduser() if configured else ROOT
    root = base / "data" / "profiles"
    profiles = sorted(path.name for path in root.iterdir() if path.is_dir()) if root.is_dir() else []
    return {"profiles": profiles, "data_root": str(root)}

def rpc_result(request_id: Any, value: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": value}

def tool_result(request_id: Any, value: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False, indent=2)}], "structuredContent": value}}

def error(request_id: Any, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": {"isError": True, "content": [{"type": "text", "text": message}]}}

def handle(message: dict[str, Any]) -> dict[str, Any] | None:
    request_id = message.get("id")
    if request_id is None:
        return None
    method = message.get("method")
    params = message.get("params") or {}
    try:
        if method == "initialize":
            return rpc_result(request_id, {"protocolVersion": params.get("protocolVersion", PROTOCOL_VERSION), "capabilities": {"tools": {}}, "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION}})
        if method == "ping":
            return rpc_result(request_id, {})
        if method == "tools/list":
            return rpc_result(request_id, {"tools": [{"name": name, **spec} for name, spec in TOOLS.items()]})
        if method == "tools/call":
            name = str(params.get("name") or "")
            if name == "datamind_list_profiles":
                return tool_result(request_id, list_profiles())
            return tool_result(request_id, asyncio.run(execute(name, params.get("arguments") or {})))
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": f"Method not found: {method}"}}
    except Exception as exc:
        return error(request_id, f"{type(exc).__name__}: {exc}")

def main() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            reply = handle(json.loads(line))
        except json.JSONDecodeError as exc:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": str(exc)}}
        if reply is not None:
            print(json.dumps(reply, ensure_ascii=False, separators=(",", ":")), flush=True)

if __name__ == "__main__":
    main()
