"""
Utilities for Obsidian Memory System

Common helper functions for agents.
"""

import os
import re
from typing import List, Dict, Optional, Any
from pathlib import Path


def extract_frontmatter(content: str) -> tuple[Dict[str, Any], str]:
    """
    Extract YAML frontmatter from markdown content.
    
    Args:
        content: Markdown file content
    
    Returns:
        Tuple of (frontmatter dict, remaining content)
    """
    frontmatter = {}
    
    # Check for frontmatter
    if content.startswith('---'):
        parts = content.split('---', 2)
        if len(parts) >= 3:
            yaml_content = parts[1].strip()
            remaining = parts[2].strip()
            
            # Simple YAML parsing (not full YAML spec)
            for line in yaml_content.split('\n'):
                line = line.strip()
                if ':' in line and not line.startswith('#'):
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Handle lists
                    if value.startswith('-'):
                        frontmatter[key] = []
                    elif value.startswith('[') and value.endswith(']'):
                        # Simple array parsing
                        items = value[1:-1].split(',')
                        frontmatter[key] = [item.strip().strip('"\'') for item in items]
                    elif value.startswith('"') and value.endswith('"'):
                        frontmatter[key] = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        frontmatter[key] = value[1:-1]
                    else:
                        # Try to convert to number or bool
                        if value.lower() == 'true':
                            frontmatter[key] = True
                        elif value.lower() == 'false':
                            frontmatter[key] = False
                        elif value.lower() == 'null' or value.lower() == '~':
                            frontmatter[key] = None
                        else:
                            try:
                                if '.' in value:
                                    frontmatter[key] = float(value)
                                else:
                                    frontmatter[key] = int(value)
                            except ValueError:
                                frontmatter[key] = value
            
            return frontmatter, remaining
    
    return frontmatter, content


def extract_wikilinks(content: str) -> List[str]:
    """
    Extract [[WikiLinks]] from Obsidian content.
    
    Args:
        content: Markdown content
    
    Returns:
        List of wiki link targets
    """
    pattern = r'\[\[([^\]|]+)(?:\|[^\]]+)?\]\]'
    matches = re.findall(pattern, content)
    return list(set(matches))  # Remove duplicates


def extract_tags(content: str) -> List[str]:
    """
    Extract #tags from Obsidian content.
    
    Args:
        content: Markdown content
    
    Returns:
        List of tags (without #)
    """
    pattern = r'#(\w+[-\w]*)'
    matches = re.findall(pattern, content)
    return list(set(matches))


def format_evidence(evidence_list: List[Dict[str, Any]]) -> str:
    """
    Format evidence list for display.
    
    Args:
        evidence_list: List of evidence dicts
    
    Returns:
        Formatted string
    """
    if not evidence_list:
        return "No evidence provided."
    
    parts = [f"### Evidence ({len(evidence_list)} citations)"]
    
    for i, ev in enumerate(evidence_list, 1):
        source = ev.get('source', 'Unknown')
        quote = ev.get('quote', '')
        confidence = ev.get('confidence', 0.5)
        
        parts.append(f"\n**{i}. {source}** (confidence: {confidence:.2f})")
        if quote:
            parts.append(f"> {quote[:200]}...")
    
    return '\n'.join(parts)


def sanitize_filename(name: str) -> str:
    """
    Sanitize a string for use as filename.
    
    Args:
        name: Original name
    
    Returns:
        Safe filename
    """
    # Replace unsafe characters
    safe = re.sub(r'[^\w\s-]', '', name)
    safe = re.sub(r'\s+', '_', safe)
    return safe[:100]  # Limit length


def truncate_content(content: str, max_length: int = 500, suffix: str = "...") -> str:
    """
    Truncate content to max length.
    
    Args:
        content: Original content
        max_length: Maximum length
        suffix: Suffix to add if truncated
    
    Returns:
        Truncated content
    """
    if len(content) <= max_length:
        return content
    
    return content[:max_length - len(suffix)] + suffix


def generate_markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    """
    Generate markdown table.
    
    Args:
        headers: Column headers
        rows: Table rows
    
    Returns:
        Markdown table string
    """
    lines = []
    
    # Header
    lines.append('| ' + ' | '.join(headers) + ' |')
    lines.append('|' + '|'.join(['---' for _ in headers]) + '|')
    
    # Rows
    for row in rows:
        lines.append('| ' + ' | '.join(str(cell) for cell in row) + ' |')
    
    return '\n'.join(lines)


def arxiv_id_from_url(url: str) -> Optional[str]:
    """
    Extract arXiv ID from URL.
    
    Args:
        url: URL string
    
    Returns:
        arXiv ID or None
    """
    patterns = [
        r'arxiv\.org/abs/(\d+\.\d+(?:v\d+)?)',
        r'arxiv\.org/pdf/(\d+\.\d+(?:v\d+)?)',
        r'arXiv:(\d+\.\d+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


class AgentLogger:
    """Simple logger for agent operations."""
    
    def __init__(self, agent_name: str, verbose: bool = True):
        self.agent_name = agent_name
        self.verbose = verbose
    
    def log(self, message: str, level: str = "INFO"):
        """Log a message."""
        if self.verbose or level in ["ERROR", "WARNING"]:
            print(f"[{level}] {self.agent_name}: {message}")
    
    def info(self, message: str):
        self.log(message, "INFO")
    
    def warning(self, message: str):
        self.log(message, "WARNING")
    
    def error(self, message: str):
        self.log(message, "ERROR")
    
    def debug(self, message: str):
        self.log(message, "DEBUG")


def get_env_or_default(key: str, default: Any = None) -> Any:
    """Get environment variable or default."""
    return os.getenv(key, default)


def ensure_dir(path: str) -> Path:
    """Ensure directory exists."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
