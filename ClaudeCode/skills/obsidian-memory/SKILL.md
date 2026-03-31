---
name: obsidian-memory
description: |
  Store and retrieve memories from Obsidian Vault.
  
  Use this skill to:
  - Save important information to your Obsidian vault
  - Search your vault for relevant context
  - Retrieve conversation history
  - Query existing notes for knowledge
  
  The vault acts as a persistent memory that persists across sessions.
tools:
  - vault_store
  - vault_search
  - vault_query
  - vault_history
---

# Obsidian Memory Skill

This skill enables Claude Code to use your Obsidian Vault as persistent memory.

## Usage Examples

### Store a memory
```
Remember that the database schema uses PostgreSQL with JSONB columns for flexibility.
```

### Search the vault
```
Search my vault for information about the trading system architecture.
```

### Get conversation history
```
Show me my recent conversations about database design.
```

### Query for context
```
What do I know about the current project structure?
```

## How It Works

When you ask me to remember something:
1. I'll store it as a markdown file in `<vault>/claude/`
2. It will include metadata (timestamp, tags) in YAML frontmatter
3. You can search it later using natural language

When you ask me to search or recall:
1. I'll search through your Obsidian vault
2. Find relevant notes based on content matching
3. Present the most relevant results

## File Structure

Stored memories go to:
- `<OBSIDIAN_VAULT_PATH>/claude/YYYY-MM-DD_<id>.md`

Each file has YAML frontmatter:
```yaml
---
id: abc123
timestamp: 2026-03-31T12:00:00
agent: claude
tags: []
---
```
