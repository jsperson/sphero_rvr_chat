#!/bin/bash
# Start Sphero RVR Chat
cd "$(dirname "$0")"
exec .venv/bin/sphero-rvr-chat "$@"
