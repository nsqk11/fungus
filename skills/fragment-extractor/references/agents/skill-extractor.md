{
  "name": "skill-extractor",
  "description": "Extracts skill fragments from session transcripts.",
  "prompt": "",
  "tools": ["read", "shell"],
  "allowedTools": ["read", "shell"],
  "resources": [
    "file://FUNGUS_ROOT/fragment-extractor/references/extract-skill.md",
    "file://FUNGUS_ROOT/fragment-extractor/references/extract-common.md"
  ],
  "hooks": {},
  "toolsSettings": {},
  "model": "claude-sonnet-4.6"
}
