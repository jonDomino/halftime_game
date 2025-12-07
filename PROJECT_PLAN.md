# PROJECT PLAN: Halftime Game Implementation

## Current State Analysis

### What's Already Implemented
1. ✅ **`show_period_2` parameter exists** in `app/plots/tempo.py::build_tempo_figure()` (line 191)
   - Already filters Period 2 data when `show_period_2=False`
   - Returns tuple of `(figure, residual_data)` where `residual_data` contains `median_residual_p2`

2. ✅ **Basic project structure** - All TFS computation, data loading, and plotting infrastructure exists

3. ✅ **Title updated** - `streamlit_app.py` and `app/main.py::render()` already show "Halftime Game 🏀"

### What's Missing/Broken
1. ❌ **`_render_content()` function is missing** - Called on line 499 but not defined
   - Code starting at line 361 appears to be orphaned and should be inside `_render_content()`
   - This code references undefined variables: `game_ids`, `selected_date`, `selected_boards`, `tabs`, `tab_games`

2. ❌ **Tab system still exists** - Need to remove tabs and show single view

3. ❌ **Game filtering** - Need to filter to only "Halftime" and "Second Half" games

4. ❌ **Game state management** - No session state for predictions, correctness tracking

5. ❌ **Prediction UI** - No Fast/Slow buttons

6. ❌ **Score tally** - No global score tracking

7. ❌ **Correctness calculation** - Not implemented

8. ❌ **Period 2 reveal logic** - `render_game()` doesn't use `show_period_2` parameter

---

## Implementation Steps

### STEP 1: Fix Missing `_render_content()` Function

**File**: `app/main.py`

**Action**: Create the `_render_content()` function by moving orphaned code (lines 361-477) into a proper function definition.

**Location**: Insert before `render()` function (around line 479)

**Implementation**:
```python
def _render_content():
    """Main content rendering function."""
    # Get user selections
    selected_date = date_selector()
    selected_boards = board_filter()
    
    # Load schedule
    sched = load_schedule(selected_date)
    if sched is None or sched.empty:
        render_warning(f"No schedule available for {selected_date}")
        return
    
    # Get all games for selected date (auto-select all for status filtering)
    game_ids = game_selector(sched, selected_date, auto_select_all=True)
    
    if not game_ids:
        render_warning(f"No games selected or available for {selected_date}")
        return
    
    # Get statuses for all games (cached)
    with st.spinner("Loading game statuses..."):
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
    
    # Fetch closing totals for filtered games (cached, runs once)
    closing_totals_raw = {}
    if filtered_game_ids:
        try:
            closing_totals_raw = get_closing_totals(filtered_game_ids)
        except Exception as e:
            import traceback
            print(f"ERROR: get_closing_totals failed: {e}")
            print(traceback.format_exc())
            closing_totals_raw = {}
    
    # Filter by board and build closing_totals dict and other market data
    closing_totals = {}
    rotation_numbers = {}
    lookahead_2h_totals = {}
    closing_spread_home = {}
    home_team_names = {}
    opening_2h_totals = {}
    closing_2h_totals = {}
    opening_2h_spreads = {}
    closing_2h_spreads = {}
    
    if closing_totals_raw:
        for gid in filtered_game_ids:
            if gid in closing_totals_raw:
                try:
                    closing_total, board, rotation_number, closing_1h_total, lookahead_2h_total, spread_home, home_team_name, opening_2h_total, closing_2h_total, opening_2h_spread, closing_2h_spread = closing_totals_raw[gid]
                    closing_total = float(closing_total)
                    # Only include if board matches filter
                    if board in selected_boards:
                        closing_totals[gid] = closing_total
                        if rotation_number is not None:
                            rotation_numbers[gid] = rotation_number
                        if lookahead_2h_total is not None:
                            lookahead_2h_totals[gid] = float(lookahead_2h_total)
                        if spread_home is not None:
                            closing_spread_home[gid] = float(spread_home)
                        if home_team_name:
                            home_team_names[gid] = home_team_name
                        if opening_2h_total is not None:
                            opening_2h_totals[gid] = float(opening_2h_total)
                        if closing_2h_total is not None:
                            closing_2h_totals[gid] = float(closing_2h_total)
                        if opening_2h_spread is not None:
                            opening_2h_spreads[gid] = float(opening_2h_spread)
                        if closing_2h_spread is not None:
                            closing_2h_spreads[gid] = float(closing_2h_spread)
                except Exception as e:
                    print(f"ERROR unpacking data for game {gid}: {e}")
                    import traceback
                    print(traceback.format_exc())
    
    # Initialize plot containers
    if 'plot_containers' not in st.session_state:
        st.session_state.plot_containers = {}
    
    # REMOVE TABS - Render games directly in a single view
    # Render games in grid
    rows = create_game_grid(filtered_game_ids, cols_per_row=config.COLS_PER_ROW)
    
    for row_idx, row in enumerate(rows):
        columns = st.columns(len(row))
        for col_idx, gid in enumerate(row):
            with columns[col_idx]:
                # Create unique key for this game's container
                container_key = f"{selected_date}_{gid}_{row_idx}_{col_idx}"
                
                # Get or create empty container (persists across refreshes)
                if container_key not in st.session_state.plot_containers:
                    st.session_state.plot_containers[container_key] = st.empty()
                
                # Render directly into the container
                try:
                    with st.session_state.plot_containers[container_key]:
                        rotation_number = rotation_numbers.get(gid)
                        lookahead_2h = lookahead_2h_totals.get(gid)
                        spread_home = closing_spread_home.get(gid)
                        home_name = home_team_names.get(gid)
                        opening_2h_t = opening_2h_totals.get(gid)
                        closing_2h_t = closing_2h_totals.get(gid)
                        opening_2h_s = opening_2h_spreads.get(gid)
                        closing_2h_s = closing_2h_spreads.get(gid)
                        render_game(
                            gid, 
                            closing_totals=closing_totals, 
                            rotation_number=rotation_number,
                            lookahead_2h_total=lookahead_2h,
                            closing_spread_home=spread_home,
                            home_team_name=home_name,
                            opening_2h_total=opening_2h_t,
                            closing_2h_total=closing_2h_t,
                            opening_2h_spread=opening_2h_s,
                            closing_2h_spread=closing_2h_s
                        )
                except Exception as e:
                    # Log error but don't crash the whole dashboard
                    if 'error_log' not in st.session_state:
                        st.session_state.error_log = []
                    st.session_state.error_log.append(f"Game {gid} render error: {str(e)}")
                    with st.session_state.plot_containers[container_key]:
                        st.error(f"Error rendering game {gid}")
```

**Key Changes**:
- Remove all tab-related code (no `tabs`, `tab_games`, `status_filter()` usage)
- Filter games to only "Halftime" and "Second Half" before rendering
- Remove status-based grouping
- Render games directly in grid layout

---

### STEP 2: Initialize Game State Management

**File**: `app/main.py`

**Location**: Add helper function before `render_game()` (around line 286)

**Implementation**:
```python
def init_game_state(game_id: str) -> Dict:
    """Initialize game state if not exists.
    
    Args:
        game_id: Game identifier
        
    Returns:
        Game state dictionary
    """
    if 'game_states' not in st.session_state:
        st.session_state.game_states = {}
    if game_id not in st.session_state.game_states:
        st.session_state.game_states[game_id] = {
            'prediction_made': False,
            'user_prediction': None,  # "fast" or "slow" or None
            'period_2_revealed': False,
            'correctness': None  # True/False/None
        }
    return st.session_state.game_states[game_id]


def init_score_tally():
    """Initialize global score tally if not exists."""
    if 'score_tally' not in st.session_state:
        st.session_state.score_tally = {
            'correct': 0,
            'total': 0
        }
```

---

### STEP 3: Add Score Display Component

**File**: `app/main.py` (or create `app/ui/prediction.py`)

**Location**: Add function before `render_game()` or in new file

**Implementation**:
```python
def render_score_tally():
    """Display global score tally."""
    init_score_tally()
    score = st.session_state.score_tally
    st.info(f"🎯 Score: {score['correct']} of {score['total']} correct")
```

**Usage**: Call this in `_render_content()` before rendering games (after filters, before game grid)

---

### STEP 4: Add Prediction Buttons UI

**File**: `app/main.py`

**Location**: Inside `render_game()` function, after status badge (around line 332)

**Implementation**:
```python
# Inside render_game(), after render_badge() call:

# Initialize game state
game_state = init_game_state(game_id)

# Show prediction buttons only if prediction not made
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
```

---

### STEP 5: Update `render_game()` to Use `show_period_2` Parameter

**File**: `app/main.py`

**Location**: Inside `render_game()` function, modify `build_tempo_figure()` call (around line 345)

**Current Code** (line 345-357):
```python
fig = build_tempo_figure(
    tfs_df, 
    game_id, 
    show_predictions=False, 
    game_status=status,
    closing_total=closing_total,
    efg_first_half=efg_1h,
    efg_second_half=efg_2h,
    rotation_number=rotation_number,
    lookahead_2h_total=lookahead_2h,
    closing_spread_home=spread_home,
    home_team_name=home_name
)
render_chart(fig)
```

**New Code**:
```python
# Get game state to determine if Period 2 should be shown
game_state = init_game_state(game_id)
show_period_2 = game_state.get('prediction_made', False)

# Build figure with period filtering
fig, residual_data = build_tempo_figure(
    tfs_df, 
    game_id, 
    show_predictions=False, 
    game_status=status,
    closing_total=closing_total,
    efg_first_half=efg_1h,
    efg_second_half=efg_2h,
    rotation_number=rotation_number,
    lookahead_2h_total=lookahead_2h,
    closing_spread_home=spread_home,
    home_team_name=home_name,
    show_period_2=show_period_2  # NEW PARAMETER
)
render_chart(fig)

# Calculate and display correctness after Period 2 is revealed
if show_period_2 and residual_data and not game_state.get('period_2_revealed', False):
    game_state['period_2_revealed'] = True
    calculate_and_update_correctness(game_id, residual_data)
```

**Note**: `build_tempo_figure()` already returns `(figure, residual_data)` tuple, so unpack it.

---

### STEP 6: Add Correctness Calculation Function

**File**: `app/main.py`

**Location**: Add function before `render_game()` (around line 286)

**Implementation**:
```python
def calculate_and_update_correctness(game_id: str, residual_data: Dict):
    """Calculate if user's prediction was correct and update score tally.
    
    Args:
        game_id: Game identifier
        residual_data: Residual data dictionary from build_tempo_figure()
    """
    game_state = st.session_state.game_states.get(game_id, {})
    user_prediction = game_state.get('user_prediction')
    
    if user_prediction is None:
        return
    
    # Get Period 2 median residual
    median_residual_p2 = residual_data.get('median_residual_p2', 0)
    
    # Determine actual result
    # median_residual_p2 > 0 means Period 2 was SLOWER than expected
    # median_residual_p2 < 0 means Period 2 was FASTER than expected
    actual_result = "slow" if median_residual_p2 > 0 else "fast"
    
    # Compare to user prediction
    user_correct = (user_prediction == actual_result)
    
    # Update game state (only once)
    if game_state.get('correctness') is None:
        game_state['correctness'] = user_correct
        
        # Update global score tally
        init_score_tally()
        st.session_state.score_tally['total'] += 1
        if user_correct:
            st.session_state.score_tally['correct'] += 1
```

---

### STEP 7: Add Correctness Feedback Display

**File**: `app/main.py`

**Location**: Inside `render_game()` function, after plot is rendered (after `render_chart(fig)`)

**Implementation**:
```python
# Show correctness feedback after Period 2 is revealed
game_state = init_game_state(game_id)
if game_state.get('prediction_made', False) and game_state.get('period_2_revealed', False):
    correctness = game_state.get('correctness')
    if correctness is not None:
        # Get actual result for display
        if residual_data:
            median_residual_p2 = residual_data.get('median_residual_p2', 0)
            actual_result = "slower" if median_residual_p2 > 0 else "faster"
            
            if correctness:
                st.success(f"✅ Correct! Period 2 was {actual_result} than expected.")
            else:
                st.error(f"❌ Incorrect. Period 2 was {actual_result} than expected.")
```

**Note**: This code should be placed after the `render_chart(fig)` call and after correctness calculation.

---

### STEP 8: Remove Debug Error Message

**File**: `app/main.py`

**Location**: Inside `render()` function (line 495)

**Action**: Remove or comment out:
```python
st.error("🔴 IF YOU SEE THIS RED BOX, THE NEW CODE IS RUNNING!")
```

---

### STEP 9: Handle Edge Cases

**File**: `app/main.py`

**Location**: Inside `render_game()` function

**Add after getting game data** (around line 321):
```python
# Check if Period 2 data exists (for games at Halftime)
if status == "Halftime":
    # Check if Period 2 data exists in tfs_df
    if 'period_number' in tfs_df.columns:
        has_period_2 = (tfs_df['period_number'] == 2).any()
        if not has_period_2:
            # Game is at halftime but Period 2 hasn't started yet
            game_state = init_game_state(game_id)
            if game_state.get('prediction_made', False):
                st.info("⏳ Period 2 data not yet available. Your prediction will be evaluated once Period 2 starts.")
                # Don't show Period 2 even if prediction made
                show_period_2 = False
```

**Update**: Modify the `show_period_2` logic to account for this:
```python
game_state = init_game_state(game_id)
show_period_2 = game_state.get('prediction_made', False)

# Override if Period 2 data doesn't exist
if status == "Halftime" and 'period_number' in tfs_df.columns:
    has_period_2 = (tfs_df['period_number'] == 2).any()
    if not has_period_2:
        show_period_2 = False
```

---

### STEP 10: Remove Orphaned Code

**File**: `app/main.py`

**Location**: Lines 360-477

**Action**: Delete the orphaned code block that starts with:
```python


    
    if not game_ids:
```

This code should be replaced by the proper `_render_content()` function from STEP 1.

---

## Testing Checklist

After completing all steps, verify:

- [ ] `_render_content()` function exists and is properly defined
- [ ] No tab system - games render in single view
- [ ] Only "Halftime" and "Second Half" games are shown
- [ ] Score tally displays at top: "🎯 Score: X of Y correct"
- [ ] "Fast" and "Slow" buttons appear before prediction
- [ ] Buttons disappear after prediction is made
- [ ] Plot shows only Period 1 data initially
- [ ] Plot updates to show Period 2 after prediction
- [ ] Correctness feedback appears after Period 2 revealed
- [ ] Score tally updates correctly
- [ ] Edge case: Games at Halftime without Period 2 data show appropriate message
- [ ] All filters (date, board) still work
- [ ] All plot elements (kernel curve, expected lines, residuals table) still render
- [ ] Market data (Total, Lookahead, Spread, 2H data) still displays
- [ ] No errors in console/logs

---

## File Modification Summary

### Files to Modify:
1. **`app/main.py`** - Major changes:
   - Add `_render_content()` function (STEP 1)
   - Add `init_game_state()` helper (STEP 2)
   - Add `init_score_tally()` helper (STEP 2)
   - Add `render_score_tally()` function (STEP 3)
   - Add `calculate_and_update_correctness()` function (STEP 6)
   - Modify `render_game()` to:
     - Add prediction buttons (STEP 4)
     - Use `show_period_2` parameter (STEP 5)
     - Add correctness feedback (STEP 7)
     - Handle edge cases (STEP 9)
   - Remove orphaned code (STEP 10)
   - Remove debug error message (STEP 8)

### Files Already Correct:
- **`app/plots/tempo.py`** - Already has `show_period_2` parameter
- **`streamlit_app.py`** - No changes needed
- **`app/ui/selectors.py`** - No changes needed (status_filter can remain, just not used)

---

## Implementation Order

1. **STEP 1** - Fix `_render_content()` (critical, app won't run without it)
2. **STEP 2** - Add state management helpers
3. **STEP 3** - Add score display
4. **STEP 4** - Add prediction buttons
5. **STEP 5** - Update `render_game()` to use `show_period_2`
6. **STEP 6** - Add correctness calculation
7. **STEP 7** - Add correctness feedback
8. **STEP 8** - Remove debug message
9. **STEP 9** - Handle edge cases
10. **STEP 10** - Clean up orphaned code

---

## Key Implementation Notes for AI Agent

1. **`build_tempo_figure()` already returns tuple**: The function signature shows it returns `Tuple[plt.Figure, Optional[Dict]]`, so always unpack: `fig, residual_data = build_tempo_figure(...)`

2. **Session state structure**:
   - `st.session_state.game_states[game_id]` - Per-game state
   - `st.session_state.score_tally` - Global score tracking
   - `st.session_state.plot_containers` - Already exists, keep it

3. **Correctness logic**:
   - `median_residual_p2 > 0` → Period 2 was **slower** (positive residual = slower than expected)
   - `median_residual_p2 < 0` → Period 2 was **faster** (negative residual = faster than expected)
   - User predicts "fast" → correct if `median_residual_p2 < 0`
   - User predicts "slow" → correct if `median_residual_p2 > 0`

4. **Period 2 reveal timing**: Period 2 is revealed immediately after user makes prediction (`prediction_made = True` triggers `show_period_2 = True`)

5. **Correctness calculation timing**: Calculate correctness when Period 2 is first revealed (when `period_2_revealed` transitions from `False` to `True`)

6. **Score tally update**: Only update once per game (check `correctness is None` before updating)

---

## Expected Behavior Flow

1. User opens app → sees games at Halftime/Second Half
2. User sees Period 1 tempo plot for each game
3. User clicks "Fast" or "Slow" button
4. Plot immediately updates to show Period 1 + Period 2
5. System calculates correctness using `median_residual_p2`
6. Feedback message appears: "✅ Correct!" or "❌ Incorrect"
7. Score tally updates: "🎯 Score: X of Y correct"
8. Buttons disappear (prediction already made)

---

## Completion Criteria

The project is complete when:
- All 10 steps are implemented
- All items in testing checklist pass
- No errors in console/logs
- App runs without crashing
- User can make predictions and see results

