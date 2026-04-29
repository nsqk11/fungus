#!/bin/bash
# install.sh — install Fungus agent to $KIRO_HOME/skills/fungus/.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
KIRO_HOME="${KIRO_HOME:-$HOME/.kiro}"
INSTALL_DIR="$KIRO_HOME/skills/fungus"
AGENT_FILE="$KIRO_HOME/agents/fungus.json"

echo "Installing Fungus to $INSTALL_DIR ..."

# Prerequisites
for cmd in python3.12 git; do
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "Error: $cmd is required but not found." >&2
    exit 1
  }
done

# Python dependencies (declared by skills that need them)
if ! python3.12 -c "import atlassian" 2>/dev/null; then
  echo "Installing atlassian-python-api ..."
  python3.12 -m pip install --user atlassian-python-api
fi

# Remove legacy top-level dirs that v2 no longer uses
for legacy in modules; do
  [ -d "$INSTALL_DIR/$legacy" ] && rm -rf "$INSTALL_DIR/$legacy"
done

# Remove orphan skill dirs that no longer exist in the repo
if [ -d "$INSTALL_DIR/skills" ]; then
  for installed in "$INSTALL_DIR/skills"/*/; do
    name="$(basename "$installed")"
    [ -d "$REPO_ROOT/skills/$name" ] || rm -rf "$installed"
  done
fi

# Sync repo to install dir, preserving data/ in every skill
mkdir -p "$INSTALL_DIR"
for dir in hooks prompts skills knowledgeBase; do
  [ -d "$REPO_ROOT/$dir" ] || continue
  if [ "$dir" = "skills" ]; then
    for skill in "$REPO_ROOT/$dir"/*/; do
      skill_name="$(basename "$skill")"
      dest="$INSTALL_DIR/$dir/$skill_name"
      mkdir -p "$dest"
      # Purge old non-data content
      find "$dest" -mindepth 1 -maxdepth 1 \
        -not -name data -exec rm -rf {} + 2>/dev/null || true
      # Copy non-data content from repo
      for item in "$skill".* "$skill"*; do
        name="$(basename "$item")"
        case "$name" in
          .|..|data|__pycache__|.pytest_cache) continue ;;
        esac
        [ -e "$item" ] || continue
        cp -r "$item" "$dest/"
      done
      # Remove any Python cache dirs that slipped in from nested copies
      find "$dest" -depth -type d \
        \( -name __pycache__ -o -name .pytest_cache \) \
        -exec rm -rf {} + 2>/dev/null || true
      mkdir -p "$dest/data"
    done
  else
    rm -rf "$INSTALL_DIR/$dir"
    cp -r "$REPO_ROOT/$dir" "$INSTALL_DIR/"
    find "$INSTALL_DIR/$dir" -depth -type d \
      \( -name __pycache__ -o -name .pytest_cache \) \
      -exec rm -rf {} + 2>/dev/null || true
  fi
done

# Clone/update external knowledge base repos
KB_DIR="$INSTALL_DIR/knowledgeBase"
mkdir -p "$KB_DIR"
declare -A KB_REPOS=(
  ["styleguide"]="https://github.com/google/styleguide.git"
  ["design-patterns-for-humans"]="https://github.com/kamranahmedse/design-patterns-for-humans.git"
)
for name in "${!KB_REPOS[@]}"; do
  dest="$KB_DIR/$name"
  if [ -d "$dest/.git" ]; then
    echo "Updating $name ..."
    git -C "$dest" pull --ff-only 2>/dev/null || true
  else
    echo "Cloning $name ..."
    git clone --depth 1 "${KB_REPOS[$name]}" "$dest"
  fi
done

# Ensure long-term-memory.md placeholder exists so Kiro can index the KB on first run
MEMORY_MD="$INSTALL_DIR/data/long-term-memory.md"
mkdir -p "$(dirname "$MEMORY_MD")"
[ -f "$MEMORY_MD" ] || echo "# Fungus Memory" > "$MEMORY_MD"

# Generate agent config
mkdir -p "$KIRO_HOME/agents"
cat > "$AGENT_FILE" <<AGENT
{
  "name": "fungus",
  "description": "General-purpose AI coding agent with persistent memory.",
  "prompt": "",
  "mcpServers": {},
  "tools": ["*"],
  "allowedTools": [
    "fs_read",
    "grep",
    "glob",
    "code",
    "web_search",
    "web_fetch",
    "knowledge",
    "use_aws",
    "execute_bash",
    "todo_list"
  ],
  "resources": [
    "file://$INSTALL_DIR/prompts/system-prompt.md",
    "skill://$KIRO_HOME/skills/**/SKILL.md",
    {
      "type": "knowledgeBase",
      "source": "file://$INSTALL_DIR/data/long-term-memory.md",
      "name": "fungus-memory",
      "indexType": "best",
      "autoUpdate": true
    },
    {
      "type": "knowledgeBase",
      "source": "file://$INSTALL_DIR/knowledgeBase/agent-skills-spec.md",
      "name": "agent-skills-spec",
      "indexType": "best",
      "autoUpdate": true
    },
    {
      "type": "knowledgeBase",
      "source": "file://$INSTALL_DIR/knowledgeBase/design-patterns-for-humans",
      "name": "design-patterns",
      "indexType": "best",
      "include": ["**/*.md"],
      "exclude": [".git/**", ".github/**"],
      "autoUpdate": true
    },
    {
      "type": "knowledgeBase",
      "source": "file://$INSTALL_DIR/knowledgeBase/styleguide",
      "name": "google-styleguide",
      "indexType": "best",
      "include": ["**/*.md", "**/*.html", "**/*.xml"],
      "exclude": [".git/**", ".github/**", "include/**", "assets/**", "_includes/**"],
      "autoUpdate": true
    }
  ],
  "hooks": {
    "agentSpawn":       [{ "command": "python3.12 $INSTALL_DIR/hooks/router.py" }],
    "userPromptSubmit": [{ "command": "python3.12 $INSTALL_DIR/hooks/router.py" }],
    "preToolUse":       [{ "command": "python3.12 $INSTALL_DIR/hooks/router.py" }],
    "postToolUse":      [{ "command": "python3.12 $INSTALL_DIR/hooks/router.py" }],
    "stop":             [{ "command": "python3.12 $INSTALL_DIR/hooks/router.py" }]
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

echo ""
echo "Done. Start with:"
echo "  kiro-cli chat --agent fungus"
