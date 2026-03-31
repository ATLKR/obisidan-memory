#!/usr/bin/env python3
"""
PostToolUse Hook - Store tool execution results to Obsidian

This hook runs after tool execution and stores important results
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
    # Read hook input
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        hook_input = {}
    
    tool_name = hook_input.get('tool', {}).get('name', '')
    tool_input = hook_input.get('tool', {}).get('input', {})
    tool_output = hook_input.get('output', {})
    
    # Only store for specific important tools
    important_tools = ['Read', 'Edit', 'Bash']
    if tool_name not in important_tools:
        print(json.dumps({}))
        return
    
    # Get memory instance
    memory = get_memory('codex')
    
    # Build content to store
    content_lines = [f"## Tool Execution: {tool_name}", ""]
    
    if 'file_path' in tool_input:
        content_lines.append(f"**File:** {tool_input['file_path']}")
    if 'command' in tool_input:
        content_lines.append(f"**Command:** `{tool_input['command']}`")
    
    content_lines.append("")
    content_lines.append("### Input")
    content_lines.append(f"```json\n{json.dumps(tool_input, indent=2)}\n```")
    content_lines.append("")
    
    # Store if it seems important
    if tool_name in ['Edit'] or (tool_name == 'Bash' and len(str(tool_output)) > 500):
        content = '\n'.join(content_lines)
        try:
            entry = memory.store(
                content=content,
                tags=['tool-execution', tool_name.lower()],
                metadata={
                    'tool': tool_name,
                    'tool_input': tool_input
                }
            )
            
            # Return empty output (we just stored to vault)
            print(json.dumps({}))
        except Exception:
            print(json.dumps({}))
    else:
        print(json.dumps({}))


if __name__ == '__main__':
    main()
