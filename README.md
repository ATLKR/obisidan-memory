# Obsidian Memory System

Multi-Agent Persistent Memory with Cross-Agent Query Protocol

## Overview

This system implements a **persistent memory layer** for multiple AI agents (Codex, Claude Code, Hermes, OpenClaw) using an **Obsidian Vault** as the storage backend.

### Key Research Foundations

| Paper | Contribution |
|-------|-------------|
| **Self-Consistency (2203.11171)** | Multiple reasoning paths, consistent answer selection |
| **ChatDev (2307.07924)** | Communicative agents with structured dialogue |

### Core Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    CrossAgentQuery Protocol                      │
│  (Query → Answer with Evidence → Verification → Arbitration)    │
├─────────────┬─────────────┬─────────────┬───────────────────────┤
│   Codex     │ ClaudeCode  │   Hermes    │      OpenClaw         │
│   (Code)    │  (Reason)   │(Orchestrate)│    (Future)         │
├─────────────┴─────────────┴─────────────┴───────────────────────┤
│              ObsidianMemory (Persistent Layer)                  │
│              - Markdown read/write via qmd                      │
│              - Vector search + metadata indexing                │
│              - Evidence tracking with confidence scores         │
└─────────────────────────────────────────────────────────────────┘
```

## Features

### Cross-Agent Query Protocol

**Flow:**
1. **Querier** (Agent A) → **Responder** (Agent B): "What's X?"
2. **Responder** → **Querier**: "X is Y" + Evidence (source citations)
3. **Verifier**: Check evidence quality and consistency
4. **Arbiter** (if disputed): Resolve using Self-Consistency

### Persistent Memory

- All conversations stored in Obsidian Vault
- Frontmatter metadata (agent, timestamp, tags, confidence)
- Evidence citations tracked per entry
- WikiLinks and tags indexed for cross-referencing

## Installation

```bash
# Clone the repository
git clone https://github.com/ATLKR/obisidan-memory.git
cd obisidan-memory

# Set your Obsidian vault path
export OBSIDIAN_VAULT_PATH="~/vaults/AllenPrimaryNotes"

# Optional: Install enhanced dependencies
pip install -r requirements.txt
```

## Usage

### CLI

```bash
# Query Codex through Hermes
python main.py query hermes codex "How do I implement a singleton?"

# Store a memory
python main.py store codex "Important pattern..." --tags code python

# Search memory
python main.py search "trading strategy" --agent hermes

# Interactive mode
python main.py interactive
```

### Programmatic

```python
from main import ObsidianMemorySystem

# Initialize
system = ObsidianMemorySystem(vault_path="~/vaults/AllenPrimaryNotes")

# Cross-agent query with verification
result = system.query_agent(
    querier="hermes",
    responder="claude",
    question="What are the key components of the trading system?"
)

# Result includes:
# - answer: Response from responder
# - evidence: Source citations with confidence
# - verification: Validity check with reasoning
```

## Agent Capabilities

### Codex
- Code generation and review
- Technical documentation lookup
- Pattern matching in vault code

### Claude Code
- Complex reasoning and analysis
- Architecture design
- Evidence verification with detailed reasoning
- Arbitration of disputes

### Hermes
- Multi-agent orchestration
- Query routing
- System monitoring
- Protocol enforcement

### OpenClaw
- Future extensibility
- Plugin hosting
- External integrations

## Evidence Format

```python
Evidence(
    source_type='memory',      # 'memory', 'arxiv', 'web', 'calculation'
    source_id='memory:abc123',   # Identifier
    quote='Relevant excerpt...', # The evidence text
    confidence=0.85              # Confidence score 0.0-1.0
)
```

## Verification

Answers are verified using:
1. **Evidence Existence**: Check if cited sources exist
2. **Source Diversity**: Multiple evidence types preferred
3. **Confidence Scoring**: Weighted average of evidence confidence
4. **Memory Verification**: Confirm evidence is retrievable

## Directory Structure

```
.
├── main.py                    # Entry point
├── requirements.txt           # Dependencies
├── shared/
│   ├── core/
│   │   └── obsidian_memory.py # Persistent memory layer
│   ├── protocols/
│   │   └── cross_agent_query.py # Query protocol
│   └── utils/
│       └── helpers.py         # Utilities
├── Codex/
│   └── agent.py              # Codex plugin
├── ClaudeCode/
│   └── agent.py              # Claude Code plugin
├── Hermes/
│   └── agent.py              # Hermes plugin
└── OpenClaw/
    └── agent.py              # OpenClaw stub
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OBSIDIAN_VAULT_PATH` | `~/vaults/AllenPrimaryNotes` | Path to Obsidian vault |

## Research References

- Wang et al. (2022). "Self-Consistency Improves Chain of Thought Reasoning in Language Models". ICLR 2023. arXiv:2203.11171
- Qian et al. (2023). "ChatDev: Communicative Agents for Software Development". ACL 2024. arXiv:2307.07924

## License

MIT
