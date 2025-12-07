# Plot Cache Directory

This directory contains pre-rendered plot images for fast loading in the Halftime Game dashboard.

## Files

- `{game_id}_hidden.png` - Plot with Period 2 hidden (black overlay)
- `{game_id}_visible.png` - Plot with Period 2 visible (no overlay)
- `{game_id}_residuals.pkl` - Residual data for correctness calculation (excluded from git)
- `metadata.json` - Cache metadata (excluded from git)

## Cache Management

- **Historical Cache**: All plots are preserved - old games are never deleted
- **Incremental Updates**: Only missing plots are generated (preserves historical data)
- **Auto-Regeneration**: Cache is checked on dashboard startup
- **24-Hour Refresh**: If cache metadata is > 24 hours old, missing plots are generated
- **Fast Loading**: Plots load instantly from disk (no generation delay)

## Git Integration

### Dev Mode (Current)
- Plot PNG files are automatically committed to git after generation
- Commits happen when new plots are generated
- Historical plots accumulate in git over time

### Production Mode (Future)
- Add logic to check if commit is needed before committing
- Can be configured to commit on schedule or manually

## File Naming

- `{game_id}_hidden.png` - Period 2 hidden with black overlay
- `{game_id}_visible.png` - Period 2 visible (no overlay)

Example: `401827508_hidden.png`, `401827508_visible.png`

## Size

PNG files are optimized for size (~50-200KB each) and are small enough to commit to git. The cache grows over time as historical games are preserved.

