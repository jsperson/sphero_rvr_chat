"""Conversation memory management."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import get_history_dir


class ConversationMemory:
    """Manages conversation history with persistence."""

    def __init__(self, max_messages: int = 100):
        self.max_messages = max_messages
        self.messages: list[dict[str, Any]] = []
        self.session_name: str | None = None
        self.metadata: dict[str, Any] = {
            "created": datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
        }

    def add_message(self, role: str, content: str, tool_calls: list | None = None) -> None:
        """Add a message to the conversation history."""
        message = {"role": role, "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls

        self.messages.append(message)
        self.metadata["updated"] = datetime.now().isoformat()

        # Trim if needed (keep system prompt + recent messages)
        if len(self.messages) > self.max_messages:
            # Keep first message if it's a system prompt
            if self.messages and self.messages[0].get("role") == "system":
                self.messages = [self.messages[0]] + self.messages[-(self.max_messages - 1):]
            else:
                self.messages = self.messages[-self.max_messages:]

    def add_tool_result(self, tool_name: str, result: Any) -> None:
        """Add a tool result message."""
        self.messages.append({
            "role": "tool",
            "name": tool_name,
            "content": json.dumps(result) if not isinstance(result, str) else result,
        })
        self.metadata["updated"] = datetime.now().isoformat()

    def get_messages(self) -> list[dict[str, Any]]:
        """Get all messages for sending to LLM."""
        return self.messages.copy()

    def clear(self) -> None:
        """Clear conversation history (keeps system prompt if present)."""
        if self.messages and self.messages[0].get("role") == "system":
            self.messages = [self.messages[0]]
        else:
            self.messages = []
        self.metadata["updated"] = datetime.now().isoformat()

    def save(self, name: str | None = None) -> Path:
        """Save conversation to file."""
        if name:
            self.session_name = name

        if not self.session_name:
            self.session_name = datetime.now().strftime("%Y%m%d_%H%M%S")

        history_dir = get_history_dir()
        filepath = history_dir / f"{self.session_name}.json"

        data = {
            "session_name": self.session_name,
            "metadata": self.metadata,
            "messages": self.messages,
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

        return filepath

    def load(self, name: str) -> bool:
        """Load conversation from file."""
        history_dir = get_history_dir()
        filepath = history_dir / f"{name}.json"

        if not filepath.exists():
            return False

        with open(filepath) as f:
            data = json.load(f)

        self.session_name = data.get("session_name", name)
        self.metadata = data.get("metadata", {})
        self.messages = data.get("messages", [])
        return True

    def list_saved(self) -> list[dict[str, Any]]:
        """List all saved conversations."""
        history_dir = get_history_dir()
        sessions = []

        for filepath in sorted(history_dir.glob("*.json"), reverse=True):
            try:
                with open(filepath) as f:
                    data = json.load(f)
                sessions.append({
                    "name": filepath.stem,
                    "created": data.get("metadata", {}).get("created", "unknown"),
                    "messages": len(data.get("messages", [])),
                })
            except (json.JSONDecodeError, IOError):
                continue

        return sessions

    def delete_saved(self, name: str) -> bool:
        """Delete a saved conversation."""
        history_dir = get_history_dir()
        filepath = history_dir / f"{name}.json"

        if filepath.exists():
            filepath.unlink()
            return True
        return False
