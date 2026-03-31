---
name: obsidian-memory
description: |
  Use Obsidian Vault as persistent memory for Codex CLI.
  
  This skill allows Codex to:
  - Store important information to your Obsidian vault
  - Search your vault for relevant context and knowledge
  - Retrieve past conversations and decisions
  - Query existing notes for project context
  
  The vault acts as long-term memory that persists across Codex sessions.
  
  Use when you need to:
  - Remember something for later sessions
  - Look up information from previous work
  - Find relevant documentation or decisions
  - Get context about the project structure
  
  Enable automatic context loading by setting in ~/.codex/config.toml:
  [features]
  codex_hooks = true
---

# Obsidian Memory Skill for Codex

## Automatic Context (Hooks)

When hooks are enabled (`codex_hooks = true` in config.toml):

1. **SessionStart** - Loads recent conversation history at session start
2. **UserPromptSubmit** - Automatically enriches prompts with relevant vault content
3. **PostToolUse** - Stores important tool executions (Edit, Write, Bash) to vault

## Manual Commands

### Store Memory
```bash
python3 .codex/skills/obsidian-memory/scripts/store.py "Content to remember" --tags tag1 tag2
```

### Search Vault
```bash
python3 .codex/skills/obsidian-memory/scripts/search.py "search query"
```

### Query Context
```bash
python3 .codex/skills/obsidian-memory/scripts/query.py "what do I know about X"
```

### Get Recent History
```bash
python3 .codex/skills/obsidian-memory/scripts/history.py --limit 5
```

## Environment Variables

- `OBSIDIAN_VAULT_PATH`: Path to your Obsidian vault (default: ~/vaults/AllenPrimaryNotes)

## File Structure

Stored memories go to:
- `<vault>/codex/YYYY-MM-DD_<id>.md`

Each file includes:
- YAML frontmatter with metadata (id, timestamp, tags)
- The content you asked to store

## Plugin Installation

This skill is packaged as a Codex plugin:

```bash
# Via local marketplace
# Create ~/.agents/plugins/marketplace.json:
{
  "plugins": [
    {
      "source": {
        "path": "./obsidian-memory"
      },
      "interface": {
        "displayName": "Obsidian Memory"
      }
    }
  ]
}

# Or use $plugin-creator skill
$plugin-creator
```

## Integration

When you ask Codex to "remember" something, it will:
1. Store the content in your Obsidian vault
2. Tag it appropriately for later retrieval
3. Confirm the storage with the file path

When you ask Codex to "search" or "recall", it will:
1. Search through your Obsidian vault
2. Find the most relevant entries
3. Present them with context
