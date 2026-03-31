#!/usr/bin/env python3
"""
SessionStart Hook - Load context from Obsidian Vault

This hook runs at the start of a Codex session and:
1. Loads recent conversation history
2. Searches for relevant project context
3. Returns context for Codex to use
"""

import json
import sys
from pathlib import Path

# Add shared module to path
SHARED_PATH = Path(__file__).parent.parent.parent.parent.parent.parent.parent / 'shared'
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

from obsidian_memory import get_memory


def main():
    # Read hook input from stdin (Codex format)
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        hook_input = {}
    
    # Get memory instance
    memory = get_memory('codex')
    
    # Load recent history
    history = memory.get_conversation_history(limit=5)
    
    # Search for project docs
    project_context = memory.search(r'# .*?(Project|Overview|Architecture)', '*.md')[:3]
    
    # Build context
    context_lines = ["## Recent Context from Obsidian Vault\n"]
    
    if history:
        context_lines.append("### Recent Conversations\n")
        for entry in history[:3]:
            content_preview = entry.content[:200].replace('\n', ' ')
            context_lines.append(f"- [{entry.timestamp[:10]}] {content_preview}...")
        context_lines.append("")
    
    if project_context:
        context_lines.append("### Project Documentation\n")
        for path, excerpt in project_context:
            context_lines.append(f"- {path}: {excerpt[:100]}...")
        context_lines.append("")
    
    context_summary = '\n'.join(context_lines)
    
    # Output for Codex (instructionsAppendix format)
    output = {
        "instructionsAppendix": context_summary
    }
    
    print(json.dumps(output))


if __name__ == '__main__':
    main()
