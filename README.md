# RVR Chat

Local LLM chat interface for controlling Sphero RVR via MCP. Runs entirely on a Raspberry Pi 5.

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Pi 5 (16GB)                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────┐ │
│  │   Ollama    │◄──►│  rvr-chat   │◄──►│ MCP Srv │ │
│  │ (qwen2.5)   │    │   (CLI)     │    │ (RVR)   │ │
│  └─────────────┘    └─────────────┘    └────┬────┘ │
└─────────────────────────────────────────────┼──────┘
                                              │ Serial
                                         ┌────┴────┐
                                         │   RVR   │
                                         └─────────┘
```

## Requirements

- Raspberry Pi 5 with 16GB RAM (or any Linux machine)
- Python 3.10+
- sphero-rvr-mcp installed and working
- Internet connection (for initial model download)

## Quick Install

```bash
git clone <this-repo>
cd rvr-chat
./install.sh
```

This will:
1. Install Ollama
2. Download the Qwen 2.5 7B model (~5GB)
3. Install rvr-chat in a virtual environment

## Manual Install

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull model
ollama pull qwen2.5:7b

# Install rvr-chat
cd rvr-chat
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

```bash
source .venv/bin/activate
rvr-chat
```

### Chat Commands

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/quit`, `/q` | Exit |
| `/save [name]` | Save conversation |
| `/load <name>` | Load conversation |
| `/list` | List saved conversations |
| `/clear` | Clear history |
| `/status` | Show RVR status |
| `/connect` | Connect to RVR |
| `/disconnect` | Disconnect |
| `/tools` | List available tools |
| `/model [name]` | Show/change model |

### Example Session

```
$ rvr-chat
RVR Chat v0.1.0
========================================
Checking Ollama... OK
Model: qwen2.5:7b
Starting MCP server... OK
Loading tools... OK (45 tools)
Connecting to RVR... OK
Battery: 85%
========================================
Type /help for commands, /quit to exit

You: drive forward 1 meter

  [Calling: drive_forward({"distance": 1.0})]
  [Result: {"success": true, "distance": 1.0}]

Assistant: I moved forward 1 meter.

You: now turn around and come back

  [Calling: pivot({"degrees": 180})]
  [Result: {"success": true, "degrees": 180}]
  [Calling: drive_forward({"distance": 1.0})]
  [Result: {"success": true, "distance": 1.0}]

Assistant: Done\! I turned 180 degrees and drove back 1 meter.

You: /save exploration
Saved to: ~/.rvr-chat/history/exploration.json

You: /quit
Shutting down...
```

## Configuration

Configuration is stored in `~/.rvr-chat/config.yaml`:

```yaml
model: qwen2.5:7b
mcp_command:
  - sphero-rvr-mcp
max_history: 100
temperature: 0.7
auto_connect_rvr: true
```

### Alternative Models

You can use other models with good tool-use capability:

```bash
# Smaller/faster
ollama pull llama3.2:3b

# Larger/smarter (needs more RAM)
ollama pull qwen2.5:14b
ollama pull llama3.1:8b
```

## Performance

Expected on Raspberry Pi 5 (16GB):

| Metric | Value |
|--------|-------|
| Model load | ~10 seconds |
| First token | 1-3 seconds |
| Token rate | 3-8 tokens/sec |
| Memory usage | ~6GB (qwen2.5:7b) |

## Uninstall

```bash
./uninstall.sh
```

## License

MIT
