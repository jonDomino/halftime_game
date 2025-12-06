# Halftime Game - Project Specification & Implementation Guide

## Overview

This document explains how to fork the existing **TFS Kernel Dashboard** into a new project called **Halftime Game**. The new project will be a prediction game where users view Period 1 tempo data and predict whether Period 2 will play faster or slower than expectation.

---

## Part 1: Current Project Architecture

### 1.1 Project Structure

```
dashboard/
├── streamlit_app.py          # Entry point (thin wrapper)
├── app/
│   ├── main.py               # Main application logic (~636 lines)
│   ├── config.py             # Configuration constants
│   ├── data/                 # Data loading modules
│   │   ├── schedule_loader.py    # Loads schedule from ESPN
│   │   ├── pbp_loader.py         # Loads play-by-play (cached)
│   │   ├── status.py             # Classifies game status
│   │   ├── bigquery_loader.py    # Fetches market data, calculates expected TFS
│   │   ├── efg.py                # Calculates effective field goal %
│   │   ├── get_sched.py          # ESPN API wrapper for schedule
│   │   └── get_pbp.py            # ESPN API wrapper for PBP (paginated)
│   ├── tfs/                  # TFS computation
│   │   ├── preprocess.py         # Preprocessing pipeline
│   │   ├── compute.py            # TFS computation
│   │   ├── change_points.py     # CUSUM change-point detection
│   │   └── segments.py           # Segment line calculations
│   ├── plots/                # Visualization
│   │   └── tempo.py              # Main tempo plot (~1096 lines)
│   ├── ui/                   # UI components
│   │   ├── selectors.py          # Date, game, status, board selectors
│   │   ├── renderer.py           # Chart/error rendering helpers
│   │   └── layout.py             # Grid layout utilities
│   └── util/                 # Utilities
│       ├── cache.py               # Caching utilities
│       ├── kernel.py             # Kernel smoothing functions
│       ├── style.py              # Plot styling, colors
│       └── time.py               # Time utilities, refresh timer
├── build_tfs/               # Standalone TFS processing module
│   ├── get_pbp.py               # ESPN API with pagination (>500 plays)
│   ├── preprocess.py            # Preprocessing orchestrator
│   ├── compute.py               # TFS computation
│   ├── process_game.py          # Main entry point
│   └── builders/                # Action time processing pipeline
│       └── action_time/
└── requirements.txt          # Dependencies
```

### 1.2 Key Data Flow

1. **Schedule Loading** (`app/data/schedule_loader.py`)
   - Fetches schedule from ESPN API
   - Filters by date (PST timezone)
   - Returns DataFrame with game_ids

2. **Game Status Classification** (`app/data/status.py`)
   - Classifies games: Not Started, Early 1H, First Half, Halftime, Second Half, Complete
   - Uses play-by-play data to determine status
   - Cached for 30 seconds

3. **Play-by-Play Loading** (`app/data/pbp_loader.py`)
   - Loads PBP from ESPN API (with pagination support)
   - Cached for 60 seconds
   - Uses `build_tfs/get_pbp.py` for paginated API calls

4. **TFS Processing** (`app/tfs/preprocess.py` → `app/tfs/compute.py`)
   - Preprocesses PBP data (adds possession start types, action times)
   - Computes Time to First Shot (TFS) for each possession
   - Filters invalid possessions
   - Returns DataFrame with columns: `tfs`, `poss_start_type`, `period_number`, `away_score`, `home_score`, etc.

5. **Expected TFS Calculation** (`app/data/bigquery_loader.py::calculate_expected_tfs()`)
   - Period 1 formulas (by possession type):
     - Turnover: `TFS = 23.4283 + -0.068865 * closing_total`
     - Rebound: `TFS = 23.2206 + -0.070364 * closing_total`
     - Oppo Made Shot: `TFS = 35.8503 + -0.105015 * closing_total`
     - Oppo Made FT: `TFS = 28.1118 + -0.065201 * closing_total`
   - Period 2 formulas (include score_diff):
     - Turnover: `TFS = 22.0475 + -0.057148 * closing_total + -0.061952 * score_diff`
     - Rebound: `TFS = 24.2071 + -0.072452 * closing_total + -0.045162 * score_diff`
     - Oppo Made Shot: `TFS = 35.0632 + -0.097778 * closing_total + -0.034749 * score_diff`
     - Oppo Made FT: `TFS = 29.7614 + -0.073256 * closing_total + -0.030282 * score_diff`
   - `score_diff = abs(max(away_score) - max(home_score))` from Period 1

6. **Plot Rendering** (`app/plots/tempo.py::build_tempo_figure()`)
   - Takes TFS DataFrame, closing_total, and other parameters
   - Creates kernel-smoothed tempo curve
   - Shows expected TFS lines (game-level and possession-level)
   - Displays residual statistics table (P1, P2, Game stats)
   - Returns matplotlib Figure

7. **Main Rendering** (`app/main.py::_render_content()`)
   - Loads schedule, filters by date/status/board
   - Groups games by status into tabs
   - Renders each game using `render_game()` function
   - Uses `st.empty()` containers for flicker-free updates

### 1.3 Key Functions to Understand

#### `app/main.py::render_game()`
- **Purpose**: Renders a single game's visualization
- **Parameters**: `game_id`, `closing_totals`, `rotation_number`, market data (lookahead, spread, etc.)
- **Flow**:
  1. Calls `get_game_data()` to get TFS DataFrame and status
  2. Calculates `score_diff` from Period 1 data
  3. Calls `build_tempo_figure()` to create plot
  4. Displays plot using `st.pyplot()`

#### `app/plots/tempo.py::build_tempo_figure()`
- **Purpose**: Creates the main tempo visualization
- **Parameters**: `tfs_df`, `closing_total`, `score_diff`, `period_number`, market data, etc.
- **Returns**: matplotlib Figure
- **Key Logic**:
  - Filters TFS data by period if needed
  - Calculates expected TFS for each possession
  - Computes residuals (actual - expected)
  - Creates kernel-smoothed curve
  - Builds residual statistics table (P1, P2, Game columns)
  - Returns complete figure with plot + table

#### `app/data/bigquery_loader.py::calculate_expected_tfs()`
- **Purpose**: Calculates expected TFS for a single possession
- **Parameters**: `closing_total`, `poss_start_type`, `period_number`, `score_diff`
- **Returns**: Expected TFS value (float)
- **Logic**: Uses period-specific formulas based on possession type

### 1.4 Session State Structure

Current session state keys:
- `plot_containers`: Dict of `st.empty()` containers for each game
- `completed_games`: Set of completed game_ids (for caching)
- `error_log`: List of error messages
- `last_scan_time`: Dict mapping game_id to last scan timestamp

### 1.5 Possession Start Types

Four types (colors defined in `app/util/style.py`):
- `rebound` (#d62728 - red)
- `turnover` (#1f77b4 - blue)
- `oppo_made_shot` (#2ca02c - green)
- `oppo_made_ft` (#ff7f0e - orange)

**Note**: `period_start` was removed from visualizations.

---

## Part 2: Forking Instructions

### 2.1 Create New Directory

```bash
# Navigate to parent directory
cd C:\Users\jonDomino\Desktop\Projects\models\cbb_2025

# Copy entire dashboard directory
xcopy dashboard halftime_game /E /I /H /Y

# Navigate into new directory
cd halftime_game
```

### 2.2 Initialize New Git Repository

```bash
# Remove old git history
rmdir /S /Q .git

# Initialize new git repo
git init

# Create initial commit
git add .
git commit -m "Initial commit: forked from tfs-dashboard for halftime prediction game"
```

### 2.3 Update Project References

- Update `streamlit_app.py` title/header (if any)
- Update any README or documentation
- Consider updating `app/config.py` if project name is referenced

---

## Part 3: Halftime Game Requirements

### 3.1 Core Concept

**User Experience:**
1. User sees a game at halftime (Period 1 complete, Period 2 not started or just started)
2. Plot shows **only Period 1 data** (filtered TFS DataFrame)
3. User clicks "Fast" or "Slow" button to predict Period 2 tempo
4. After selection, plot updates to show **full game data** (Period 1 + Period 2)
5. System determines correctness by comparing Period 2 median residual to 0:
   - If `median_residual_p2 > 0` → Period 2 was **slower** than expected
   - If `median_residual_p2 < 0` → Period 2 was **faster** than expected
6. Score tally updates: "X of Y correct"

### 3.2 What to Keep

✅ **Keep All Filters**:
- Date selector
- Board filter (Main/Extra)
- Game selector (but only show halftime/in-progress games)

✅ **Keep All TFS Logic**:
- All preprocessing (`app/tfs/preprocess.py`)
- All TFS computation (`app/tfs/compute.py`)
- All expected TFS formulas (Period 1 and Period 2)
- All residual calculations

✅ **Keep All Plot Content and Formats**:
- Kernel-smoothed tempo curve
- Expected TFS lines
- Residual statistics table (P1, P2, Game columns)
- Scoreboard overlay
- Market data display (Total, Lookahead, Spread, 2H data)
- All styling and colors

### 3.3 What to Change

#### A. Remove Tab System
- **File**: `app/main.py`
- **Change**: Remove all tab logic, show only one view
- **Details**: 
  - Remove `status_filter()` function or modify to always return `["Halftime", "Second Half"]`
  - Remove tab creation loop
  - Render games directly in a single view

#### B. Filter Games to Halftime/In-Progress Only
- **File**: `app/main.py::_render_content()`
- **Change**: Only show games with status "Halftime" or "Second Half"
- **Logic**: Filter `game_ids` by status before rendering

#### C. Add Game State Management
- **File**: `app/main.py` (or new `app/data/state.py`)
- **New Session State Structure**:
  ```python
  if 'game_states' not in st.session_state:
      st.session_state.game_states = {}
  
  # For each game_id:
  st.session_state.game_states[game_id] = {
      'prediction_made': False,      # Has user made a prediction?
      'user_prediction': None,       # "fast" or "slow" or None
      'period_2_revealed': False,    # Has Period 2 been shown?
      'correctness': None            # True/False/None (None = not yet determined)
  }
  
  # Global score tracking:
  if 'score_tally' not in st.session_state:
      st.session_state.score_tally = {
          'correct': 0,
          'total': 0
      }
  ```

#### D. Modify Plot Function to Support Period Filtering
- **File**: `app/plots/tempo.py::build_tempo_figure()`
- **Change**: Add parameter `show_period_2: bool = False`
- **Logic**:
  ```python
  def build_tempo_figure(
      tfs_df: pd.DataFrame,
      closing_total: float,
      ...,
      show_period_2: bool = False,  # NEW PARAMETER
      ...
  ):
      # Filter TFS data if Period 2 should be hidden
      if not show_period_2:
          tfs_df = tfs_df[tfs_df['period_number'] == 1].copy()
      
      # Rest of function remains the same...
  ```

#### E. Add Prediction UI
- **File**: `app/main.py::render_game()` or new `app/ui/prediction.py`
- **Components**:
  1. **Prediction Buttons** (only show if `prediction_made == False`):
     ```python
     col1, col2 = st.columns(2)
     with col1:
         if st.button("⚡ Fast", key=f"fast_{game_id}"):
             st.session_state.game_states[game_id]['user_prediction'] = "fast"
             st.session_state.game_states[game_id]['prediction_made'] = True
             st.rerun()
     with col2:
         if st.button("🐌 Slow", key=f"slow_{game_id}"):
             st.session_state.game_states[game_id]['user_prediction'] = "slow"
             st.session_state.game_states[game_id]['prediction_made'] = True
             st.rerun()
     ```
  
  2. **Score Display** (always visible):
     ```python
     score = st.session_state.score_tally
     st.info(f"🎯 Score: {score['correct']} of {score['total']} correct")
     ```

#### F. Add Correctness Calculation
- **File**: `app/main.py::render_game()` or `app/plots/tempo.py`
- **Logic** (after Period 2 is revealed):
  ```python
  # Get Period 2 median residual from residual_data
  median_residual_p2 = residual_data.get('median_residual_p2', 0)
  
  # Determine actual result
  actual_result = "slow" if median_residual_p2 > 0 else "fast"
  
  # Compare to user prediction
  user_prediction = st.session_state.game_states[game_id]['user_prediction']
  user_correct = (user_prediction == actual_result)
  
  # Update game state
  if st.session_state.game_states[game_id]['correctness'] is None:
      st.session_state.game_states[game_id]['correctness'] = user_correct
      st.session_state.score_tally['total'] += 1
      if user_correct:
          st.session_state.score_tally['correct'] += 1
  ```

#### G. Update Plot Rendering Logic
- **File**: `app/main.py::render_game()`
- **Change**: Pass `show_period_2` parameter based on game state
  ```python
  game_state = st.session_state.game_states.get(game_id, {})
  show_period_2 = game_state.get('prediction_made', False)
  
  fig = build_tempo_figure(
      tfs_df=tfs_df,
      closing_total=closing_total,
      ...,
      show_period_2=show_period_2,  # NEW PARAMETER
      ...
  )
  ```

#### H. Add Correctness Feedback
- **File**: `app/main.py::render_game()`
- **Display**: After prediction is made and Period 2 revealed, show feedback
  ```python
  if game_state.get('prediction_made', False) and game_state.get('period_2_revealed', False):
      correctness = game_state.get('correctness')
      if correctness is True:
          st.success("✅ Correct! Period 2 was " + actual_result + ".")
      elif correctness is False:
          st.error("❌ Incorrect. Period 2 was " + actual_result + ".")
  ```

---

## Part 4: Implementation Details

### 4.1 Modified Function Signatures

#### `app/plots/tempo.py::build_tempo_figure()`
```python
def build_tempo_figure(
    tfs_df: pd.DataFrame,
    closing_total: float,
    score_diff: Optional[float] = None,
    rotation_number: Optional[int] = None,
    lookahead_2h_total: Optional[float] = None,
    closing_spread_home: Optional[float] = None,
    home_team_name: Optional[str] = None,
    opening_2h_total: Optional[float] = None,
    closing_2h_total: Optional[float] = None,
    opening_2h_spread: Optional[float] = None,
    closing_2h_spread: Optional[float] = None,
    show_period_2: bool = False,  # NEW PARAMETER
    ...
) -> plt.Figure:
```

#### `app/main.py::render_game()`
```python
def render_game(
    game_id: str,
    closing_totals: Dict[str, float] = None,
    rotation_number: Optional[int] = None,
    lookahead_2h_total: Optional[float] = None,
    closing_spread_home: Optional[float] = None,
    home_team_name: Optional[str] = None,
    opening_2h_total: Optional[float] = None,
    closing_2h_total: Optional[float] = None,
    opening_2h_spread: Optional[float] = None,
    closing_2h_spread: Optional[float] = None
):
    # NEW: Get game state
    if 'game_states' not in st.session_state:
        st.session_state.game_states = {}
    if game_id not in st.session_state.game_states:
        st.session_state.game_states[game_id] = {
            'prediction_made': False,
            'user_prediction': None,
            'period_2_revealed': False,
            'correctness': None
        }
    
    game_state = st.session_state.game_states[game_id]
    show_period_2 = game_state.get('prediction_made', False)
    
    # ... rest of function ...
    
    # NEW: Add prediction buttons (before plot)
    if not game_state.get('prediction_made', False):
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚡ Fast", key=f"fast_{game_id}"):
                game_state['user_prediction'] = "fast"
                game_state['prediction_made'] = True
                st.rerun()
        with col2:
            if st.button("🐌 Slow", key=f"slow_{game_id}"):
                game_state['user_prediction'] = "slow"
                game_state['prediction_made'] = True
                st.rerun()
    
    # ... render plot with show_period_2 parameter ...
    
    # NEW: Calculate correctness after Period 2 revealed
    if show_period_2 and not game_state.get('period_2_revealed', False):
        game_state['period_2_revealed'] = True
        # Calculate correctness (see section 3.3.F)
```

### 4.2 Residual Data Structure

The `build_tempo_figure()` function returns residual data in this structure:
```python
residual_data = {
    'total_poss_p1': int,
    'mean_residual_p1': float,
    'median_residual_p1': float,
    'total_poss_p2': int,
    'mean_residual_p2': float,
    'median_residual_p2': float,  # USE THIS FOR CORRECTNESS
    'total_poss': int,
    'mean_residual': float,
    'median_residual': float,
    # ... by-type data ...
}
```

**Key**: Use `median_residual_p2` to determine if Period 2 was fast or slow.

### 4.3 Game Filtering Logic

In `app/main.py::_render_content()`:
```python
# Get all games for selected date
game_ids = game_selector(sched, selected_date, auto_select_all=True)

# Get statuses
statuses = get_game_statuses(game_ids)

# FILTER: Only show Halftime or Second Half games
eligible_statuses = {"Halftime", "Second Half"}
filtered_game_ids = [
    gid for gid in game_ids
    if statuses.get(gid) in eligible_statuses
]

if not filtered_game_ids:
    render_warning("No halftime or in-progress games available.")
    return
```

### 4.4 Score Tally Persistence

**Option 1**: Session-only (resets on refresh)
- Store in `st.session_state.score_tally`
- Simple, but resets when user refreshes

**Option 2**: Persistent (using Streamlit's session state with persistence)
- Could use `st.session_state` with `persist=True` (if available)
- Or use a simple JSON file to persist across sessions

**Recommendation**: Start with Option 1 (session-only), add persistence later if needed.

---

## Part 5: Testing Checklist

After implementation, verify:

- [ ] Only Halftime/Second Half games are shown
- [ ] Period 1 data is visible initially
- [ ] "Fast" and "Slow" buttons appear before prediction
- [ ] Buttons disappear after prediction is made
- [ ] Plot updates to show Period 2 after prediction
- [ ] Correctness is calculated correctly (median_residual_p2 > 0 = slow, < 0 = fast)
- [ ] Score tally updates correctly
- [ ] Feedback message shows after Period 2 is revealed
- [ ] All filters (date, board) still work
- [ ] All plot elements (kernel curve, expected lines, residuals table) still render correctly
- [ ] Market data (Total, Lookahead, Spread, 2H data) still displays
- [ ] Scoreboard overlay still works

---

## Part 6: Key Files to Modify

### High Priority (Core Changes)
1. **`app/main.py`**
   - Remove tab system
   - Add game state management
   - Add prediction buttons
   - Add correctness calculation
   - Filter games to Halftime/Second Half only

2. **`app/plots/tempo.py`**
   - Add `show_period_2` parameter
   - Filter TFS DataFrame when `show_period_2=False`

### Medium Priority (UI Enhancements)
3. **`app/ui/prediction.py`** (new file, optional)
   - Extract prediction UI components
   - Extract score display component

4. **`streamlit_app.py`**
   - Update title/header if needed

### Low Priority (Polish)
5. **`app/config.py`**
   - Add any new configuration constants

---

## Part 7: Important Notes

### Period 2 Data Availability
- Games at "Halftime" may not have Period 2 data yet
- Games in "Second Half" will have Period 2 data
- Handle gracefully: if Period 2 data doesn't exist, show message "Period 2 data not yet available"

### Residual Calculation
- The residual statistics table already calculates Period 2 median residual
- Access it from the return value of `build_tempo_figure()` or from `residual_data` dict
- Ensure `build_tempo_figure()` returns residual data or stores it in a way that `render_game()` can access

### State Management
- Each game has its own state (prediction, correctness)
- Score tally is global (shared across all games)
- Use unique keys for buttons: `f"fast_{game_id}"`, `f"slow_{game_id}"`

### Performance
- Keep all existing caching (PBP, status, closing totals)
- Prediction state is in session state (fast, no API calls)
- No additional performance concerns

---

## Part 8: Example Code Snippets

### Initialize Game State
```python
def init_game_state(game_id: str):
    """Initialize game state if not exists."""
    if 'game_states' not in st.session_state:
        st.session_state.game_states = {}
    if game_id not in st.session_state.game_states:
        st.session_state.game_states[game_id] = {
            'prediction_made': False,
            'user_prediction': None,
            'period_2_revealed': False,
            'correctness': None
        }
    return st.session_state.game_states[game_id]
```

### Calculate Correctness
```python
def calculate_correctness(game_id: str, median_residual_p2: float) -> bool:
    """Calculate if user's prediction was correct."""
    game_state = st.session_state.game_states.get(game_id, {})
    user_prediction = game_state.get('user_prediction')
    
    if user_prediction is None:
        return None
    
    actual_result = "slow" if median_residual_p2 > 0 else "fast"
    return (user_prediction == actual_result)
```

### Update Score Tally
```python
def update_score_tally(game_id: str, is_correct: bool):
    """Update global score tally."""
    if 'score_tally' not in st.session_state:
        st.session_state.score_tally = {'correct': 0, 'total': 0}
    
    game_state = st.session_state.game_states.get(game_id, {})
    
    # Only update once per game
    if game_state.get('correctness') is None and is_correct is not None:
        game_state['correctness'] = is_correct
        st.session_state.score_tally['total'] += 1
        if is_correct:
            st.session_state.score_tally['correct'] += 1
```

---

## Summary

This document provides a complete guide for forking the TFS Kernel Dashboard into Halftime Game. The key changes are:

1. **Remove tabs** - Single view only
2. **Filter games** - Only Halftime/Second Half
3. **Add prediction UI** - Fast/Slow buttons
4. **Period filtering** - Hide Period 2 until prediction made
5. **Correctness calculation** - Compare prediction to median_residual_p2
6. **Score tracking** - Global tally of correct predictions

All existing TFS logic, filters, and plot formats remain unchanged. The new agent should be able to implement these changes systematically using this document as a guide.

