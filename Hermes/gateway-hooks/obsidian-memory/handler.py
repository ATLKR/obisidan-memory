"""
Gateway hook handler for Obsidian Memory.

Runs in Gateway only (non-blocking, never crashes agent).
Receives events: agent:start, message:received, tool:after, agent:end
"""

import sys
from pathlib import Path

# Add shared module to path (adjust based on where plugin is installed)
# This assumes obsidian-memory plugin is cloned to a known location
SHARED_PATH = Path.home() / "obsidian-memory" / "shared"
if str(SHARED_PATH) not in sys.path:
    sys.path.insert(0, str(SHARED_PATH))

try:
    from obsidian_memory import get_memory
    
    # Initialize memory once
    memory = get_memory("hermes-gateway")
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False
    memory = None


async def handle(event_type: str, context: dict):
    """
    Called for each subscribed event.
    
    Args:
        event_type: The event name (e.g., 'agent:start')
        context: Event-specific data dict
    
    Must be named 'handle'. Can be async def or regular def.
    Errors are caught and logged, never crashing the agent.
    """
    if not MEMORY_AVAILABLE:
        return
    
    try:
        if event_type == "agent:start":
            _handle_agent_start(context)
        
        elif event_type == "message:received":
            _handle_message_received(context)
        
        elif event_type == "tool:after":
            _handle_tool_after(context)
        
        elif event_type == "agent:end":
            _handle_agent_end(context)
    
    except Exception:
        # Never crash the agent
        pass


def _handle_agent_start(context: dict):
    """Load recent context when agent starts."""
    if memory is None:
        return
    
    history = memory.get_conversation_history(limit=3)
    
    if history:
        # Add context to agent
        context["obsidian_context"] = {
            "loaded": True,
            "recent_entries": len(history),
            "vault_path": memory.vault_path,
            "last_entry": {
                "timestamp": history[0].timestamp,
                "preview": history[0].content[:100] + "..."
            }
        }


def _handle_message_received(context: dict):
    """Enrich incoming messages with vault context."""
    if memory is None:
        return
    
    message = context.get("message", "")
    
    # Skip short messages
    if len(message) < 10:
        return
    
    # Search vault for relevant content
    relevant = memory.query(message, n_results=3)
    
    if relevant:
        context["obsidian_enrichment"] = {
            "query": message[:50],
            "matches_found": len(relevant),
            "top_matches": [
                {
                    "source": e.source,
                    "agent": e.agent,
                    "preview": e.content[:150] + "...",
                    "tags": e.tags
                }
                for e in relevant[:2]  # Top 2 only
            ]
        }


def _handle_tool_after(context: dict):
    """Store important tool execution results."""
    if memory is None:
        return
    
    tool_name = context.get("tool", "unknown")
    tool_input = context.get("input", {})
    tool_output = context.get("output", "")
    
    # Only store for important tools
    if tool_name not in ["Edit", "Write", "Bash"]:
        return
    
    # Build content
    content_lines = [f"## Tool Execution: {tool_name}", ""]
    
    if "file_path" in tool_input:
        content_lines.append(f"**File:** `{tool_input['file_path']}`")
    
    if "command" in tool_input:
        cmd = tool_input["command"]
        # Don't store secrets
        if any(secret in cmd.lower() for secret in ["password", "token", "key", "secret"]):
            content_lines.append("**Command:** `[redacted for security]`")
        else:
            content_lines.append(f"**Command:** `{cmd[:100]}`")
    
    content = "\n".join(content_lines)
    
    # Store to vault
    try:
        entry = memory.store(
            content=content,
            tags=["hermes-gateway", "tool-execution", tool_name.lower()],
            metadata={
                "tool": tool_name,
                "has_output": len(str(tool_output)) > 0
            }
        )
        
        # Report success to context
        context["obsidian_stored"] = {
            "entry_id": entry.id,
            "source": entry.source
        }
    except Exception:
        pass


def _handle_agent_end(context: dict):
    """Store session summary when agent ends."""
    # Placeholder for session summary storage
    pass
