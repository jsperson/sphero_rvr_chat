"""Command-line interface for Sphero RVR Chat."""

import asyncio
import sys
from typing import Any

import ollama
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from . import __version__
from .config import get_config_dir, load_config
from .mcp_client import MCPClient, convert_tools_to_ollama
from .memory import ConversationMemory
from .system_prompt import get_system_prompt


# CLI colors
STYLE = Style.from_dict({
    "prompt": "#00aa00 bold",
    "assistant": "#0088ff",
    "tool": "#888888 italic",
    "error": "#ff0000 bold",
})


class RVRChat:
    """Main chat application."""

    def __init__(self):
        self.config = load_config()
        self.memory = ConversationMemory(max_messages=self.config.get("max_history", 100))
        self.mcp_client: MCPClient | None = None
        self.tools: list[dict[str, Any]] = []
        self.ollama_tools: list[dict[str, Any]] = []
        self.running = False

    async def start(self) -> bool:
        """Initialize the chat application."""
        print(f"Sphero RVR Chat v{__version__}")
        print("=" * 40)

        # Check Ollama is running
        print("Checking Ollama...", end=" ", flush=True)
        try:
            models = ollama.list()
            print("OK")
        except Exception as e:
            print(f"FAILED\nError: {e}")
            print("\nMake sure Ollama is running: ollama serve")
            return False

        # Check model is available
        model = self.config.get("model", "qwen2.5:1.5b")
        model_names = [m.get("name", "").split(":")[0] for m in models.get("models", [])]
        base_model = model.split(":")[0]

        if base_model not in model_names and model not in [m.get("name") for m in models.get("models", [])]:
            print(f"Model '{model}' not found. Pulling...", flush=True)
            try:
                ollama.pull(model)
                print(f"Model '{model}' ready")
            except Exception as e:
                print(f"Failed to pull model: {e}")
                return False
        else:
            print(f"Model: {model}")

        # Start MCP server
        print("Starting MCP server...", end=" ", flush=True)
        mcp_command = self.config.get("mcp_command", ["sphero-rvr-mcp"])
        self.mcp_client = MCPClient(mcp_command)

        if not await self.mcp_client.start():
            print("FAILED")
            print("Could not start MCP server. Check sphero-rvr-mcp is installed.")
            return False
        print("OK")

        # Get available tools
        print("Loading tools...", end=" ", flush=True)
        self.tools = await self.mcp_client.list_tools()
        self.ollama_tools = convert_tools_to_ollama(self.tools)
        print(f"OK ({len(self.tools)} tools)")

        # Initialize conversation with system prompt
        self.memory.add_message("system", get_system_prompt())

        # Auto-connect to RVR if configured
        if self.config.get("auto_connect_rvr", True):
            print("Connecting to RVR...", end=" ", flush=True)
            result = await self.mcp_client.call_tool("connect", {})
            if result.get("success"):
                print("OK")
                # Get battery status
                battery = await self.mcp_client.call_tool("get_battery_status", {})
                if battery.get("success"):
                    print(f"Battery: {battery.get('battery_percentage', '?')}%")
            else:
                print(f"FAILED ({result.get('error', 'unknown')})")
                print("You can connect manually with: connect")

        print("=" * 40)
        print("Type /help for commands, /quit to exit\n")
        return True

    async def stop(self) -> None:
        """Shutdown the chat application."""
        if self.mcp_client:
            # Disconnect RVR
            await self.mcp_client.call_tool("disconnect", {})
            await self.mcp_client.stop()

    async def handle_command(self, command: str) -> bool:
        """Handle slash commands. Returns True if command was handled."""
        parts = command[1:].split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        if cmd in ("quit", "exit", "q"):
            self.running = False
            return True

        elif cmd == "help":
            print("""
Commands:
  /help              - Show this help
  /quit, /exit, /q   - Exit the chat
  /save [name]       - Save conversation
  /load <name>       - Load conversation
  /list              - List saved conversations
  /delete <name>     - Delete saved conversation
  /clear             - Clear conversation history
  /status            - Show RVR status
  /connect           - Connect to RVR
  /disconnect        - Disconnect from RVR
  /tools             - List available tools
  /model [name]      - Show or change model
""")
            return True

        elif cmd == "save":
            name = args.strip() if args else None
            filepath = self.memory.save(name)
            print(f"Saved to: {filepath}")
            return True

        elif cmd == "load":
            if not args:
                print("Usage: /load <name>")
                return True
            if self.memory.load(args.strip()):
                print(f"Loaded conversation: {args.strip()}")
            else:
                print(f"Conversation not found: {args.strip()}")
            return True

        elif cmd == "list":
            sessions = self.memory.list_saved()
            if not sessions:
                print("No saved conversations")
            else:
                print("Saved conversations:")
                for s in sessions[:10]:
                    print(f"  {s['name']} ({s['messages']} messages, {s['created'][:10]})")
            return True

        elif cmd == "delete":
            if not args:
                print("Usage: /delete <name>")
                return True
            if self.memory.delete_saved(args.strip()):
                print(f"Deleted: {args.strip()}")
            else:
                print(f"Not found: {args.strip()}")
            return True

        elif cmd == "clear":
            self.memory.clear()
            print("Conversation cleared")
            return True

        elif cmd == "status":
            if self.mcp_client:
                status = await self.mcp_client.call_tool("get_connection_status", {})
                print(f"Connected: {status.get('connected', False)}")
                if status.get("connected"):
                    battery = await self.mcp_client.call_tool("get_battery_status", {})
                    print(f"Battery: {battery.get('battery_percentage', '?')}%")
            return True

        elif cmd == "connect":
            if self.mcp_client:
                result = await self.mcp_client.call_tool("connect", {})
                if result.get("success"):
                    print("Connected to RVR")
                else:
                    print(f"Connection failed: {result.get('error', 'unknown')}")
            return True

        elif cmd == "disconnect":
            if self.mcp_client:
                await self.mcp_client.call_tool("disconnect", {})
                print("Disconnected from RVR")
            return True

        elif cmd == "tools":
            print(f"Available tools ({len(self.tools)}):")
            for tool in self.tools:
                print(f"  {tool['name']}")
            return True

        elif cmd == "model":
            if args:
                self.config["model"] = args.strip()
                print(f"Model set to: {args.strip()}")
            else:
                print(f"Current model: {self.config.get('model')}")
            return True

        return False

    async def _stream_chat(self, messages: list, prefix: str = "") -> tuple[str, list]:
        """Stream a chat response, printing tokens as they arrive.

        Returns:
            Tuple of (full content text, list of tool calls)
        """
        model = self.config.get("model", "qwen2.5:1.5b")
        content_parts = []
        tool_calls = []

        client = ollama.AsyncClient()

        if prefix:
            print(prefix, end="", flush=True)

        stream = await client.chat(
            model=model,
            messages=messages,
            tools=self.ollama_tools,
            options={"temperature": self.config.get("temperature", 0.7)},
            stream=True,
        )

        async for chunk in stream:
            msg = chunk.get("message", {})
            text = msg.get("content", "")
            if text:
                content_parts.append(text)
                print(text, end="", flush=True)
            if msg.get("tool_calls"):
                tool_calls.extend(msg["tool_calls"])

        if content_parts:
            print()  # newline after streamed content

        return "".join(content_parts), tool_calls

    async def process_message(self, user_input: str) -> None:
        """Process a user message with streaming output."""
        self.memory.add_message("user", user_input)
        messages = self.memory.get_messages()

        # Stream response from Ollama
        try:
            content, tool_calls = await self._stream_chat(messages, "\nAssistant: ")
        except Exception as e:
            error_msg = f"LLM error: {e}"
            self.memory.add_message("assistant", error_msg)
            print(f"\nAssistant: {error_msg}\n")
            return

        # Process tool calls
        if tool_calls:
            self.memory.add_message("assistant", content, tool_calls=tool_calls)

            for tool_call in tool_calls:
                func = tool_call.get("function", {})
                tool_name = func.get("name", "")
                tool_args = func.get("arguments", {})

                print(f"  [Calling: {tool_name}({tool_args})]")

                if self.mcp_client:
                    result = await self.mcp_client.call_tool(tool_name, tool_args)
                    self.memory.add_tool_result(tool_name, result)
                    print(f"  [Result: {result}]")

            # Stream follow-up response after tool calls
            try:
                content, _ = await self._stream_chat(
                    self.memory.get_messages(), "\nAssistant: "
                )
            except Exception as e:
                content = f"Error getting follow-up: {e}"
                print(f"\nAssistant: {content}")

        self.memory.add_message("assistant", content)
        print()  # blank line after response

    async def run(self) -> None:
        """Run the main chat loop."""
        if not await self.start():
            return

        self.running = True

        # Set up prompt with history
        history_file = get_config_dir() / "prompt_history"
        session: PromptSession = PromptSession(
            history=FileHistory(str(history_file)),
            style=STYLE,
        )

        try:
            while self.running:
                try:
                    user_input = await asyncio.get_event_loop().run_in_executor(
                        None,
                        lambda: session.prompt("You: ")
                    )
                except (EOFError, KeyboardInterrupt):
                    break

                user_input = user_input.strip()
                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    if await self.handle_command(user_input):
                        continue

                # Process regular message (streams output directly)
                await self.process_message(user_input)

        finally:
            print("\nShutting down...")
            await self.stop()


def main():
    """Entry point."""
    chat = RVRChat()
    try:
        asyncio.run(chat.run())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
