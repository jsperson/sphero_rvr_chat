"""MCP client for connecting to sphero_rvr_mcp server."""

import asyncio
import json
import subprocess
import sys
from typing import Any


class MCPClient:
    """Simple MCP client that communicates via stdio with the MCP server."""

    def __init__(self, command: list[str]):
        self.command = command
        self.process: subprocess.Popen | None = None
        self._request_id = 0
        self._lock = asyncio.Lock()

    async def start(self) -> bool:
        """Start the MCP server process."""
        try:
            self.process = subprocess.Popen(
                self.command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )

            # Send initialize request
            response = await self._request("initialize", {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "rvr-chat", "version": "0.1.0"}
            })

            if response and "result" in response:
                # Send initialized notification
                await self._notify("notifications/initialized", {})
                return True
            return False

        except Exception as e:
            print(f"Failed to start MCP server: {e}", file=sys.stderr)
            return False

    async def stop(self) -> None:
        """Stop the MCP server process."""
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None

    async def list_tools(self) -> list[dict[str, Any]]:
        """Get available tools from the MCP server."""
        response = await self._request("tools/list", {})
        if response and "result" in response:
            return response["result"].get("tools", [])
        return []

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """Call a tool on the MCP server."""
        response = await self._request("tools/call", {
            "name": name,
            "arguments": arguments
        })

        if response and "result" in response:
            content = response["result"].get("content", [])
            if content and len(content) > 0:
                # Return the text content
                text = content[0].get("text", "{}")
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    return {"result": text}

        if response and "error" in response:
            return {"error": response["error"].get("message", "Unknown error")}

        return {"error": "No response from MCP server"}

    async def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """Send a JSON-RPC request and wait for response."""
        if not self.process or not self.process.stdin or not self.process.stdout:
            return None

        async with self._lock:
            self._request_id += 1
            request = {
                "jsonrpc": "2.0",
                "id": self._request_id,
                "method": method,
                "params": params,
            }

            try:
                # Write request
                request_json = json.dumps(request)
                self.process.stdin.write(request_json + "\n")
                self.process.stdin.flush()

                # Read response (with timeout), skipping non-JSON lines
                loop = asyncio.get_event_loop()
                start_time = asyncio.get_event_loop().time()
                timeout = 30.0

                while True:
                    remaining = timeout - (asyncio.get_event_loop().time() - start_time)
                    if remaining <= 0:
                        raise asyncio.TimeoutError()

                    response_line = await asyncio.wait_for(
                        loop.run_in_executor(None, self.process.stdout.readline),
                        timeout=remaining
                    )

                    if not response_line:
                        return None

                    response_line = response_line.strip()
                    if not response_line:
                        continue

                    # Try to parse as JSON
                    if response_line.startswith("{"):
                        try:
                            return json.loads(response_line)
                        except json.JSONDecodeError:
                            continue
                    # Skip non-JSON lines (server startup messages, logs, etc.)

            except asyncio.TimeoutError:
                print("MCP request timed out", file=sys.stderr)
                return None
            except Exception as e:
                print(f"MCP request error: {e}", file=sys.stderr)
                return None

    async def _notify(self, method: str, params: dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        if not self.process or not self.process.stdin:
            return

        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }

        try:
            notification_json = json.dumps(notification)
            self.process.stdin.write(notification_json + "\n")
            self.process.stdin.flush()
        except Exception as e:
            print(f"MCP notification error: {e}", file=sys.stderr)


def convert_tools_to_ollama(mcp_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert MCP tool definitions to Ollama tool format."""
    ollama_tools = []

    for tool in mcp_tools:
        ollama_tool = {
            "type": "function",
            "function": {
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("inputSchema", {"type": "object", "properties": {}}),
            }
        }
        ollama_tools.append(ollama_tool)

    return ollama_tools
