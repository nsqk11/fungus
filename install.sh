#!/bin/bash
# install.sh — install Fungus agent to ~/.kiro/skills/fungus/
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
KIRO_HOME="${KIRO_HOME:-$HOME/.kiro}"
INSTALL_DIR="$KIRO_HOME/skills/fungus"
AGENT_FILE="$KIRO_HOME/agents/fungus.json"

echo "Installing Fungus to $INSTALL_DIR ..."

# Check prerequisites
for cmd in python3.12 jq; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "Error: $cmd is required but not found." >&2
    exit 1
  }
done

# Clean previous install, preserve data/
if [ -d "$INSTALL_DIR" ]; then
  echo "Updating existing installation (preserving data/) ..."
  find "$INSTALL_DIR" -mindepth 1 -maxdepth 1 \
    -not -name data -exec rm -rf {} + 2>/dev/null || true
fi

# Copy files
mkdir -p "$INSTALL_DIR"
for dir in hooks modules prompts skills; do
  [ -d "$REPO_ROOT/$dir" ] && cp -r "$REPO_ROOT/$dir" "$INSTALL_DIR/"
done

# Ensure data directory and memory.json
mkdir -p "$INSTALL_DIR/data"
[ -f "$INSTALL_DIR/data/memory.json" ] || echo '[]' > "$INSTALL_DIR/data/memory.json"

# Create agent config
mkdir -p "$KIRO_HOME/agents"
if [ -f "$AGENT_FILE" ]; then
  echo "Agent config exists: $AGENT_FILE (skipped)"
else
  cat > "$AGENT_FILE" <<AGENT
{
  "name": "fungus",
  "description": "An AI agent that grows from experience — like fungi.",
  "prompt": "",
  "tools": ["*"],
  "allowedTools": [
    "fs_read",
    "grep",
    "glob",
    "code",
    "execute_bash",
    "knowledge",
    "todo_list"
  ],
  "resources": [
    "file://$INSTALL_DIR/prompts/agent-context.md",
    "skill://$INSTALL_DIR/**/SKILL.md"
  ],
  "hooks": {
    "agentSpawn": [
      { "command": "bash $INSTALL_DIR/hooks/substrate.sh agent-spawn" }
    ],
    "userPromptSubmit": [
      { "command": "bash $INSTALL_DIR/hooks/substrate.sh user-prompt-submit" }
    ],
    "preToolUse": [
      { "command": "bash $INSTALL_DIR/hooks/substrate.sh pre-tool-use" }
    ],
    "postToolUse": [
      { "command": "bash $INSTALL_DIR/hooks/substrate.sh post-tool-use" }
    ],
    "stop": [
      { "command": "bash $INSTALL_DIR/hooks/substrate.sh stop" }
    ]
  }
}
AGENT
  echo "Agent config created: $AGENT_FILE"
fi

echo ""
echo "Done. Start with:"
echo "  kiro-cli chat --agent fungus"
