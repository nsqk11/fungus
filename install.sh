#!/bin/bash
# Install fungus memory pipeline
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
KIRO_HOME="${HOME}/.kiro"
FUNGUS_HOME="${KIRO_HOME}/skills/github/fungus"

# Copy fungus to skills/github/fungus
mkdir -p "${FUNGUS_HOME}/prompts" "${FUNGUS_HOME}/hooks" "${FUNGUS_HOME}/data"
cp "${SCRIPT_DIR}/SKILL.md" "${FUNGUS_HOME}/"
cp "${SCRIPT_DIR}/_memory.py" "${FUNGUS_HOME}/"
cp "${SCRIPT_DIR}/run-extraction.py" "${FUNGUS_HOME}/"
cp "${SCRIPT_DIR}/prompts/"*.md "${FUNGUS_HOME}/prompts/"
cp "${SCRIPT_DIR}/hooks/"*.py "${FUNGUS_HOME}/hooks/"
chmod +x "${FUNGUS_HOME}/run-extraction.py" "${FUNGUS_HOME}/_memory.py"

# Copy agent configs (rewrite paths)
mkdir -p "${KIRO_HOME}/agents"
for f in "${SCRIPT_DIR}/agents/"*-extractor.json; do
    sed "s|FUNGUS_ROOT|${FUNGUS_HOME}|g" "$f" > "${KIRO_HOME}/agents/$(basename "$f")"
done

# Add cron job if not present
CRON_CMD="python3 ${FUNGUS_HOME}/run-extraction.py"
if ! crontab -l 2>/dev/null | grep -qF "$CRON_CMD"; then
    (crontab -l 2>/dev/null; echo "*/5 * * * * ${CRON_CMD}") | crontab -
    echo "Cron job added."
fi

echo "Installed to ${FUNGUS_HOME}"
