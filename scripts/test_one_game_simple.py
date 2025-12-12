"""Simple test for one game"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

print("Starting test...", flush=True)

try:
    from app.util.plot_cache import generate_plot_for_game
    print("Imported generate_plot_for_game", flush=True)
    
    game_id = "401824809"
    print(f"Testing {game_id}...", flush=True)
    
    print("Calling generate_plot_for_game...", flush=True)
    fig, residual_data = generate_plot_for_game(game_id, closing_total=None)
    print(f"Returned: fig={fig is not None}, residual_data={residual_data is not None}", flush=True)
    
    if fig:
        from app.util.plot_cache import save_plot_to_cache
        print("Saving plot...", flush=True)
        save_plot_to_cache(fig, game_id)
        print(f"Saved plot for {game_id}", flush=True)
    else:
        print("ERROR: fig is None", flush=True)
        
except Exception as e:
    print(f"EXCEPTION: {e}", flush=True)
    import traceback
    traceback.print_exc()

