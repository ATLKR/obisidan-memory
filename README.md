# Obsidian Memory Plugins for AI Agents

Independent plugins that enable AI agents to use Obsidian Vault as persistent memory.

## Overview

Each agent has its own plugin that connects directly to your Obsidian Vault. Agents share knowledge **only through the Vault** - there is no direct communication between agents.

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Claude Code    │     │   Codex CLI     │     │     Hermes      │
│   (.claude-     │     │  (.codex/skills)│     │  (Python mod)   │
│    plugin/)     │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │   Obsidian Vault        │
                    │  (Markdown files)       │
                    │                         │
                    │  claude/  - Claude Code │
                    │  codex/   - Codex CLI   │
                    │  hermes/  - Hermes      │
                    └─────────────────────────┘
```

## Quick Start

```bash
# Set your vault path
export OBSIDIAN_VAULT_PATH="~/vaults/AllenPrimaryNotes"

# Test shared module
python3 shared/obsidian_memory.py
```

## Plugin Structure

### 1. Claude Code Plugin ⭐ (Supports Hooks)

Location: `ClaudeCode/`

Claude Code has rich **hook support** for automating context loading:

```
ClaudeCode/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest with hooks config
├── skills/
│   └── obsidian-memory/
│       └── SKILL.md         # Skill definition
├── commands/
│   └── vault-search.md      # Quick command
├── mcp-servers/
│   └── obsidian-memory-server/
│       └── server.py        # MCP server implementation
└── hooks/                    # 🎣 Automatic context hooks
    ├── on-session-start.py   # Load context at session start
    ├── on-prompt-submit.py   # Enrich prompts with vault context
    └── on-tool-use.py        # Store tool results to vault
```

**Supported Hook Events:**
- `SessionStart` - Load recent context when session begins
- `UserPromptSubmit` - Auto-enrich prompts with relevant vault content
- `PostToolUse` - Store important tool executions automatically
- `PreToolUse`, `InstructionsLoaded`, `Notification`, etc.

**Installation:**
```bash
# Copy or symlink to Claude Code plugins directory
# On macOS/Linux:
ln -s $(pwd)/ClaudeCode ~/.claude/plugins/obsidian-memory

# Or install via Claude Code CLI
claude plugin install /path/to/ClaudeCode
```

**Usage:**
```
# Automatic (via hooks):
# - Context loads automatically when session starts
# - Prompts are enriched with relevant vault content
# - Tool executions are stored automatically

# Manual skill usage:
/obsidian-memory:remember "Important decision about database schema"
/obsidian-memory:vault-search "trading system"
```

### 2. Codex CLI Plugin ⭐ (Hooks - Experimental)

Location: `Codex/`

> ⚠️ **Note:** Hooks are **experimental** in Codex CLI. Enable by adding to `~/.codex/config.toml`:
> ```toml
> [features]
> codex_hooks = true
> ```

Codex now supports hooks similar to Claude Code:

```
Codex/
├── .codex-plugin/
│   └── plugin.json          # Plugin manifest
├── .codex/
│   ├── hooks.json           # 🎣 Hook configuration
│   └── skills/
│       └── obsidian-memory/
│           ├── SKILL.md              # Skill definition
│           ├── agents/
│           │   └── openai.yaml       # Skill metadata
│           ├── hooks/                # 🎣 Hook scripts
│           │   ├── on-session-start.py
│           │   ├── on-prompt-submit.py
│           │   └── on-tool-use.py
│           └── scripts/              # Manual scripts
│               ├── store.py
│               ├── search.py
│               ├── query.py
│               └── history.py
```

**Supported Hook Events:**
- `SessionStart` - Load recent context when session begins
- `UserPromptSubmit` - Auto-enrich prompts with relevant vault content
- `PostToolUse` - Store important tool executions automatically
- `PreToolUse` - Validate before tool execution
- `Stop` - Run at conversation turn end

**Installation:**

```bash
# Via local marketplace
# Create ~/.agents/plugins/marketplace.json:
{
  "plugins": [
    {
      "source": { "path": "./obsidian-memory" },
      "interface": { "displayName": "Obsidian Memory" }
    }
  ]
}

# Or copy skill to your project
cp -r Codex/.codex/skills/obsidian-memory /your/project/.codex/skills/

# Enable hooks
echo '[features]' >> ~/.codex/config.toml
echo 'codex_hooks = true' >> ~/.codex/config.toml
```

**Usage:**
```bash
# Automatic (via hooks):
# - Context loads automatically when session starts
# - Prompts are enriched with relevant vault content
# - Tool executions are stored automatically

# Manual script usage:
python3 .codex/skills/obsidian-memory/scripts/store.py "Remember this"
python3 .codex/skills/obsidian-memory/scripts/search.py "database"

# Via Codex prompt:
"Remember that we decided to use PostgreSQL"
"Search my vault for database decisions"
```

### 3. Hermes Agent Plugin ⭐ (Dual Hook System)

Location: `Hermes/`

Hermes has **two** hook systems:

1. **Plugin hooks** (`ctx.register_hook()`) - Tool interception, runs in CLI + Gateway
2. **Gateway hooks** (`~/.hermes/hooks/`) - Event-driven, runs in Gateway only

```
Hermes/
├── plugin.py                      # Python module with plugin hooks
└── gateway-hooks/
    └── obsidian-memory/
        ├── HOOK.yaml              # Gateway hook manifest
        └── handler.py             # Gateway hook handler
```

**Installation:**

```bash
# 1. Install Gateway hooks
cp -r Hermes/gateway-hooks/obsidian-memory ~/.hermes/hooks/

# 2. Or use CLI installer
python3 Hermes/plugin.py install-hooks
```

**Plugin Hooks Usage (ctx.register_hook()):**
```python
from Hermes.plugin import HermesMemoryPlugin

# With Hermes context (automatic hook registration)
plugin = HermesMemoryPlugin(ctx=hermes_context)

# Or manual usage
plugin = HermesMemoryPlugin()
entry_id = plugin.remember("Important decision", tags=["architecture"])
results = plugin.recall("database decisions", n_results=5)
```

**CLI:**
```bash
python3 Hermes/plugin.py remember "Content here" --tags tag1 tag2
python3 Hermes/plugin.py recall "search query"
python3 Hermes/plugin.py search "pattern"
python3 Hermes/plugin.py recent
python3 Hermes/plugin.py stats
python3 Hermes/plugin.py install-hooks  # Install Gateway hooks
```

**Available Hermes Hook Events:**
- `agent:start` / `agent:end` - Session lifecycle
- `agent:step` - Each agent step
- `message:received` / `message:send` - Message events
- `tool:before` / `tool:after` - Tool execution (interception)
- `command:*` - Command events (wildcard)
- `gateway:startup` - Gateway initialization

### 4. OpenClaw (Stub) 🔮

Location: `OpenClaw/`

Reserved for future agent integration. Hook support will depend on the target agent framework.

## Hook Support Summary by Harness

| Harness | Hook Support | Type | Context Automation |
|---------|--------------|------|-------------------|
| **Claude Code** | ✅ Full | Event-driven hooks | Automatic via `SessionStart`, `UserPromptSubmit`, `PostToolUse` |
| **Codex CLI** | ⚠️ Experimental | `hooks.json` config | Automatic when `codex_hooks = true` |
| **Hermes** | ⭐ Dual System | Plugin + Gateway | `ctx.register_hook()` or `~/.hermes/hooks/` |
| **OpenClaw** | 🔮 TBD | Future | Depends on target framework |

**Available Hook Events:**
- `SessionStart` / `agent:start` - Runs at session start, loads context from vault
- `UserPromptSubmit` / `message:received` - Runs on each prompt, enriches with relevant vault content
- `PostToolUse` / `tool:after` - Runs after tool execution, stores important results
- `PreToolUse` / `tool:before` - Runs before tool execution (validation/interception)
- `Stop` / `agent:end` - Runs at conversation turn end

**Configuration Locations:**
- **Claude Code:** `.claude-plugin/plugin.json`
- **Codex CLI:** `.codex/hooks.json` (requires `codex_hooks = true` in `~/.codex/config.toml`)
- **Hermes:** 
  - Plugin hooks: `ctx.register_hook()` in Python code
  - Gateway hooks: `~/.hermes/hooks/<hook-name>/HOOK.yaml` + `handler.py`

## Shared Module

Location: `shared/obsidian_memory.py`

Core module used by all plugins:

```python
from obsidian_memory import get_memory

# Get memory instance for an agent
memory = get_memory('agent-name')

# Store
entry = memory.store("Content", tags=["tag1"])

# Search
matches = memory.search("pattern")

# Query
entries = memory.query("search text", n_results=5)

# Get history
history = memory.get_conversation_history(limit=10)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OBSIDIAN_VAULT_PATH` | `~/vaults/AllenPrimaryNotes` | Path to Obsidian vault |

## File Storage Format

Memories are stored as markdown files:

```markdown
---
id: abc123
timestamp: 2026-03-31T12:00:00
agent: claude
tags: ["decision", "database"]
metadata:
  session: xyz789
---

# Content goes here

Full text of the memory...
```

**Storage locations:**
- Claude Code: `<vault>/claude/YYYY-MM-DD_<id>.md`
- Codex CLI: `<vault>/codex/YYYY-MM-DD_<id>.md`
- Hermes: `<vault>/hermes/YYYY-MM-DD_<id>.md`
- OpenClaw: `<vault>/openclaw/YYYY-MM-DD_<id>.md`

## Example Workflow

1. **Claude Code session:**
   ```
   User: "Remember that we decided to use Redis for caching"
   Claude: Stores to `<vault>/claude/2026-03-31_abc123.md`
   ```

2. **Later, Codex CLI session:**
   ```
   User: "What did we decide about caching?"
   Codex: Searches vault, finds the Redis decision
   ```

3. **Hermes automation:**
   ```python
   # Cron job or scheduled task
   plugin = HermesMemoryPlugin()
   daily_summary = plugin.recall("daily summary", n_results=1)
   ```

## Requirements

- Python 3.8+
- Obsidian Vault (any markdown-based vault)
- No external dependencies (uses Python stdlib only)

## Directory Structure

```
obsidian-memory/
├── README.md
├── .env.example
├── requirements.txt
├── shared/
│   └── obsidian_memory.py              # Core shared module
├── ClaudeCode/                          # Claude Code plugin ✅ Hooks
│   ├── .claude-plugin/
│   │   └── plugin.json                  # Plugin manifest + hooks config
│   ├── skills/
│   │   └── obsidian-memory/
│   │       └── SKILL.md                 # Skill definition
│   ├── commands/
│   │   └── vault-search.md              # Quick command
│   ├── mcp-servers/
│   │   └── obsidian-memory-server/
│   │       └── server.py                # MCP server
│   └── hooks/                           # 🎣 Automatic context hooks
│       ├── on-session-start.py          # Load context at session start
│       ├── on-prompt-submit.py          # Enrich prompts with vault context
│       └── on-tool-use.py               # Store tool results to vault
├── Codex/                               # Codex CLI plugin ⚠️ Experimental hooks
│   ├── .codex-plugin/
│   │   └── plugin.json                   # Plugin manifest
│   └── .codex/
│       ├── hooks.json                    # 🎣 Hook configuration
│       └── skills/
│           └── obsidian-memory/
│               ├── SKILL.md              # Skill definition
│               ├── agents/
│               │   └── openai.yaml       # Skill metadata
│               ├── hooks/                  # 🎣 Hook scripts
│               │   ├── on-session-start.py
│               │   ├── on-prompt-submit.py
│               │   └── on-tool-use.py
│               └── scripts/              # Manual scripts
│                   ├── store.py
│                   ├── search.py
│                   ├── query.py
│                   └── history.py
├── Hermes/                              # Hermes plugin ⭐ Dual hook system
│   ├── plugin.py                        # Python module with ctx.register_hook()
│   └── gateway-hooks/                   # 🎣 Gateway hooks template
│       └── obsidian-memory/
│           ├── HOOK.yaml                # Gateway hook manifest
│           └── handler.py               # Gateway hook handler
└── OpenClaw/                            # OpenClaw stub 🔮
    └── plugin.py
```

## License

MIT
