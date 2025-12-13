# Halftime Game 🏀

A Pygame-based desktop game where users view Period 1 tempo trends and predict whether Period 2 will play faster or slower than expected.

## Features

- Pre-generated tempo visualizations from cached plots
- Interactive prediction game (Fast/Slow)
- Score tracking across multiple games
- Visual feedback with color-coded results
- Auto-advance through games

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate Cache Files

Before running the game, you must generate cache files:

```bash
python scripts/generate_cache.py
```

This will create plot images and residual data files in `cache/plots/`.

### 3. Run the Game

```bash
python run_game.py
```

## Project Structure

```
halftime_game/
├── run_game.py              # Entry point (Pygame game)
├── app/
│   ├── game_pygame.py      # Game implementation
│   ├── data/               # Data loading modules
│   ├── tfs/                # TFS computation
│   ├── plots/              # Plot generation
│   └── util/               # Utilities
├── scripts/
│   ├── generate_cache.py   # Cache generation script
│   └── analyze_p2_stats.py # Analysis script
├── build_tfs/              # TFS processing pipeline
└── cache/plots/            # Pre-generated cache files
```

## Requirements

### Runtime (for `run_game.py`)
- Python 3.8+
- pygame >=2.5.0
- Pillow >=9.0.0
- numpy >=1.23.0

### Cache Generation (for `scripts/generate_cache.py`)
- All runtime dependencies plus:
- pandas >=1.5.0
- matplotlib >=3.6.0
- requests >=2.28.0
- google-cloud-bigquery >=3.11.0

## Usage

### Running the Game

1. Ensure cache files exist in `cache/plots/`
2. Run `python run_game.py`
3. Use ←/→ arrow keys or mouse clicks to make predictions
4. Press ESC to quit

### Generating Cache

1. Configure BigQuery credentials in `meatloaf.json`
2. Run `python scripts/generate_cache.py`
3. Cache files will be saved to `cache/plots/`

### Analysis

Run analysis on Period 2 statistics:

```bash
python scripts/analyze_p2_stats.py
```

## Documentation

- `PYGAME_REQS.md` - Detailed requirements for `run_game.py` and `analyze_p2_stats.py`
- `DEPENDENCY_REVIEW.md` - Dependency analysis and cleanup guide
- `HALFTIME_GAME_SPEC.md` - Original game specification

## Notes

- All plots must be pre-generated before running the game
- Cache files are read-only during gameplay
- Game loops through all cached games
- Score resets when looping back to start
