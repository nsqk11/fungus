# Agent Skills Specification

Source: https://agentskills.io/specification

## Directory structure

A skill is a directory containing, at minimum, a SKILL.md file:

```
skill-name/
├── SKILL.md       # Required: metadata + instructions
├── scripts/       # Optional: executable code
├── references/    # Optional: documentation
├── assets/        # Optional: templates, resources
└── ...            # Any additional files or directories
```

## SKILL.md format

The SKILL.md file must contain YAML frontmatter followed by Markdown content.

## Frontmatter

| Field | Required | Constraints |
|-------|----------|-------------|
| name | Yes | Max 64 characters. Lowercase letters, numbers, and hyphens only. Must not start or end with a hyphen. |
| description | Yes | Max 1024 characters. Non-empty. Describes what the skill does and when to use it. |
| license | No | License name or reference to a bundled license file. |
| compatibility | No | Max 500 characters. Indicates environment requirements. |
| metadata | No | Arbitrary key-value mapping for additional metadata. |
| allowed-tools | No | Space-separated string of pre-approved tools the skill may use. (Experimental) |

Minimal example:

```yaml
---
name: skill-name
description: A description of what this skill does and when to use it.
---
```

Example with optional fields:

```yaml
---
name: pdf-processing
description: Extract PDF text, fill forms, merge files. Use when handling PDFs.
license: Apache-2.0
metadata:
  author: example-org
  version: "1.0"
---
```

### name field

The required name field:
- Must be 1-64 characters
- May only contain lowercase alphanumeric characters (a-z) and hyphens (-)
- Must not start or end with a hyphen (-)
- Must not contain consecutive hyphens (--)
- Must match the parent directory name

### description field

The required description field:
- Must be 1-1024 characters
- Should describe both what the skill does and when to use it
- Should include specific keywords that help agents identify relevant tasks

Good example:
```
description: Extracts text and tables from PDF files, fills PDF forms, and merges multiple PDFs. Use when working with PDF documents or when the user mentions PDFs, forms, or document extraction.
```

Poor example:
```
description: Helps with PDFs.
```

### license field

The optional license field specifies the license applied to the skill. Keep it short — either the name of a license or the name of a bundled license file.

### compatibility field

- Must be 1-500 characters if provided
- Should only be included if your skill has specific environment requirements
- Can indicate intended product, required system packages, network access needs

Examples:
```
compatibility: Designed for Claude Code (or similar products)
compatibility: Requires git, docker, jq, and access to the internet
compatibility: Requires Python 3.14+ and uv
```

### metadata field

A map from string keys to string values. Clients can use this to store additional properties not defined by the spec.

### allowed-tools field

A space-separated string of tools that are pre-approved to run. Experimental.

## Body content

The Markdown body after the frontmatter contains the skill instructions. There are no format restrictions. Write whatever helps agents perform the task effectively.

Recommended sections:
- Step-by-step instructions
- Examples of inputs and outputs
- Common edge cases

Consider splitting longer SKILL.md content into referenced files.

## Optional directories

### scripts/

Contains executable code that agents can run. Scripts should:
- Be executable (have appropriate shebang line)
- Handle errors gracefully
- Document their usage in SKILL.md

### references/

Contains documentation files that SKILL.md can reference. Kiro loads reference files only when the instructions direct it to.

### assets/

Contains templates, configuration files, or other resources the skill needs.

## Progressive disclosure

Skills support progressive disclosure — metadata (name, description) is loaded at startup, full SKILL.md content is loaded on demand when activated, and reference files are loaded only when instructions direct the agent to read them.

## File references

Reference files in your SKILL.md using relative paths:
```
For deployment patterns, see `references/deployment-guide.md`.
```

## Validation

- name must match directory name
- name must follow naming constraints (lowercase, hyphens, 1-64 chars)
- description must be non-empty and max 1024 characters
- SKILL.md must have valid YAML frontmatter
