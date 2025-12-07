"""Main Streamlit application entry point"""
import streamlit as st
from datetime import datetime, date, timedelta
from typing import List, Dict, Set, Tuple, Optional
# Removed: ThreadPoolExecutor, as_completed - no parallel scanning needed for completed games
from app.data.schedule_loader import load_schedule
from app.data.pbp_loader import load_pbp
from app.data.status import classify_game_status_pbp, GameStatus
from app.data.bigquery_loader import get_closing_totals
from app.data.efg import calculate_efg_by_half
from app.tfs.preprocess import preprocess_pbp
from app.tfs.compute import compute_tfs
from app.ui.selectors import date_selector, game_selector, status_filter, board_filter
from app.ui.renderer import render_chart, render_error, render_warning, render_info, render_badge
from app.ui.layout import render_game_grid, create_game_grid
from app.plots.tempo import build_tempo_figure
# Removed: setup_refresh_timer - no real-time polling needed for completed games
from app.util.plot_cache import (
    load_plot_from_cache, load_residual_data_from_cache,
    pregenerate_plots_for_games, is_cache_fresh, get_missing_plots,
    get_cache_metadata, save_cache_metadata
)
from app.config import config


# Removed: should_scan_game() and _scan_single_game() - no real-time scanning needed for completed games


@st.cache_data(ttl=3600)  # Cache status for 1 hour (completed games don't change)
def get_game_statuses(game_ids: List[str]) -> Dict[str, str]:
    """Get game statuses for a list of game IDs.
    
    Simplified for completed games only - no real-time polling needed.
    Status is cached since completed games don't change.
    
    Args:
        game_ids: List of game ID strings
        
    Returns:
        Dictionary mapping game_id to status
    """
    statuses = {}
    
    # Load PBP data and classify status (cached, no polling)
    for game_id in game_ids:
        try:
            raw_pbp = load_pbp(game_id)
            if raw_pbp is None or len(raw_pbp) == 0:
                statuses[game_id] = "Not Started"
            else:
                statuses[game_id] = classify_game_status_pbp(raw_pbp)
        except Exception as e:
            statuses[game_id] = "Not Started"
    
    return statuses


def filter_games_by_status(game_ids: List[str], selected_statuses: List[str]) -> List[str]:
    """Filter game IDs based on selected statuses.
    
    Args:
        game_ids: List of game ID strings
        selected_statuses: List of selected status filter strings
        
    Returns:
        Filtered list of game IDs
    """
    if not selected_statuses:
        return game_ids
    
    # Handle "Live Only" special case
    if "Live Only" in selected_statuses:
        # "Live Only" means First Half or Second Half
        if "First Half" not in selected_statuses:
            selected_statuses.append("First Half")
        if "Second Half" not in selected_statuses:
            selected_statuses.append("Second Half")
        # Remove "Live Only" from the list since we've expanded it
        selected_statuses = [s for s in selected_statuses if s != "Live Only"]
    
    # Get statuses for all games
    statuses = get_game_statuses(game_ids)
    
    # Filter games that match selected statuses
    filtered_ids = [
        game_id for game_id in game_ids
        if statuses.get(game_id, "Not Started") in selected_statuses
    ]
    
    return filtered_ids


def process_game(game_id: str):
    """Process a single game and return TFS DataFrame and raw PBP.
    
    Args:
        game_id: Game identifier
        
    Returns:
        Tuple of (TFS DataFrame, raw PBP DataFrame)
    """
    raw_pbp = load_pbp(game_id)
    df = preprocess_pbp(raw_pbp)
    tfs_df = compute_tfs(df)
    return tfs_df, raw_pbp


@st.cache_data(ttl=3600)  # Cache for 1 hour (completed games don't change)
def get_game_data(game_id: str):
    """Get processed game data with caching.
    
    Simplified for completed games only - no scanning/polling needed.
    Data is cached since completed games don't change.
    
    Args:
        game_id: Game identifier
        
    Returns:
        Tuple of (tfs_df, raw_pbp, status, efg_first_half, efg_second_half) or None if error
    """
    # Load and process game data (cached, no scanning needed for completed games)
    try:
        raw_pbp = load_pbp(game_id)
        if raw_pbp is None or len(raw_pbp) == 0:
            return None
        
        df = preprocess_pbp(raw_pbp)
        tfs_df = compute_tfs(df)
        status = classify_game_status_pbp(raw_pbp)
        
        # Calculate eFG% for both halves
        efg_1h, efg_2h = calculate_efg_by_half(raw_pbp)
        
        return tfs_df, raw_pbp, status, efg_1h, efg_2h
    except Exception as e:
        # Log error for debugging but don't crash the app
        import traceback
        if 'error_log' not in st.session_state:
            st.session_state.error_log = []
        st.session_state.error_log.append(f"Game {game_id}: {str(e)}")
        # Keep only last 10 errors
        if len(st.session_state.error_log) > 10:
            st.session_state.error_log = st.session_state.error_log[-10:]
        return None, None, None, None, None


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


def render_score_tally():
    """Display global score tally."""
    init_score_tally()
    score = st.session_state.score_tally
    st.info(f"🎯 Score: {score['correct']} of {score['total']} correct")


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
    """Render a single game's visualization.
    
    Args:
        game_id: Game identifier
        closing_totals: Dictionary mapping game_id to closing_total
        rotation_number: Away team rotation number (optional)
        lookahead_2h_total: Lookahead 2H total (optional)
        closing_spread_home: Closing spread from home team's perspective (optional)
        home_team_name: Home team name (optional)
        opening_2h_total: Opening 2H total (optional)
        closing_2h_total: Closing 2H total (optional)
        opening_2h_spread: Opening 2H spread (optional)
        closing_2h_spread: Closing 2H spread (optional)
    """
    st.markdown(f"**Game {game_id}**")
    
    # Get cached game data (this is fast due to caching)
    result = get_game_data(game_id)
    if result[0] is None:
        render_error(f"Error processing game {game_id}")
        return
    
    tfs_df, raw_pbp, status, efg_1h, efg_2h = result
    
    # Render status badge
    status_colors = {
        "Not Started": "gray",
        "Early 1H": "lightblue",
        "First Half": "blue",
        "Second Half": "green",
        "Halftime": "orange",
        "Complete": "red"
    }
    render_badge(status, status_colors.get(status, "blue"))
    
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
    
    # Get closing total for possession-level expected TFS calculation
    closing_total = None
    if closing_totals and game_id in closing_totals:
        closing_total = closing_totals[game_id]
    
    # Get lookahead 2H total and spread for this game
    lookahead_2h = lookahead_2h_total if lookahead_2h_total is not None else None
    spread_home = closing_spread_home if closing_spread_home is not None else None
    home_name = home_team_name if home_team_name is not None else None
    
    # Get game state to determine if Period 2 should be hidden with overlay
    game_state = init_game_state(game_id)
    prediction_made = game_state.get('prediction_made', False)
    
    # Check if Period 2 data exists
    has_period_2 = False
    if 'period_number' in tfs_df.columns:
        has_period_2 = (tfs_df['period_number'] == 2).any()
    
    # For completed games, Period 2 should always be available
    # This check is kept for safety but shouldn't trigger for completed games
    if not has_period_2:
        if prediction_made:
            st.warning("⚠️ Period 2 data not available for this completed game.")
    
    # Always render full plot, but hide Period 2 with overlay if prediction not made
    hide_overlay = not prediction_made and has_period_2
    
    # Try to load from cache first
    cached_plot_path = load_plot_from_cache(game_id, overlay_hidden=hide_overlay)
    residual_data = load_residual_data_from_cache(game_id)
    
    # If cached, display cached image (much faster)
    if cached_plot_path:
        from PIL import Image
        img = Image.open(cached_plot_path)
        st.image(img, use_container_width=True)
    else:
        # If not cached, generate on-the-fly (fallback)
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
            show_period_2=True,  # Always show Period 2 in data
            hide_period_2_overlay=hide_overlay  # Hide with overlay if prediction not made
        )
        render_chart(fig)
    
    # Calculate and display correctness after Period 2 is revealed (overlay removed)
    if prediction_made and has_period_2 and residual_data and not game_state.get('period_2_revealed', False):
        game_state['period_2_revealed'] = True
        calculate_and_update_correctness(game_id, residual_data)
    
    # Show correctness feedback after Period 2 is revealed
    if game_state.get('prediction_made', False) and game_state.get('period_2_revealed', False):
        correctness = game_state.get('correctness')
        if correctness is not None and residual_data:
            median_residual_p2 = residual_data.get('median_residual_p2', 0)
            actual_result = "slower" if median_residual_p2 > 0 else "faster"
            
            if correctness:
                st.success(f"✅ Correct! Period 2 was {actual_result} than expected.")
            else:
                st.error(f"❌ Incorrect. Period 2 was {actual_result} than expected.")


def _render_content():
    """Main content rendering function."""
    # Get user selections
    selected_date = date_selector()
    selected_boards = board_filter()
    
    # Load schedule
    sched = load_schedule()
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
    
    # FILTER: Only show Completed games (no real-time polling needed)
    eligible_statuses = {"Complete"}
    filtered_game_ids = [
        gid for gid in game_ids
        if statuses.get(gid) in eligible_statuses
    ]
    
    if not filtered_game_ids:
        render_warning("No completed games available.")
        return
    
    # Initialize current game index tracking
    if 'current_game_index' not in st.session_state:
        st.session_state.current_game_index = 0
    
    # Filter by board
    board_filtered_game_ids = []
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
                        board_filtered_game_ids.append(gid)
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
    
    if not board_filtered_game_ids:
        render_warning("No games available for selected board filter.")
        return
    
    # Check cache freshness and regenerate missing plots if needed
    # Use incremental mode to preserve historical plots
    if not is_cache_fresh():
        missing_plots = get_missing_plots(board_filtered_game_ids)
        if missing_plots:
            with st.spinner(f"🔄 Generating {len(missing_plots)} missing plots (preserving historical cache)..."):
                pregenerate_plots_for_games(
                    board_filtered_game_ids,
                    closing_totals,
                    rotation_numbers,
                    lookahead_2h_totals,
                    closing_spread_home,
                    home_team_names,
                    opening_2h_totals,
                    closing_2h_totals,
                    opening_2h_spreads,
                    closing_2h_spreads,
                    incremental=True,  # Only generate missing plots
                    dev_mode=True  # Auto-commit to git in dev mode
                )
            st.success(f"✅ Generated {len(missing_plots)} new plots! Historical cache preserved.")
            st.rerun()
        else:
            # All plots exist, just update metadata timestamp
            metadata = get_cache_metadata()
            metadata['last_update'] = datetime.now().isoformat()
            save_cache_metadata(metadata)
    
    # Ensure current_game_index is valid
    if st.session_state.current_game_index >= len(board_filtered_game_ids):
        st.session_state.current_game_index = 0
    
    # Display score tally
    render_score_tally()
    
    # Show progress indicator
    current_idx = st.session_state.current_game_index
    total_games = len(board_filtered_game_ids)
    st.info(f"Game {current_idx + 1} of {total_games}")
    
    # Get current game ID
    current_game_id = board_filtered_game_ids[current_idx]
    
    # Render only the current game
    try:
        rotation_number = rotation_numbers.get(current_game_id)
        lookahead_2h = lookahead_2h_totals.get(current_game_id)
        spread_home = closing_spread_home.get(current_game_id)
        home_name = home_team_names.get(current_game_id)
        opening_2h_t = opening_2h_totals.get(current_game_id)
        closing_2h_t = closing_2h_totals.get(current_game_id)
        opening_2h_s = opening_2h_spreads.get(current_game_id)
        closing_2h_s = closing_2h_spreads.get(current_game_id)
        
        render_game(
            current_game_id, 
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
        
        # Check if current game has prediction made and Period 2 revealed - if so, auto-advance to next
        game_state = init_game_state(current_game_id)
        if (game_state.get('prediction_made', False) and 
            game_state.get('period_2_revealed', False) and 
            current_idx < len(board_filtered_game_ids) - 1):
            # Move to next game immediately (user will see result on rerun)
            st.session_state.current_game_index += 1
            st.rerun()
    except Exception as e:
        # Log error but don't crash the whole dashboard
        if 'error_log' not in st.session_state:
            st.session_state.error_log = []
        st.session_state.error_log.append(f"Game {current_game_id} render error: {str(e)}")
        st.error(f"Error rendering game {current_game_id}")


def render():
    """Main render function - flicker-free pattern."""
    try:
        st.set_page_config(
            page_title="Halftime Game", 
            layout="wide",
            page_icon="🏀"  # Optional: add basketball emoji as icon
        )
    except Exception:
        # set_page_config can only be called once, ignore if already set
        pass
    
    # Always show title to prevent blank screen
    st.title("Halftime Game 🏀")
    st.caption("Version: Prediction Game Mode")
    st.markdown("---")
    
    try:
        _render_content()
    except Exception as e:
        # Catch any unhandled errors to prevent blank screen
        import traceback
        st.error("⚠️ An error occurred while rendering the dashboard")
        with st.expander("Error Details", expanded=True):
            st.exception(e)
            st.code(traceback.format_exc())
        
        # Show error log if available
        if 'error_log' in st.session_state and st.session_state.error_log:
            with st.expander("Recent Errors"):
                for err in st.session_state.error_log[-5:]:
                    st.text(err)
        
        # No refresh button needed - only showing completed games (no real-time updates)


if __name__ == "__main__":
    render()
    # No refresh timer needed - only showing completed games

