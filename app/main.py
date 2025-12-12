"""Ultra-simple Halftime Game dashboard.

This dashboard loads pre-rendered plots from cache and lets users play the game.
All plots must be pre-generated using scripts/generate_cache.py.
"""
import streamlit as st
from pathlib import Path
import pickle
from PIL import Image


# Constants
CACHE_DIR = Path("cache/plots")


def get_all_cached_games() -> list:
    """Scan cache directory and return list of game_ids with cached plots.
    
    Returns:
        Sorted list of game ID strings
    """
    if not CACHE_DIR.exists():
        return []
    
    game_ids = set()
    for png_file in CACHE_DIR.glob("*.png"):
        # Skip residual data files
        if png_file.name.endswith('_residuals.png'):
            continue
        # Extract game_id from filename (format: {game_id}.png)
        game_id = png_file.stem
        game_ids.add(game_id)
    
    return sorted(list(game_ids))


def load_all_residual_data(game_ids: list) -> dict:
    """Load all residual data files into a dict.
    
    Args:
        game_ids: List of game ID strings
        
    Returns:
        Dictionary mapping game_id to residual_data dict
    """
    residuals = {}
    for game_id in game_ids:
        pkl_path = CACHE_DIR / f"{game_id}_residuals.pkl"
        if pkl_path.exists():
            try:
                with open(pkl_path, 'rb') as f:
                    residuals[game_id] = pickle.load(f)
            except Exception as e:
                print(f"Error loading residual data for {game_id}: {e}")
    
    return residuals


def init_session_state():
    """Initialize all session state variables."""
    if 'game_ids' not in st.session_state:
        st.session_state.game_ids = get_all_cached_games()
    
    if 'residual_data' not in st.session_state:
        st.session_state.residual_data = load_all_residual_data(st.session_state.game_ids)
    
    # Preload all images into memory for instant display
    if 'cached_images' not in st.session_state:
        st.session_state.cached_images = {}
        for game_id in st.session_state.game_ids:
            plot_path = CACHE_DIR / f"{game_id}.png"
            if plot_path.exists():
                try:
                    st.session_state.cached_images[game_id] = Image.open(plot_path)
                except Exception as e:
                    print(f"Error loading image for {game_id}: {e}")
    
    if 'current_game_index' not in st.session_state:
        st.session_state.current_game_index = 0
    
    if 'score_tally' not in st.session_state:
        st.session_state.score_tally = {'correct': 0, 'total': 0}
    
    if 'game_states' not in st.session_state:
        st.session_state.game_states = {}


def get_game_state(game_id: str) -> dict:
    """Get or create game state for a game.
    
    Args:
        game_id: Game identifier
        
    Returns:
        Game state dictionary
    """
    if game_id not in st.session_state.game_states:
        st.session_state.game_states[game_id] = {
            'prediction_made': False,
            'user_prediction': None,  # "fast" or "slow"
            'correctness': None  # True/False/None
        }
    return st.session_state.game_states[game_id]


def calculate_correctness(user_prediction: str, residual_data: dict) -> tuple:
    """Calculate if user prediction was correct.
    
    Args:
        user_prediction: "fast" or "slow"
        residual_data: Residual data dictionary
        
    Returns:
        Tuple of (is_correct: bool, actual_result: str)
    """
    median_residual_p2 = residual_data.get('median_residual_p2', 0)
    # median_residual_p2 > 0 means Period 2 was SLOWER than expected
    # median_residual_p2 < 0 means Period 2 was FASTER than expected
    actual_result = "slow" if median_residual_p2 > 0 else "fast"
    is_correct = (user_prediction == actual_result)
    return is_correct, actual_result


def render():
    """Main render function - ultra simple."""
    st.set_page_config(
        page_title="Halftime Game",
        layout="centered",
        page_icon="🏀"
    )
    
    st.title("Halftime Game 🏀")
    st.caption("Predict if Period 2 will be faster or slower than expected")
    st.markdown("---")
    
    # Initialize session state
    init_session_state()
    
    game_ids = st.session_state.game_ids
    if not game_ids:
        st.error("❌ No cached plots found. Please run `python scripts/generate_cache.py` first.")
        st.info("This will generate all plots for games 11/1/25-11/5/25 and save them to cache.")
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
    if score['total'] > 0:
        percentage = (score['correct'] / score['total']) * 100
        st.info(f"🎯 Score: {score['correct']} of {score['total']} correct ({percentage:.1f}%)")
    else:
        st.info("🎯 Score: 0 of 0 correct")
    
    # Display progress
    st.caption(f"Game {current_idx + 1} of {len(game_ids)}")
    
    # Load and display plot (use preloaded image)
    img = st.session_state.cached_images.get(current_game_id)
    if img:
        st.image(img, use_container_width=True)
    else:
        st.error(f"Plot not found for game {current_game_id}")
        return
    
    # Show prediction buttons if not made
    if not game_state['prediction_made']:
        st.markdown("### Make your prediction:")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("⚡ Fast", key=f"fast_{current_game_id}", use_container_width=True):
                game_state['user_prediction'] = "fast"
                game_state['prediction_made'] = True
                st.rerun()
        with col2:
            if st.button("🐌 Slow", key=f"slow_{current_game_id}", use_container_width=True):
                game_state['user_prediction'] = "slow"
                game_state['prediction_made'] = True
                st.rerun()
    else:
        # Prediction made - show result
        # Check if residual_data exists and has the required field
        if (game_state['correctness'] is None and 
            residual_data and 
            residual_data.get('median_residual_p2') is not None):
            # Calculate correctness (only once)
            is_correct, actual_result = calculate_correctness(
                game_state['user_prediction'],
                residual_data
            )
            game_state['correctness'] = is_correct
            
            # Update score (only once)
            st.session_state.score_tally['total'] += 1
            if is_correct:
                st.session_state.score_tally['correct'] += 1
            
            # Flash screen with color based on P2 result (faster = green, slower = red)
            median_residual_p2 = residual_data.get('median_residual_p2', 0)
            flash_color = "green" if median_residual_p2 < 0 else "red"  # < 0 = faster, > 0 = slower
            
            # Set flash state and timestamp
            game_state['flash_active'] = True
            game_state['flash_color'] = flash_color
            game_state['flash_timestamp'] = time.time()
            
            # Show flash overlay
            st.markdown(
                f'<div id="flash-overlay" style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: {flash_color}; opacity: 0.15; z-index: 9999; pointer-events: none;"></div>'
                f'<script>setTimeout(function(){{document.getElementById("flash-overlay").style.display="none";}}, 100);</script>',
                unsafe_allow_html=True
            )
            
            # Show result
            actual_result_display = "slower" if actual_result == "slow" else "faster"
            if is_correct:
                st.success(f"✅ Correct! 2H went {actual_result_display}")
            else:
                st.error(f"❌ Incorrect. 2H went {actual_result_display}")
            
            # Auto-advance to next game after a brief moment
            if current_idx < len(game_ids) - 1:
                st.session_state.current_game_index += 1
            else:
                st.session_state.current_game_index = 0  # Loop back to start
            st.rerun()
        elif game_state['prediction_made'] and residual_data and residual_data.get('median_residual_p2') is None:
            # Prediction made but no residual data available
            st.warning("⚠️ Cannot determine correctness - market data not available for this game")
            # Still advance to next game
            if current_idx < len(game_ids) - 1:
                st.session_state.current_game_index += 1
            else:
                st.session_state.current_game_index = 0
            st.rerun()
        else:
            # Already calculated - just show result (shouldn't happen due to auto-advance)
            if game_state['correctness'] is not None and residual_data and residual_data.get('median_residual_p2') is not None:
                median_residual_p2 = residual_data.get('median_residual_p2', 0)
                actual_result = "slower" if median_residual_p2 > 0 else "faster"
                if game_state['correctness']:
                    st.success(f"✅ Correct! 2H went {actual_result}")
                else:
                    st.error(f"❌ Incorrect. 2H went {actual_result}")


if __name__ == "__main__":
    render()
