"""Plot caching utilities for fast plot loading"""
import os
import json
import pickle
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple, List, Callable
import matplotlib.pyplot as plt
import pandas as pd
from app.plots.tempo import build_tempo_figure
from app.data.pbp_loader import load_pbp
from app.data.status import classify_game_status_pbp
from app.data.bigquery_loader import get_closing_totals
from app.data.efg import calculate_efg_by_half
from app.tfs.preprocess import preprocess_pbp
from app.tfs.compute import compute_tfs


# Cache directory
CACHE_DIR = Path("cache/plots")
CACHE_METADATA_FILE = CACHE_DIR / "metadata.json"
CACHE_AGE_HOURS = 24  # Regenerate cache if older than 24 hours


def ensure_cache_dir():
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_metadata() -> Dict:
    """Load cache metadata."""
    ensure_cache_dir()
    if CACHE_METADATA_FILE.exists():
        try:
            with open(CACHE_METADATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}


def save_cache_metadata(metadata: Dict):
    """Save cache metadata."""
    ensure_cache_dir()
    with open(CACHE_METADATA_FILE, 'w') as f:
        json.dump(metadata, f, indent=2, default=str)


def is_cache_fresh() -> bool:
    """Check if cache is fresh (less than 24 hours old)."""
    metadata = get_cache_metadata()
    if not metadata or 'last_update' not in metadata:
        return False
    
    try:
        last_update = datetime.fromisoformat(metadata['last_update'])
        age = datetime.now() - last_update
        return age < timedelta(hours=CACHE_AGE_HOURS)
    except:
        return False


def get_missing_plots(game_ids: List[str]) -> List[str]:
    """Get list of game IDs that are missing from cache.
    
    Args:
        game_ids: List of game IDs to check
        
    Returns:
        List of game IDs that are missing plots
    """
    missing = []
    for game_id in game_ids:
        plot_path = get_plot_cache_path(game_id)
        if not plot_path.exists():
            missing.append(game_id)
    return missing


def get_all_cached_game_ids() -> List[str]:
    """Get list of all game IDs that have cached plots.
    
    Returns:
        List of game IDs (unique, extracted from filenames)
    """
    ensure_cache_dir()
    game_ids = set()
    
    # Find all PNG files (excluding residual data files)
    for png_file in CACHE_DIR.glob('*.png'):
        # Skip residual data files
        if png_file.name.endswith('_residuals.png'):
            continue
        # Extract game_id from filename (format: {game_id}.png)
        name = png_file.stem  # Gets filename without extension
        game_ids.add(name)
    
    return sorted(list(game_ids))


def commit_cache_to_git(dev_mode: bool = True) -> bool:
    """Commit cache plots to git.
    
    Args:
        dev_mode: If True, commits automatically. If False, only commits if needed.
        
    Returns:
        True if commit was made, False otherwise
    """
    import subprocess
    from pathlib import Path
    import glob
    
    try:
        # Check if we're in a git repo
        result = subprocess.run(
            ['git', 'rev-parse', '--git-dir'],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )
        if result.returncode != 0:
            return False  # Not a git repo
        
        # Find all PNG files in cache
        png_files = list(CACHE_DIR.glob('*.png'))
        if not png_files:
            return False  # No plots to commit
        
        # Check if there are changes to commit
        result = subprocess.run(
            ['git', 'status', '--porcelain', 'cache/plots/'],
            capture_output=True,
            text=True,
            cwd=Path.cwd()
        )
        
        if not result.stdout.strip():
            return False  # No changes
        
        # In dev mode, always commit
        if dev_mode:
            # Add all PNG files in cache directory (exclude residual data files)
            png_files = [f for f in CACHE_DIR.glob('*.png') if not f.name.endswith('_residuals.png')]
            if png_files:
                # Add all PNG files
                for png_file in png_files:
                    subprocess.run(
                        ['git', 'add', str(png_file)],
                        cwd=Path.cwd(),
                        capture_output=True,
                        check=False
                    )
            
            # Check if anything was staged
            result = subprocess.run(
                ['git', 'diff', '--cached', '--name-only'],
                cwd=Path.cwd(),
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip():
                return False  # Nothing to commit
            
            # Commit with timestamp
            commit_message = f"Update plot cache - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            result = subprocess.run(
                ['git', 'commit', '-m', commit_message],
                cwd=Path.cwd(),
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"✅ Committed plot cache to git")
                return True
            else:
                print(f"⚠️ Git commit failed: {result.stderr}")
                return False
        
        # In prod mode, could add logic to check if commit is needed
        # For now, return False (no auto-commit in prod)
        return False
        
    except Exception as e:
        print(f"Error committing cache to git: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def get_plot_cache_path(game_id: str) -> Path:
    """Get cache file path for a plot.
    
    Args:
        game_id: Game identifier
        
    Returns:
        Path to cached plot file
    """
    return CACHE_DIR / f"{game_id}.png"


def save_plot_to_cache(fig: plt.Figure, game_id: str):
    """Save a plot figure to cache.
    
    Args:
        fig: Matplotlib figure
        game_id: Game identifier
    """
    ensure_cache_dir()
    cache_path = get_plot_cache_path(game_id)
    fig.savefig(cache_path, dpi=100, bbox_inches='tight', format='png')
    plt.close(fig)  # Close figure to free memory


def load_plot_from_cache(game_id: str) -> Optional[str]:
    """Load a plot from cache.
    
    Args:
        game_id: Game identifier
        
    Returns:
        Path to cached plot file (as string) or None if not cached
    """
    cache_path = get_plot_cache_path(game_id)
    if cache_path.exists():
        return str(cache_path)
    return None


def get_residual_data_cache_path(game_id: str) -> Path:
    """Get cache file path for residual data."""
    return CACHE_DIR / f"{game_id}_residuals.pkl"


def save_residual_data_to_cache(residual_data: Dict, game_id: str):
    """Save residual data to cache."""
    ensure_cache_dir()
    cache_path = get_residual_data_cache_path(game_id)
    with open(cache_path, 'wb') as f:
        pickle.dump(residual_data, f)


def load_residual_data_from_cache(game_id: str) -> Optional[Dict]:
    """Load residual data from cache."""
    cache_path = get_residual_data_cache_path(game_id)
    if cache_path.exists():
        try:
            with open(cache_path, 'rb') as f:
                return pickle.load(f)
        except Exception as e:
            print(f"Error loading cached residual data for {game_id}: {e}")
            return None
    return None


def generate_plot_for_game(
    game_id: str,
    closing_total: Optional[float] = None,
    rotation_number: Optional[int] = None,
    lookahead_2h_total: Optional[float] = None,
    closing_spread_home: Optional[float] = None,
    home_team_name: Optional[str] = None,
    opening_2h_total: Optional[float] = None,
    closing_2h_total: Optional[float] = None,
    opening_2h_spread: Optional[float] = None,
    closing_2h_spread: Optional[float] = None
) -> Tuple[Optional[plt.Figure], Optional[Dict]]:
    """Generate plot for a single game.
    
    Args:
        game_id: Game identifier
        closing_total: Closing total
        rotation_number: Rotation number
        lookahead_2h_total: Lookahead 2H total
        closing_spread_home: Closing spread
        home_team_name: Home team name
        opening_2h_total: Opening 2H total
        closing_2h_total: Closing 2H total
        opening_2h_spread: Opening 2H spread
        closing_2h_spread: Closing 2H spread
        
    Returns:
        Tuple of (figure, residual_data)
        Note: Plot shows only Period 1, but residual_data includes full game stats
    """
    try:
        # Load and process game data
        raw_pbp = load_pbp(game_id)
        if raw_pbp is None or len(raw_pbp) == 0:
            return None, None
        
        df = preprocess_pbp(raw_pbp)
        tfs_df = compute_tfs(df)
        status = classify_game_status_pbp(raw_pbp)
        efg_1h, efg_2h = calculate_efg_by_half(raw_pbp)
        
        # Build plot
        fig, residual_data = build_tempo_figure(
            tfs_df,
            game_id,
            show_predictions=False,
            game_status=status,
            closing_total=closing_total,
            efg_first_half=efg_1h,
            efg_second_half=efg_2h,
            rotation_number=rotation_number,
            lookahead_2h_total=lookahead_2h_total,
            closing_spread_home=closing_spread_home,
            home_team_name=home_team_name,
            opening_2h_total=opening_2h_total,
            closing_2h_total=closing_2h_total,
            opening_2h_spread=opening_2h_spread,
            closing_2h_spread=closing_2h_spread,
            show_period_2=False  # Only show Period 1
        )
        
        return fig, residual_data
    except Exception as e:
        # Force flush to ensure error messages appear
        import sys
        error_msg = f"Error generating plot for game {game_id}: {e}"
        print(error_msg, file=sys.stderr, flush=True)
        import traceback
        tb = traceback.format_exc()
        print(tb, file=sys.stderr, flush=True)
        # Also print to stdout for visibility
        print(error_msg, flush=True)
        print(tb, flush=True)
        return None, None


def pregenerate_plots_for_games(
    game_ids: List[str],
    closing_totals: Dict[str, float],
    rotation_numbers: Dict[str, int],
    lookahead_2h_totals: Dict[str, float],
    closing_spread_home: Dict[str, float],
    home_team_names: Dict[str, str],
    opening_2h_totals: Dict[str, float],
    closing_2h_totals: Dict[str, float],
    opening_2h_spreads: Dict[str, float],
    closing_2h_spreads: Dict[str, float],
    progress_callback: Optional[Callable[[str, int, int], None]] = None,
    incremental: bool = True,
    dev_mode: bool = True
):
    """Pre-generate and cache plots for all games.
    
    Args:
        game_ids: List of game IDs
        closing_totals: Dict mapping game_id to closing_total
        rotation_numbers: Dict mapping game_id to rotation_number
        lookahead_2h_totals: Dict mapping game_id to lookahead_2h_total
        closing_spread_home: Dict mapping game_id to closing_spread_home
        home_team_names: Dict mapping game_id to home_team_name
        opening_2h_totals: Dict mapping game_id to opening_2h_total
        closing_2h_totals: Dict mapping game_id to closing_2h_total
        opening_2h_spreads: Dict mapping game_id to opening_2h_spread
        closing_2h_spreads: Dict mapping game_id to closing_2h_spread
        progress_callback: Optional callback function(game_id, current, total)
        incremental: If True, only generate missing plots. If False, regenerate all.
        dev_mode: If True, auto-commit to git after generation.
    """
    ensure_cache_dir()
    
    # If incremental, only process missing games (preserve historical cache)
    if incremental:
        games_to_process = get_missing_plots(game_ids)
    else:
        games_to_process = game_ids
    
    total = len(games_to_process)
    cached_count = len(game_ids) - total  # Games that were already cached
    generated_count = 0
    
    for idx, game_id in enumerate(games_to_process):
        if progress_callback:
            progress_callback(game_id, idx + 1, total)
        
        # Generate plot (Period 1 only)
        cache_path = get_plot_cache_path(game_id)
        
        # Skip if already cached (incremental mode)
        if incremental and cache_path.exists():
            cached_count += 1
            # Still need to check for residual data
            residual_path = get_residual_data_cache_path(game_id)
            if not residual_path.exists():
                # Need to generate to get residual data
                pass
            else:
                continue
        
        # Generate plot
        fig, residual_data = generate_plot_for_game(
            game_id,
            closing_total=closing_totals.get(game_id),
            rotation_number=rotation_numbers.get(game_id),
            lookahead_2h_total=lookahead_2h_totals.get(game_id),
            closing_spread_home=closing_spread_home.get(game_id),
            home_team_name=home_team_names.get(game_id),
            opening_2h_total=opening_2h_totals.get(game_id),
            closing_2h_total=closing_2h_totals.get(game_id),
            opening_2h_spread=opening_2h_spreads.get(game_id),
            closing_2h_spread=closing_2h_spreads.get(game_id)
        )
        
        if fig is not None:
            save_plot_to_cache(fig, game_id)
            generated_count += 1
            
            # Save residual data (includes full game stats for correctness calculation)
            if residual_data:
                save_residual_data_to_cache(residual_data, game_id)
        
        # Residual data should already be saved above, but check if missing
        residual_path = get_residual_data_cache_path(game_id)
        if not residual_path.exists() and residual_data:
            save_residual_data_to_cache(residual_data, game_id)
    
    # Update metadata
    metadata = {
        'last_update': datetime.now().isoformat(),
        'total_games': len(game_ids),
        'processed_games': total,
        'cached_plots': cached_count,
        'generated_plots': generated_count
    }
    save_cache_metadata(metadata)
    
    # Auto-commit to git in dev mode if plots were generated
    if dev_mode and generated_count > 0:
        commit_cache_to_git(dev_mode=True)
    
    return metadata

