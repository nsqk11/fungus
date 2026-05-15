#!/bin/bash
# install.sh — install Fungus agent to $KIRO_HOME/skills/fungus/.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
KIRO_HOME="${KIRO_HOME:-$HOME/.kiro}"
INSTALL_DIR="$KIRO_HOME/skills/fungus"
AGENT_FILE="$KIRO_HOME/agents/fungus.json"

echo "Installing Fungus to $INSTALL_DIR ..."

# Prerequisites
command -v python3 >/dev/null 2>&1 || { echo "Error: python3 is required." >&2; exit 1; }
command -v git >/dev/null 2>&1 || { echo "Error: git is required." >&2; exit 1; }

python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null || {
  echo "Error: Python >= 3.10 required." >&2; exit 1
}

# Sync repo to install dir, preserving data/
mkdir -p "$INSTALL_DIR"
for dir in hooks prompts skills; do
  [ -d "$REPO_ROOT/$dir" ] || continue
  if [ "$dir" = "skills" ]; then
    mkdir -p "$INSTALL_DIR/$dir"
    for skill in "$REPO_ROOT/$dir"/*/; do
      skill_name="$(basename "$skill")"
      dest="$INSTALL_DIR/$dir/$skill_name"
      rm -rf "$dest"
      cp -r "$skill" "$dest"
      find "$dest" -type d \( -name __pycache__ -o -name tests -o -name .pytest_cache \) -exec rm -rf {} + 2>/dev/null || true
    done
  else
    rm -rf "$INSTALL_DIR/$dir"
    cp -r "$REPO_ROOT/$dir" "$INSTALL_DIR/"
    find "$INSTALL_DIR/$dir" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
  fi
done

# Make scripts executable
find "$INSTALL_DIR/hooks" -name "*.py" -not -name "_*" -exec chmod +x {} +
find "$INSTALL_DIR/hooks" -name "*.sh" -exec chmod +x {} +

# Clone/update anthropics community skills
COMMUNITY_SKILLS_DIR="$INSTALL_DIR/.cache/anthropics-skills"
COMMUNITY_SKILLS_REPO="https://github.com/anthropics/skills.git"
if [ -d "$COMMUNITY_SKILLS_DIR/.git" ]; then
  echo "Updating anthropics/skills ..."
  git -C "$COMMUNITY_SKILLS_DIR" pull --ff-only 2>/dev/null || true
else
  echo "Cloning anthropics/skills ..."
  mkdir -p "$(dirname "$COMMUNITY_SKILLS_DIR")"
  git clone --depth 1 "$COMMUNITY_SKILLS_REPO" "$COMMUNITY_SKILLS_DIR"
fi
for skill in docx pptx xlsx pdf skill-creator; do
  dest="$INSTALL_DIR/skills/$skill"
  [ -d "$dest" ] && rm -rf "$dest"
  cp -r "$COMMUNITY_SKILLS_DIR/skills/$skill" "$dest"
done

# Generate agent config (only if not present; preserves user customizations)
mkdir -p "$KIRO_HOME/agents"
if [ -f "$AGENT_FILE" ]; then
  echo "Agent config exists, skipping: $AGENT_FILE"
else
  cat > "$AGENT_FILE" <<AGENT
{
  "name": "fungus",
  "description": "General-purpose AI coding agent with persistent memory.",
  "prompt": "",
  "tools": ["*"],
  "resources": [
    "file://$INSTALL_DIR/prompts/system-prompt.md",
    "file://$INSTALL_DIR/memory/procedural.md",
    "skill://$KIRO_HOME/skills/**/SKILL.md",
    {
      "type": "knowledgeBase",
      "source": "file://$INSTALL_DIR/memory",
      "name": "fungus-memory",
      "indexType": "best",
      "include": ["memory-*.md"],
      "autoUpdate": true
    }
  ],
  "hooks": {
    "agentSpawn":       [{ "command": "$INSTALL_DIR/hooks/router.py" }],
    "userPromptSubmit": [{ "command": "$INSTALL_DIR/hooks/router.py" }],
    "preToolUse":       [{ "command": "$INSTALL_DIR/hooks/router.py" }],
    "postToolUse":      [{ "command": "$INSTALL_DIR/hooks/router.py" }],
    "stop":             [{ "command": "$INSTALL_DIR/hooks/router.py" }]
  },
  "toolsSettings": {
    "execute_bash": {
      "autoAllowReadonly": true,
      "deniedCommands": [
        "rm .*",
        "rmdir .*",
        "mv .*",
        "cp .*",
        "chmod .*",
        "chown .*",
        "dd .*",
        "mkfs .*",
        "\\\\>.*",
        "tee .*"
      ]
    }
  },
  "includeMcpJson": true,
  "model": null,
  "keyboardShortcut": "alt+f"
}
AGENT
  echo "Agent config created: $AGENT_FILE"
fi

echo ""
echo "Done. Start with:"
echo "  kiro-cli chat --agent fungus"
