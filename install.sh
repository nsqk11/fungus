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

# Clean previous install, preserve data/ and skills/ (skills handled separately)
if [ -d "$INSTALL_DIR" ]; then
  echo "Updating existing installation (preserving data/) ..."
  find "$INSTALL_DIR" -mindepth 1 -maxdepth 1 \
    -not -name data -not -name skills -exec rm -rf {} + 2>/dev/null || true
fi

# Copy files (preserve data/ dirs inside skills)
mkdir -p "$INSTALL_DIR"
for dir in hooks modules prompts skills; do
  [ -d "$REPO_ROOT/$dir" ] || continue
  if [ "$dir" = "skills" ]; then
    # Sync each skill individually, preserving its data/
    for skill in "$REPO_ROOT/$dir"/*/; do
      skill_name="$(basename "$skill")"
      dest="$INSTALL_DIR/$dir/$skill_name"
      mkdir -p "$dest"
      # Remove non-data contents, then copy
      find "$dest" -mindepth 1 -maxdepth 1 \
        -not -name data -exec rm -rf {} + 2>/dev/null || true
      # Copy non-data contents from repo
      for item in "$skill"*; do
        [ "$(basename "$item")" = "data" ] && continue
        cp -r "$item" "$dest/"
      done
      # Ensure data dir exists
      mkdir -p "$dest/data"
    done
  else
    cp -r "$REPO_ROOT/$dir" "$INSTALL_DIR/"
  fi
done

# Ensure data directory
mkdir -p "$INSTALL_DIR/data"
[ -f "$INSTALL_DIR/data/memory.json" ] \
  || echo '[]' > "$INSTALL_DIR/data/memory.json"

# Create agent config (overwrite)
mkdir -p "$KIRO_HOME/agents"
cat > "$AGENT_FILE" <<AGENT
{
  "name": "fungus",
  "description": "An AI agent that grows from experience — like fungi.",
  "prompt": "You are Fungus — an AI agent that grows from experience.",
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
      { "command": "bash $INSTALL_DIR/hooks/substrate.sh" }
    ],
    "userPromptSubmit": [
      { "command": "bash $INSTALL_DIR/hooks/substrate.sh" }
    ],
    "preToolUse": [
      { "command": "bash $INSTALL_DIR/hooks/substrate.sh" }
    ],
    "postToolUse": [
      { "command": "bash $INSTALL_DIR/hooks/substrate.sh" }
    ],
    "stop": [
      { "command": "bash $INSTALL_DIR/hooks/substrate.sh" }
    ]
  }
}
AGENT
echo "Agent config created: $AGENT_FILE"

echo ""
echo "Done. Start with:"
echo "  kiro-cli chat --agent fungus"
