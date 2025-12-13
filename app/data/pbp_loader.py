"""Play-by-play data loading"""
import pandas as pd
from .get_pbp import get_pbp


def load_pbp(game_id: str, use_cache: bool = True) -> pd.DataFrame:
    """Load play-by-play data.
    
    Note: Caching is handled by the cache generation script.
    This function always fetches fresh data from the API.
    
    Args:
        game_id: Game identifier as string
        use_cache: Ignored (kept for API compatibility, but caching handled externally)
        
    Returns:
        DataFrame with play-by-play data
        
    Raises:
        ValueError: If no play data found
    """
    raw = get_pbp(int(game_id))
    if raw is None or len(raw) == 0:
        raise ValueError("No play data found.")
    return raw

