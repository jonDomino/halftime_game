# Simplified Halftime Game - Project Plan

## Overview

This plan outlines a drastically simplified version optimized for **UX speed**. The project is split into two parts:

1. **One-time cache generation script** (run locally, push to git)
2. **Ultra-simple dashboard** (loads cached plots, shows game, tracks score)

---

## Part 1: One-Time Cache Generation Script

### Purpose
A standalone Python script that runs **once locally** to:
- Fetch PBP data for games 11/1/25-11/5/25
- Generate all plots (with Period 2 hidden overlay)
- Save plots and residual data to `cache/plots/`
- User then commits and pushes to git

### File Structure
```
scripts/
  └── generate_cache.py  # NEW: Standalone cache generation script
```

### Script Flow

```python
# scripts/generate_cache.py

1. Define date range: 11/1/25 - 11/5/25
2. Load schedule for those dates
3. Get all game_ids for those dates
4. Fetch market data (closing_totals, etc.) for all games
5. For each game_id:
   a. Load PBP data
   b. Process TFS data
   c. Generate plot with Period 2 hidden overlay
   d. Save plot as PNG: cache/plots/{game_id}_hidden.png
   e. Save residual data as PKL: cache/plots/{game_id}_residuals.pkl
6. Print summary: "Generated X plots for Y games"
7. Exit (user commits to git manually)
```

### Key Functions to Reuse
- `app/data/schedule_loader.load_schedule()` - Get schedule
- `app/data/pbp_loader.load_pbp()` - Get PBP
- `app/data/bigquery_loader.get_closing_totals()` - Get market data
- `app/tfs/preprocess.preprocess_pbp()` - Preprocess
- `app/tfs/compute.compute_tfs()` - Compute TFS
- `app/plots/tempo.build_tempo_figure()` - Generate plot
- `app/util/plot_cache.save_plot_to_cache()` - Save plot
- `app/util/plot_cache.save_residual_data_to_cache()` - Save residuals

### What This Script Does NOT Do
- ❌ No Streamlit UI
- ❌ No cache freshness checks
- ❌ No git auto-commit (user does this manually)
- ❌ No incremental generation (always regenerates all)
- ❌ No status checking (assumes all games are completed)

### Expected Output
```
cache/plots/
  ├── {game_id}_hidden.png      # Plot with Period 2 hidden
  ├── {game_id}_residuals.pkl   # Residual data (for correctness calculation)
  └── ... (one set per game)
```

---

## Part 2: Ultra-Simple Dashboard

### Purpose
A minimal Streamlit app that:
- Loads all cached plots on startup
- Shows one plot at a time
- Lets user pick Fast or Slow
- Shows correctness immediately
- Tracks score
- Advances to next game

### File Structure
```
app/
  └── main.py  # COMPLETELY REWRITE - ultra simple
streamlit_app.py  # Keep as thin wrapper
```

### Dashboard Flow

```
On Startup:
1. Scan cache/plots/ for all {game_id}_hidden.png files
2. Extract game_ids from filenames
3. Load all residual data files
4. Store in memory: game_ids list, residual_data dict
5. Initialize session state:
   - current_game_index = 0
   - score_tally = {'correct': 0, 'total': 0}
   - game_states = {}  # Per-game prediction state

On Each Render:
1. Get current game_id from game_ids[current_game_index]
2. Load cached plot: cache/plots/{game_id}_hidden.png
3. Display plot using st.image()
4. If prediction not made:
   - Show "Fast" and "Slow" buttons
5. If prediction made:
   - Load residual_data for this game
   - Calculate correctness (median_residual_p2 > 0 = slow, < 0 = fast)
   - Show result: "Correct! 2H went {slower/faster}" or "Incorrect. 2H went {slower/faster}"
   - Update score tally
   - Auto-advance to next game (st.rerun())
```

### Simplified `app/main.py` Structure

```python
# app/main.py - ULTRA SIMPLIFIED

import streamlit as st
from pathlib import Path
import pickle
from PIL import Image

# Constants
CACHE_DIR = Path("cache/plots")
TARGET_DATES = [date(2025, 11, 1), date(2025, 11, 2), ..., date(2025, 11, 5)]

def get_all_cached_games():
    """Scan cache directory and return list of game_ids with cached plots."""
    game_ids = []
    for png_file in CACHE_DIR.glob("*_hidden.png"):
        game_id = png_file.stem.replace("_hidden", "")
        game_ids.append(game_id)
    return sorted(game_ids)

def load_all_residual_data(game_ids):
    """Load all residual data files into a dict."""
    residuals = {}
    for game_id in game_ids:
        pkl_path = CACHE_DIR / f"{game_id}_residuals.pkl"
        if pkl_path.exists():
            with open(pkl_path, 'rb') as f:
                residuals[game_id] = pickle.load(f)
    return residuals

def init_session_state():
    """Initialize all session state variables."""
    if 'game_ids' not in st.session_state:
        st.session_state.game_ids = get_all_cached_games()
    
    if 'residual_data' not in st.session_state:
        st.session_state.residual_data = load_all_residual_data(st.session_state.game_ids)
    
    if 'current_game_index' not in st.session_state:
        st.session_state.current_game_index = 0
    
    if 'score_tally' not in st.session_state:
        st.session_state.score_tally = {'correct': 0, 'total': 0}
    
    if 'game_states' not in st.session_state:
        st.session_state.game_states = {}

def get_game_state(game_id):
    """Get or create game state for a game."""
    if game_id not in st.session_state.game_states:
        st.session_state.game_states[game_id] = {
            'prediction_made': False,
            'user_prediction': None,  # "fast" or "slow"
            'correctness': None  # True/False/None
        }
    return st.session_state.game_states[game_id]

def calculate_correctness(game_id, user_prediction, residual_data):
    """Calculate if user prediction was correct."""
    median_residual_p2 = residual_data.get('median_residual_p2', 0)
    actual_result = "slow" if median_residual_p2 > 0 else "fast"
    return (user_prediction == actual_result), actual_result

def render():
    """Main render function - ultra simple."""
    st.set_page_config(page_title="Halftime Game", layout="centered")
    st.title("Halftime Game 🏀")
    
    init_session_state()
    
    game_ids = st.session_state.game_ids
    if not game_ids:
        st.error("No cached plots found. Run scripts/generate_cache.py first.")
        return
    
    # Get current game
    current_idx = st.session_state.current_game_index
    if current_idx >= len(game_ids):
        st.session_state.current_game_index = 0
        current_idx = 0
    
    current_game_id = game_ids[current_idx]
    game_state = get_game_state(current_game_id)
    residual_data = st.session_state.residual_data.get(current_game_id)
    
    # Display score
    score = st.session_state.score_tally
    st.info(f"🎯 Score: {score['correct']} of {score['total']} correct")
    
    # Display progress
    st.caption(f"Game {current_idx + 1} of {len(game_ids)}")
    
    # Load and display plot
    plot_path = CACHE_DIR / f"{current_game_id}_hidden.png"
    if plot_path.exists():
        img = Image.open(plot_path)
        st.image(img, use_container_width=True)
    else:
        st.error(f"Plot not found for game {current_game_id}")
        return
    
    # Show prediction buttons if not made
    if not game_state['prediction_made']:
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚡ Fast", key=f"fast_{current_game_id}"):
                game_state['user_prediction'] = "fast"
                game_state['prediction_made'] = True
                st.rerun()
        with col2:
            if st.button("🐌 Slow", key=f"slow_{current_game_id}"):
                game_state['user_prediction'] = "slow"
                game_state['prediction_made'] = True
                st.rerun()
    else:
        # Prediction made - show result
        if game_state['correctness'] is None and residual_data:
            # Calculate correctness (only once)
            is_correct, actual_result = calculate_correctness(
                current_game_id,
                game_state['user_prediction'],
                residual_data
            )
            game_state['correctness'] = is_correct
            
            # Update score (only once)
            st.session_state.score_tally['total'] += 1
            if is_correct:
                st.session_state.score_tally['correct'] += 1
            
            # Show result
            if is_correct:
                st.success(f"✅ Correct! 2H went {actual_result}")
            else:
                st.error(f"❌ Incorrect. 2H went {actual_result}")
            
            # Auto-advance to next game
            if current_idx < len(game_ids) - 1:
                st.session_state.current_game_index += 1
            else:
                st.session_state.current_game_index = 0  # Loop back
            st.rerun()
        else:
            # Already calculated - just show result
            if game_state['correctness'] is not None and residual_data:
                median_residual_p2 = residual_data.get('median_residual_p2', 0)
                actual_result = "slower" if median_residual_p2 > 0 else "faster"
                if game_state['correctness']:
                    st.success(f"✅ Correct! 2H went {actual_result}")
                else:
                    st.error(f"❌ Incorrect. 2H went {actual_result}")
```

### What the Dashboard Does NOT Do
- ❌ No date selector
- ❌ No board filter
- ❌ No game selector
- ❌ No status checking
- ❌ No tabs
- ❌ No refresh logic
- ❌ No cache freshness checks
- ❌ No API calls (everything from cache)
- ❌ No market data fetching (already in cache)
- ❌ No PBP loading (already processed)
- ❌ No plot generation (all pre-rendered)

---

## Part 3: What Gets Removed

### Files to Delete/Simplify
- ❌ `app/ui/selectors.py` - No longer needed (no filters)
- ❌ `app/util/status_cache.py` - No status checking
- ❌ `app/util/time.py` - No refresh timers
- ❌ `app/data/status.py` - No status classification needed
- ❌ Remove all status-related code from `app/main.py`
- ❌ Remove all filter UI from `app/main.py`
- ❌ Remove all cache freshness checks
- ❌ Remove all API calls from dashboard (only in cache script)

### Code to Remove from `app/main.py`
- `get_game_statuses()` function
- `filter_games_by_status()` function
- `get_game_data()` function (no longer needed - use cache)
- All date/board/game selector logic
- All cache freshness checking
- All plot generation logic (move to script)
- All market data fetching (move to script)

---

## Part 4: Implementation Steps

### Step 1: Create Cache Generation Script
1. Create `scripts/generate_cache.py`
2. Copy relevant functions from `app/main.py` and `app/util/plot_cache.py`
3. Hardcode date range: 11/1/25 - 11/5/25
4. Generate all plots and save to cache
5. Test: Run script, verify plots are generated

### Step 2: Simplify Dashboard
1. Completely rewrite `app/main.py` with ultra-simple logic
2. Remove all filter UI
3. Remove all status checking
4. Remove all API calls
5. Only load from cache
6. Test: Run dashboard, verify it loads cached plots

### Step 3: Clean Up
1. Remove unused functions from `app/main.py`
2. Delete or comment out unused imports
3. Update `.gitignore` if needed (plots should be committed)
4. Test end-to-end: Generate cache → Commit to git → Run dashboard

---

## Part 5: File Structure After Simplification

```
halftime_game/
├── scripts/
│   └── generate_cache.py          # NEW: One-time cache generation
├── app/
│   ├── main.py                    # REWRITE: Ultra simple dashboard
│   ├── plots/
│   │   └── tempo.py               # KEEP: Plot generation (used by script)
│   ├── data/                      # KEEP: Data loaders (used by script)
│   ├── tfs/                       # KEEP: TFS computation (used by script)
│   └── util/
│       └── plot_cache.py         # KEEP: Cache utilities (used by script)
├── cache/
│   └── plots/                     # All pre-rendered plots (committed to git)
│       ├── {game_id}_hidden.png
│       └── {game_id}_residuals.pkl
└── streamlit_app.py               # KEEP: Thin wrapper
```

---

## Part 6: User Workflow

### Initial Setup (One Time)
1. Run `python scripts/generate_cache.py`
2. Wait for all plots to generate
3. Commit cache to git: `git add cache/plots/ && git commit -m "Add cached plots"`
4. Push to git: `git push`

### Playing the Game
1. Open dashboard: `streamlit run streamlit_app.py`
2. Dashboard loads all cached plots instantly
3. View plot → Click Fast or Slow → See result → Next game
4. Score updates automatically

### Adding New Games (Future)
1. Update date range in `scripts/generate_cache.py`
2. Run script again
3. Commit new plots to git
4. Push

---

## Part 7: Key Simplifications Summary

| Feature | Before | After |
|---------|--------|-------|
| **Date Selection** | UI selector | Hardcoded in script |
| **Board Filter** | UI selector | None (all games) |
| **Game Selection** | UI selector | Sequential (one at a time) |
| **Status Checking** | Real-time API calls | None (all completed) |
| **Cache Freshness** | 24-hour check | None (user manages) |
| **Plot Generation** | On-demand in dashboard | Pre-generated in script |
| **API Calls** | Every dashboard load | Only in cache script |
| **Tabs** | Multiple tabs | Single view |
| **Refresh Logic** | Auto-refresh timer | None |
| **Market Data** | Fetched on load | Pre-fetched in script |

---

## Part 8: Performance Optimizations

### Why This Is Fast
1. **Zero API calls** in dashboard (all data pre-fetched)
2. **Pre-rendered plots** (PNG files load instantly)
3. **In-memory residual data** (loaded once on startup)
4. **No status checking** (no PBP loading)
5. **No plot generation** (all cached)
6. **Simple UI** (no complex filters or tabs)

### Expected Performance
- **Dashboard startup**: < 1 second (just scanning cache directory)
- **Plot display**: Instant (PNG file load)
- **Answer feedback**: Instant (in-memory calculation)
- **Next game transition**: Instant (just increment index)

---

## Part 9: Testing Checklist

### Cache Generation Script
- [ ] Script runs without errors
- [ ] Generates plots for all games 11/1/25-11/5/25
- [ ] Creates `{game_id}_hidden.png` files
- [ ] Creates `{game_id}_residuals.pkl` files
- [ ] Handles missing PBP data gracefully
- [ ] Handles missing market data gracefully

### Dashboard
- [ ] Loads all cached plots on startup
- [ ] Displays plots correctly
- [ ] Fast/Slow buttons work
- [ ] Correctness calculation is accurate
- [ ] Score tally updates correctly
- [ ] Auto-advances to next game
- [ ] Loops back to first game after last
- [ ] Handles missing plots gracefully
- [ ] No API calls during gameplay

### End-to-End
- [ ] Generate cache → Commit → Push → Open dashboard → Play game
- [ ] Score persists during session
- [ ] Can play through all games
- [ ] Performance is fast (no lag)

---

## Summary

This simplified plan separates concerns:
- **Cache generation** = One-time script (run locally)
- **Dashboard** = Ultra-simple UI (loads from cache)

The result is a **blazing fast** user experience with zero API calls during gameplay, pre-rendered plots, and a minimal UI focused solely on the game mechanics.

