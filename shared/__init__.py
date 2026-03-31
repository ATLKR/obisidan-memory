"""Shared components for Obsidian Memory System."""

from shared.core.obsidian_memory import ObsidianMemory, MemoryEntry, QueryResult, get_memory
from shared.protocols.cross_agent_query import (
    CrossAgentQuery, QueryMessage, Evidence, VerificationResult,
    QueryStatus, AgentRole, create_protocol
)
from shared.utils.helpers import (
    extract_frontmatter, extract_wikilinks, extract_tags,
    format_evidence, sanitize_filename, AgentLogger
)

__all__ = [
    # Core
    'ObsidianMemory', 'MemoryEntry', 'QueryResult', 'get_memory',
    # Protocols
    'CrossAgentQuery', 'QueryMessage', 'Evidence', 'VerificationResult',
    'QueryStatus', 'AgentRole', 'create_protocol',
    # Utils
    'extract_frontmatter', 'extract_wikilinks', 'extract_tags',
    'format_evidence', 'sanitize_filename', 'AgentLogger'
]
