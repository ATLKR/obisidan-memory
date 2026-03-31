"""
ObsidianMemory - Persistent Memory Layer for Multi-Agent Systems

Uses qmd library to read/write from Obsidian Vault with vector search capabilities.
Based on research from Self-Consistency (2203.11171) and ChatDev (2307.07924).
"""

import os
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict


try:
    import qmd
except ImportError:
    qmd = None

try:
    import numpy as np
except ImportError:
    np = None


@dataclass
class MemoryEntry:
    """Single memory entry with metadata for evidence tracking."""
    id: str
    content: str
    source: str  # File path in vault
    agent: str  # Which agent created this
    timestamp: str
    tags: List[str] = field(default_factory=list)
    evidence: List[Dict[str, Any]] = field(default_factory=list)  # Citations/sources
    confidence: float = 1.0  # Self-consistency score
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryEntry':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class QueryResult:
    """Result of a memory query with evidence."""
    query: str
    results: List[MemoryEntry]
    confidence: float
    evidence_summary: str
    sources: List[str] = field(default_factory=list)


class ObsidianMemory:
    """
    Persistent memory interface using Obsidian Vault.
    
    Implements patterns from:
    - Self-Consistency: Multiple retrieval paths, consistent answer selection
    - ChatDev: Communicative memory with source tracking
    """
    
    def __init__(self, vault_path: Optional[str] = None):
        """
        Initialize ObsidianMemory.
        
        Args:
            vault_path: Path to Obsidian vault. If None, reads from OBSIDIAN_VAULT_PATH env var.
        """
        self.vault_path = vault_path or os.getenv('OBSIDIAN_VAULT_PATH', '~/vaults/AllenPrimaryNotes')
        self.vault_path = os.path.expanduser(self.vault_path)
        
        # Memory index
        self._memory_index: Dict[str, MemoryEntry] = {}
        self._tag_index: Dict[str, List[str]] = {}
        
        # Cache directory for embeddings and index
        self._cache_dir = Path.home() / '.obsidian_memory_cache'
        self._cache_dir.mkdir(exist_ok=True)
        
        # Load existing index if available
        self._load_index()
    
    def _generate_id(self, content: str, source: str) -> str:
        """Generate unique ID for memory entry."""
        hash_input = f"{content}{source}{datetime.now().isoformat()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:12]
    
    def _load_index(self) -> None:
        """Load memory index from cache."""
        index_file = self._cache_dir / 'memory_index.json'
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    data = json.load(f)
                    self._memory_index = {
                        k: MemoryEntry.from_dict(v) for k, v in data.items()
                    }
            except Exception as e:
                print(f"Warning: Could not load index: {e}")
    
    def _save_index(self) -> None:
        """Save memory index to cache."""
        index_file = self._cache_dir / 'memory_index.json'
        try:
            with open(index_file, 'w') as f:
                json.dump(
                    {k: v.to_dict() for k, v in self._memory_index.items()},
                    f,
                    indent=2
                )
        except Exception as e:
            print(f"Warning: Could not save index: {e}")
    
    def read_vault_file(self, rel_path: str) -> Optional[str]:
        """
        Read a file from the Obsidian vault.
        
        Args:
            rel_path: Relative path from vault root (e.g., 'Notes/Work-Logs/test.md')
        
        Returns:
            File content or None if not found
        """
        full_path = Path(self.vault_path) / rel_path
        if not full_path.exists():
            return None
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {rel_path}: {e}")
            return None
    
    def write_vault_file(self, rel_path: str, content: str, 
                         frontmatter: Optional[Dict] = None) -> bool:
        """
        Write a file to the Obsidian vault with optional YAML frontmatter.
        
        Args:
            rel_path: Relative path from vault root
            content: Markdown content
            frontmatter: Optional YAML frontmatter dict
        
        Returns:
            True if successful
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
                        else:
                            f.write(f'{key}: {value}\n')
                    f.write('---\n\n')
                f.write(content)
            return True
        except Exception as e:
            print(f"Error writing {rel_path}: {e}")
            return False
    
    def search_vault(self, pattern: str, file_pattern: str = '*.md') -> List[str]:
        """
        Search for pattern in vault files.
        
        Args:
            pattern: Regex pattern to search for
            file_pattern: Glob pattern for files to search
        
        Returns:
            List of matching file paths (relative to vault)
        """
        matches = []
        vault_path = Path(self.vault_path)
        
        for file_path in vault_path.rglob(file_pattern):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if re.search(pattern, content, re.IGNORECASE):
                        rel_path = str(file_path.relative_to(vault_path))
                        matches.append(rel_path)
            except Exception:
                continue
        
        return matches
    
    def store(self, content: str, agent: str, tags: List[str] = None,
              evidence: List[Dict] = None, namespace: str = 'conversations') -> MemoryEntry:
        """
        Store a memory entry with metadata.
        
        Args:
            content: Content to store
            agent: Agent identifier (e.g., 'codex', 'claude', 'hermes')
            tags: List of tags for categorization
            evidence: List of evidence dicts with 'source', 'quote', 'confidence'
            namespace: Folder namespace in vault (e.g., 'conversations', 'research')
        
        Returns:
            MemoryEntry with ID
        """
        # Generate entry
        timestamp = datetime.now().isoformat()
        source = f"{namespace}/{agent}/{datetime.now().strftime('%Y-%m-%d')}_{self._generate_id(content, agent)}.md"
        
        entry = MemoryEntry(
            id=self._generate_id(content, agent),
            content=content,
            source=source,
            agent=agent,
            timestamp=timestamp,
            tags=tags or [],
            evidence=evidence or [],
            confidence=self._calculate_confidence(evidence or [])
        )
        
        # Store in vault
        frontmatter = {
            'id': entry.id,
            'agent': agent,
            'timestamp': timestamp,
            'tags': tags or [],
            'evidence': evidence or [],
            'confidence': entry.confidence
        }
        
        success = self.write_vault_file(source, content, frontmatter)
        if not success:
            raise RuntimeError(f"Failed to write memory to {source}")
        
        # Update index
        self._memory_index[entry.id] = entry
        for tag in (tags or []):
            if tag not in self._tag_index:
                self._tag_index[tag] = []
            self._tag_index[tag].append(entry.id)
        
        self._save_index()
        
        return entry
    
    def _calculate_confidence(self, evidence: List[Dict]) -> float:
        """
        Calculate confidence score based on evidence quality.
        Based on Self-Consistency principle: more consistent evidence = higher confidence.
        """
        if not evidence:
            return 0.5  # Neutral confidence with no evidence
        
        # Average confidence from evidence
        confidences = [e.get('confidence', 0.5) for e in evidence]
        return sum(confidences) / len(confidences)
    
    def query(self, query_text: str, agent_filter: Optional[str] = None,
              tag_filter: Optional[str] = None, n_results: int = 5) -> QueryResult:
        """
        Query memory with semantic similarity (fallback to keyword if embeddings unavailable).
        
        Args:
            query_text: Query string
            agent_filter: Optional agent name to filter by
            tag_filter: Optional tag to filter by
            n_results: Number of results to return
        
        Returns:
            QueryResult with ranked entries and evidence summary
        """
        # Filter candidates
        candidates = list(self._memory_index.values())
        
        if agent_filter:
            candidates = [c for c in candidates if c.agent == agent_filter]
        
        if tag_filter and tag_filter in self._tag_index:
            valid_ids = set(self._tag_index[tag_filter])
            candidates = [c for c in candidates if c.id in valid_ids]
        
        # Score candidates (keyword-based fallback)
        query_words = set(query_text.lower().split())
        scored = []
        for entry in candidates:
            entry_words = set(entry.content.lower().split())
            overlap = len(query_words & entry_words)
            score = overlap / max(len(query_words), 1)
            scored.append((score, entry))
        
        # Sort by score and return top N
        scored.sort(reverse=True, key=lambda x: x[0])
        top_results = [entry for _, entry in scored[:n_results]]
        
        # Generate evidence summary
        sources = list(set([e.source for e in top_results]))
        avg_confidence = sum(e.confidence for e in top_results) / max(len(top_results), 1)
        
        evidence_summary = self._generate_evidence_summary(top_results)
        
        return QueryResult(
            query=query_text,
            results=top_results,
            confidence=avg_confidence,
            evidence_summary=evidence_summary,
            sources=sources
        )
    
    def _generate_evidence_summary(self, entries: List[MemoryEntry]) -> str:
        """Generate human-readable evidence summary from entries."""
        if not entries:
            return "No relevant memories found."
        
        parts = [f"Found {len(entries)} relevant memory entries:"]
        for i, entry in enumerate(entries, 1):
            parts.append(f"\n{i}. From {entry.agent} ({entry.timestamp[:10]}):")
            parts.append(f"   Content: {entry.content[:150]}...")
            if entry.evidence:
                parts.append(f"   Evidence: {len(entry.evidence)} citations")
                for ev in entry.evidence[:2]:  # Show top 2
                    parts.append(f"     - {ev.get('source', 'Unknown')}: {ev.get('quote', '')[:50]}...")
        
        return '\n'.join(parts)
    
    def get_conversation_thread(self, thread_id: str) -> List[MemoryEntry]:
        """
        Retrieve a conversation thread by ID.
        
        Args:
            thread_id: Thread identifier
        
        Returns:
            List of MemoryEntry in chronological order
        """
        # Search for entries with this thread_id in tags or content
        results = []
        for entry in self._memory_index.values():
            if thread_id in entry.tags or thread_id in entry.content:
                results.append(entry)
        
        # Sort by timestamp
        results.sort(key=lambda e: e.timestamp)
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        agents = {}
        for entry in self._memory_index.values():
            agents[entry.agent] = agents.get(entry.agent, 0) + 1
        
        return {
            'total_entries': len(self._memory_index),
            'by_agent': agents,
            'indexed_tags': len(self._tag_index),
            'vault_path': self.vault_path
        }


# Singleton instance for shared access
_memory_instance: Optional[ObsidianMemory] = None


def get_memory(vault_path: Optional[str] = None) -> ObsidianMemory:
    """Get or create singleton ObsidianMemory instance."""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = ObsidianMemory(vault_path)
    return _memory_instance
