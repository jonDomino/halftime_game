"""Game status caching to disk - persist across sessions"""
import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime

# Cache directory
CACHE_DIR = Path("cache")
STATUS_CACHE_FILE = CACHE_DIR / "game_statuses.json"


def ensure_cache_dir():
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_status_cache() -> Dict[str, str]:
    """Load game status cache from disk.
    
    Returns:
        Dictionary mapping game_id to status
    """
    ensure_cache_dir()
    if STATUS_CACHE_FILE.exists():
        try:
            with open(STATUS_CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_status_cache(statuses: Dict[str, str]):
    """Save game status cache to disk.
    
    Args:
        statuses: Dictionary mapping game_id to status
    """
    ensure_cache_dir()
    # Load existing cache and update it
    existing = load_status_cache()
    existing.update(statuses)
    
    with open(STATUS_CACHE_FILE, 'w') as f:
        json.dump(existing, f, indent=2)


def get_cached_status(game_id: str) -> Optional[str]:
    """Get cached status for a game.
    
    Args:
        game_id: Game identifier
        
    Returns:
        Status string or None if not cached
    """
    cache = load_status_cache()
    return cache.get(game_id)


def cache_status(game_id: str, status: str):
    """Cache a game's status.
    
    Args:
        game_id: Game identifier
        status: Status string
    """
    save_status_cache({game_id: status})

