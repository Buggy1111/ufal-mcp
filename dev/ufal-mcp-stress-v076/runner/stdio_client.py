"""Minimal MCP stdio client for UFAL MCP stress testing.

Spawns ufal-mcp jako subprocess, mluvi JSON-RPC 2.0 pres stdin/stdout
podle MCP specu. Bez zavislosti na mcp SDK -- chceme presne to, co
by udelal libovolny klient (Claude Code, Cline, atd.).
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from dataclasses import dataclass
from typing import Any


UFAL_MCP_BIN = "/home/buggy1111/dev/mcp-servers/ufal-mcp/.venv/bin/ufal-mcp"


@dataclass
class CallResult:
    ok: bool
    elapsed_s: float
    response: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    exception: str | None = None
    stderr_tail: str = ""


class UfalMcpClient:
    """Async stdio MCP client. Jeden subprocess, paralelni calls pres JSON-RPC ID."""

    def __init__(self, bin_path: str = UFAL_MCP_BIN, debug: bool = False):
        self.bin_path = bin_path
        self.debug = debug
        self.proc: asyncio.subprocess.Process | None = None
        self._next_id = 1
        self._pending: dict[int, asyncio.Future] = {}
        self._reader_task: asyncio.Task | None = None
        self._stderr_task: asyncio.Task | None = None
        self._stderr_buf: list[str] = []
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()

    async def start(self) -> None:
        env = {**os.environ, "PYTHONUNBUFFERED": "1"}
        self.proc = await asyncio.create_subprocess_exec(
            self.bin_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            limit=2**20,  # 1MB readline buffer — pro velke JSON-RPC odpovedi z UFAL
        )
        self._reader_task = asyncio.create_task(self._read_loop())
        self._stderr_task = asyncio.create_task(self._stderr_loop())
        await self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "ufal-stress-v076", "version": "0.1.0"},
            },
        )
        await self._send_raw({"jsonrpc": "2.0", "method": "notifications/initialized"})

    async def close(self) -> None:
        if self.proc and self.proc.returncode is None:
            try:
                self.proc.stdin.close()
            except Exception:
                pass
            try:
                await asyncio.wait_for(self.proc.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                self.proc.kill()
                await self.proc.wait()
        for t in (self._reader_task, self._stderr_task):
            if t and not t.done():
                t.cancel()

    async def _send_raw(self, msg: dict[str, Any]) -> None:
        async with self._lock:
            line = json.dumps(msg, ensure_ascii=False) + "\n"
            self.proc.stdin.write(line.encode("utf-8"))
            await self.proc.stdin.drain()
            if self.debug:
                sys.stderr.write(f">>> {line}")

    async def _read_loop(self) -> None:
        assert self.proc and self.proc.stdout
        while True:
            line = await self.proc.stdout.readline()
            if not line:
                for fut in list(self._pending.values()):
                    if not fut.done():
                        fut.set_exception(RuntimeError("MCP server stdout closed"))
                return
            try:
                msg = json.loads(line.decode("utf-8"))
            except Exception as e:
                if self.debug:
                    sys.stderr.write(f"!!! bad json: {line!r} ({e})\n")
                continue
            if self.debug:
                sys.stderr.write(f"<<< {line.decode('utf-8')}")
            mid = msg.get("id")
            if mid is not None and mid in self._pending:
                fut = self._pending.pop(mid)
                if not fut.done():
                    fut.set_result(msg)

    async def _stderr_loop(self) -> None:
        assert self.proc and self.proc.stderr
        while True:
            line = await self.proc.stderr.readline()
            if not line:
                return
            text = line.decode("utf-8", errors="replace")
            self._stderr_buf.append(text)
            if len(self._stderr_buf) > 200:
                self._stderr_buf = self._stderr_buf[-200:]

    def _stderr_tail(self, n: int = 20) -> str:
        return "".join(self._stderr_buf[-n:])

    async def _request(self, method: str, params: dict[str, Any], timeout: float = 180.0) -> dict[str, Any]:
        mid = self._next_id
        self._next_id += 1
        fut: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending[mid] = fut
        await self._send_raw(
            {"jsonrpc": "2.0", "id": mid, "method": method, "params": params}
        )
        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        finally:
            self._pending.pop(mid, None)

    async def list_tools(self) -> list[dict[str, Any]]:
        resp = await self._request("tools/list", {})
        return resp.get("result", {}).get("tools", [])

    async def call_tool(
        self, name: str, arguments: dict[str, Any], timeout: float = 180.0
    ) -> CallResult:
        loop = asyncio.get_event_loop()
        t0 = loop.time()
        try:
            resp = await self._request(
                "tools/call", {"name": name, "arguments": arguments}, timeout=timeout
            )
            elapsed = loop.time() - t0
            if "error" in resp:
                return CallResult(
                    ok=False,
                    elapsed_s=elapsed,
                    error=resp["error"],
                    stderr_tail=self._stderr_tail(),
                )
            result = resp.get("result", {})
            return CallResult(
                ok=not result.get("isError", False),
                elapsed_s=elapsed,
                response=result,
                stderr_tail=self._stderr_tail(),
            )
        except asyncio.TimeoutError:
            return CallResult(
                ok=False,
                elapsed_s=loop.time() - t0,
                exception=f"timeout after {timeout}s",
                stderr_tail=self._stderr_tail(),
            )
        except Exception as e:
            return CallResult(
                ok=False,
                elapsed_s=loop.time() - t0,
                exception=f"{type(e).__name__}: {e}",
                stderr_tail=self._stderr_tail(),
            )


def extract_tool_payload(result: CallResult) -> Any:
    """UFAL tools vraci dict -- FastMCP ho serializuje do result.content[0].text."""
    if not result.response:
        return None
    content = result.response.get("content", [])
    if not content:
        return None
    first = content[0]
    if first.get("type") == "text":
        try:
            return json.loads(first.get("text", ""))
        except (json.JSONDecodeError, TypeError):
            return first.get("text")
    return first


async def _smoke():
    async with UfalMcpClient(debug=False) as client:
        tools = await client.list_tools()
        print(f"Tools: {[t['name'] for t in tools]}")
        r = await client.call_tool(
            "extract_entities",
            {"text": "Jiri Pluharik bydli v Ostrave."},
            timeout=60.0,
        )
        print(f"ok={r.ok} elapsed={r.elapsed_s:.2f}s")
        payload = extract_tool_payload(r)
        if isinstance(payload, dict):
            print(f"entities={len(payload.get('entities', []))} lang={payload.get('detected_language')}")
        else:
            print(f"payload={payload!r}")


if __name__ == "__main__":
    asyncio.run(_smoke())
