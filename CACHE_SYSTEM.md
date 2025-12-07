# Plot Cache System Documentation

## Overview

The Halftime Game uses a pre-rendered plot cache system for maximum speed. All plots are generated upfront and stored as PNG files, allowing instant loading during gameplay.

## Key Features

### 1. Historical Cache Preservation
- **All plots are preserved** - old games are never deleted
- Historical cache accumulates over time
- Can load plots for any game that was ever cached
- Unlike the original project, we keep historical data

### 2. Incremental Updates
- Only generates **missing plots** (doesn't regenerate existing ones)
- Preserves all historical plots
- Fast cache updates (only new games are processed)

### 3. Auto-Git Commits (Dev Mode)
- Automatically commits new plot PNG files to git after generation
- Commits happen when cache is regenerated
- Historical plots accumulate in git over time
- Ready for production mode with conditional commit logic

### 4. Fast Loading
- Plots load instantly from disk (no generation delay)
- Uses `st.image()` for cached plots (faster than `st.pyplot()`)
- Residual data cached separately for instant correctness calculation

## Cache Structure

```
cache/plots/
├── {game_id}_hidden.png      # Plot with Period 2 hidden (black overlay)
├── {game_id}_visible.png     # Plot with Period 2 visible (no overlay)
├── {game_id}_residuals.pkl   # Residual data (excluded from git)
└── metadata.json             # Cache metadata (excluded from git)
```

## Cache Lifecycle

### On Dashboard Startup:
1. Check if cache metadata is fresh (< 24 hours old)
2. If stale:
   - Find missing plots (games without both `_hidden.png` and `_visible.png`)
   - Generate only missing plots (incremental mode)
   - Preserve all existing historical plots
   - Auto-commit new plots to git (dev mode)
3. If fresh:
   - Use existing cache (no generation needed)

### During Gameplay:
1. Load plot from cache (instant)
2. If not cached, generate on-the-fly (fallback)
3. Load residual data from cache (instant correctness calculation)

## Git Integration

### Dev Mode (Current)
- **Auto-commit**: New plots are automatically committed to git
- **Commit message**: `"Update plot cache - {timestamp}"`
- **Files committed**: Only PNG files (`.pkl` and `metadata.json` excluded)

### Production Mode (Future)
- Add conditional commit logic
- Can be scheduled (e.g., daily commit)
- Or manual commit via script: `python scripts/commit_cache.py`

## File Sizes

- PNG files: ~50-200KB each (small enough for git)
- Total cache grows over time as historical games accumulate
- `.pkl` files excluded from git (can be regenerated)
- `metadata.json` excluded from git (can be regenerated)

## Functions

### Core Functions
- `pregenerate_plots_for_games()` - Generate and cache plots
- `load_plot_from_cache()` - Load cached plot (returns file path)
- `load_residual_data_from_cache()` - Load cached residual data
- `get_missing_plots()` - Find games missing from cache
- `get_all_cached_game_ids()` - List all cached game IDs
- `is_cache_fresh()` - Check if cache is < 24 hours old
- `commit_cache_to_git()` - Commit cache to git

### Configuration
- `CACHE_AGE_HOURS = 24` - Cache refresh threshold
- `CACHE_DIR = "cache/plots"` - Cache directory location

## Usage

### Automatic (Recommended)
Cache is automatically managed by the dashboard:
- Checks freshness on startup
- Generates missing plots
- Commits to git (dev mode)

### Manual Cache Generation
```python
from app.util.plot_cache import pregenerate_plots_for_games

pregenerate_plots_for_games(
    game_ids,
    closing_totals,
    rotation_numbers,
    # ... other market data ...
    incremental=True,  # Only generate missing
    dev_mode=True      # Auto-commit to git
)
```

### Manual Git Commit
```bash
python scripts/commit_cache.py
```

## Best Practices

1. **Historical Preservation**: Always use `incremental=True` to preserve historical cache
2. **Git Commits**: In dev mode, commits happen automatically. In prod, add conditional logic.
3. **Cache Size**: Monitor cache size over time. PNG files are small, but many games will accumulate.
4. **Performance**: Cache provides instant plot loading - no generation delay between games.

## Migration Notes

- Original project: Only kept recent games
- Halftime Game: Keeps all historical games
- Cache grows over time but remains fast (disk I/O is quick)
- Git history preserves plot evolution over time

