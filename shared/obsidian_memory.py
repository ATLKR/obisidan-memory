"""
ObsidianMemory - Persistent Memory for AI Agents

Each agent uses Obsidian Vault as its independent persistent memory.
No cross-agent communication - agents share only through the Vault.
"""

import os
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict


@dataclass
class MemoryEntry:
    """A memory entry stored in Obsidian Vault."""
    id: str
    content: str
    source: str           # File path in vault (relative)
    agent: str            # Which agent created this
    timestamp: str
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        return cls(**data)


class ObsidianMemory:
    """
    Persistent memory interface using Obsidian Vault.
    
    Each agent has its own namespace but can read the entire vault.
    Agents share knowledge only through the Vault files.
    """
    
    def __init__(self, vault_path: Optional[str] = None, agent_name: str = "unknown"):
        """
        Initialize ObsidianMemory.
        
        Args:
            vault_path: Path to Obsidian vault. Uses OBSIDIAN_VAULT_PATH env var if not provided.
            agent_name: Name of the agent using this memory instance.
        """
        self.vault_path = vault_path or os.getenv('OBSIDIAN_VAULT_PATH', '~/vaults/AllenPrimaryNotes')
        self.vault_path = os.path.expanduser(self.vault_path)
        self.agent_name = agent_name
        
        # In-memory cache of entries
        self._cache: Dict[str, MemoryEntry] = {}
        
        # Cache directory for index
        self._cache_dir = Path.home() / '.obsidian_memory_cache'
        self._cache_dir.mkdir(exist_ok=True)
    
    def _generate_id(self, content: str) -> str:
        """Generate unique ID for memory entry."""
        hash_input = f"{content}{self.agent_name}{datetime.now().isoformat()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def read_file(self, rel_path: str) -> Optional[str]:
        """Read a file from the vault."""
        full_path = Path(self.vault_path) / rel_path
        if not full_path.exists():
            return None
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"[ObsidianMemory] Error reading {rel_path}: {e}")
            return None
    
    def write_file(self, rel_path: str, content: str, 
                   frontmatter: Optional[Dict] = None) -> bool:
        """
        Write a file to the vault with optional YAML frontmatter.
        """
        full_path = Path(self.vault_path) / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                if frontmatter:
                    f.write('---\n')
                    for key, value in frontmatter.items():
                        if isinstance(value, list):
                            f.write(f'{key}:\n')
                            for item in value:
                                f.write(f'  - {item}\n')
                        elif isinstance(value, dict):
                            f.write(f'{key}:\n')
                            for k, v in value.items():
                                f.write(f'  {k}: {v}\n')
                        else:
                            f.write(f'{key}: {value}\n')
                    f.write('---\n\n')
                f.write(content)
            return True
        except Exception as e:
            print(f"[ObsidianMemory] Error writing {rel_path}: {e}")
            return False
    
    def store(self, content: str, tags: List[str] = None,
              metadata: Dict[str, Any] = None,
              namespace: str = None) -> MemoryEntry:
        """
        Store content in the vault.
        
        Args:
            content: Content to store
            tags: List of tags for categorization
            metadata: Additional metadata to store in frontmatter
            namespace: Folder namespace (default: agent name)
        
        Returns:
            MemoryEntry with ID and source path
        """
        timestamp = datetime.now().isoformat()
        entry_id = self._generate_id(content)
        ns = namespace or self.agent_name
        
        # Create file path: <namespace>/<date>_<id>.md
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"{date_str}_{entry_id}.md"
        source = f"{ns}/{filename}"
        
        # Build frontmatter
        frontmatter = {
            'id': entry_id,
            'agent': self.agent_name,
            'timestamp': timestamp,
            'tags': tags or [],
        }
        if metadata:
            frontmatter['metadata'] = metadata
        
        # Write to vault
        success = self.write_file(source, content, frontmatter)
        if not success:
            raise RuntimeError(f"Failed to write memory to {source}")
        
        entry = MemoryEntry(
            id=entry_id,
            content=content,
            source=source,
            agent=self.agent_name,
            timestamp=timestamp,
            tags=tags or [],
            metadata=metadata or {}
        )
        
        self._cache[entry_id] = entry
        return entry
    
    def search(self, pattern: str, file_pattern: str = '*.md') -> List[Tuple[str, str]]:
        """
        Search for pattern in vault files.
        
        Returns:
            List of (rel_path, matching_content) tuples
        """
        matches = []
        vault_path = Path(self.vault_path)
        
        for file_path in vault_path.rglob(file_pattern):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(pattern, content, re.IGNORECASE):
                        rel_path = str(file_path.relative_to(vault_path))
                        # Return excerpt around match
                        match = re.search(pattern, content, re.IGNORECASE)
                        if match:
                            start = max(0, match.start() - 100)
                            end = min(len(content), match.end() + 100)
                            excerpt = content[start:end]
                            matches.append((rel_path, excerpt))
            except Exception:
                continue
        
        return matches
    
    def query(self, query_text: str, n_results: int = 5) -> List[MemoryEntry]:
        """
        Query memory by keyword matching.
        
        Args:
            query_text: Search query
            n_results: Number of results to return
        
        Returns:
            List of matching MemoryEntry objects
        """
        query_words = set(query_text.lower().split())
        results = []
        
        # Search all markdown files
        vault_path = Path(self.vault_path)
        for file_path in vault_path.rglob('*.md'):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    content_words = set(content.lower().split())
                    overlap = len(query_words & content_words)
                    if overlap > 0:
                        rel_path = str(file_path.relative_to(vault_path))
                        results.append((overlap, rel_path, content))
            except Exception:
                continue
        
        # Sort by relevance and return top N
        results.sort(reverse=True, key=lambda x: x[0])
        
        entries = []
        for score, path, content in results[:n_results]:
            # Try to extract frontmatter
            entry_id = hashlib.md5(content.encode()).hexdigest()[:12]
            timestamp = datetime.now().isoformat()
            
            entry = MemoryEntry(
                id=entry_id,
                content=content[:500],  # Truncate for preview
                source=path,
                agent="unknown",  # Could parse from frontmatter
                timestamp=timestamp,
                tags=[]
            )
            entries.append(entry)
        
        return entries
    
    def get_conversation_history(self, session_id: str = None, 
                                  limit: int = 10) -> List[MemoryEntry]:
        """
        Get recent conversation history from this agent's namespace.
        
        Args:
            session_id: Optional session ID to filter by
            limit: Maximum number of entries to return
        
        Returns:
            List of MemoryEntry objects
        """
        ns_path = Path(self.vault_path) / self.agent_name
        if not ns_path.exists():
            return []
        
        entries = []
        for file_path in sorted(ns_path.glob('*.md'), reverse=True)[:limit]:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                rel_path = str(file_path.relative_to(Path(self.vault_path)))
                
                # Parse frontmatter if present
                entry_id = ""
                timestamp = ""
                tags = []
                
                if content.startswith('---'):
                    try:
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            yaml_content = parts[1]
                            for line in yaml_content.split('\n'):
                                if line.startswith('id:'):
                                    entry_id = line.split(':', 1)[1].strip()
                                elif line.startswith('timestamp:'):
                                    timestamp = line.split(':', 1)[1].strip()
                                elif line.startswith('- '):
                                    tag = line.strip()[2:]
                                    tags.append(tag)
                    except Exception:
                        pass
                
                entry = MemoryEntry(
                    id=entry_id or hashlib.md5(content.encode()).hexdigest()[:12],
                    content=content,
                    source=rel_path,
                    agent=self.agent_name,
                    timestamp=timestamp or datetime.now().isoformat(),
                    tags=tags
                )
                entries.append(entry)
            except Exception:
                continue
        
        return entries
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        total_files = 0
        by_namespace = {}
        
        vault_path = Path(self.vault_path)
        for file_path in vault_path.rglob('*.md'):
            total_files += 1
            rel_path = file_path.relative_to(vault_path)
            ns = rel_path.parts[0] if rel_path.parts else "root"
            by_namespace[ns] = by_namespace.get(ns, 0) + 1
        
        return {
            'total_entries': total_files,
            'by_namespace': by_namespace,
            'vault_path': self.vault_path,
            'agent': self.agent_name
        }


# Singleton cache
_memory_instances: Dict[str, ObsidianMemory] = {}


def get_memory(agent_name: str, vault_path: Optional[str] = None) -> ObsidianMemory:
    """Get or create ObsidianMemory instance for an agent."""
    key = f"{agent_name}:{vault_path or os.getenv('OBSIDIAN_VAULT_PATH', '')}"
    if key not in _memory_instances:
        _memory_instances[key] = ObsidianMemory(vault_path, agent_name)
    return _memory_instances[key]
