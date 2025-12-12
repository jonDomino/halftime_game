"""Test script to debug a single game"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("Script starting...", flush=True)

from app.util.plot_cache import generate_plot_for_game
from app.data.bigquery_loader import get_closing_totals

# Test with one of the games from 11/3/25
game_id = "401824809"  # First game from the list

print(f"Testing game {game_id}...", flush=True)

# Check if we have closing_total
print("Fetching market data...", flush=True)
closing_totals_raw = get_closing_totals([game_id])
print(f"Market data: {closing_totals_raw}", flush=True)

closing_total = None
if game_id in closing_totals_raw:
    closing_total = float(closing_totals_raw[game_id][0])
    print(f"closing_total = {closing_total}", flush=True)
else:
    print("WARNING: No closing_total found for this game", flush=True)

try:
    fig, residual_data = generate_plot_for_game(game_id, closing_total=closing_total)
    print(f"Result: fig={fig is not None}, residual_data={residual_data is not None}", flush=True)
    if fig is None:
        print("ERROR: fig is None", flush=True)
    if residual_data is None:
        print("ERROR: residual_data is None", flush=True)
except Exception as e:
    print(f"EXCEPTION: {e}", flush=True)
    import traceback
    traceback.print_exc()

