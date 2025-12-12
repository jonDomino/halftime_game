"""One-time cache generation script for Halftime Game.

This script fetches PBP data and generates all plots for specified dates.
Run this locally, then commit the cache to git.

Usage:
    python scripts/generate_cache.py
    
Note: Update TARGET_DATES in this file to match dates with available games.
The schedule loader fetches games from (today - 2 days) to (today + 3 days),
so dates must be within that range.
"""
import sys
from pathlib import Path
from datetime import date
import pandas as pd

# Ensure stderr is unbuffered
sys.stderr.reconfigure(line_buffering=True) if hasattr(sys.stderr, 'reconfigure') else None

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.data.bigquery_loader import get_closing_totals
from app.util.plot_cache import (
    generate_plot_for_game,
    save_plot_to_cache,
    save_residual_data_to_cache,
    ensure_cache_dir
)
import requests
from datetime import timezone, timedelta


# Date range: 11/1/25 - 11/5/25
TARGET_DATES = [
    date(2025, 11, 1),
    date(2025, 11, 2),
    date(2025, 11, 3),
    date(2025, 11, 4),
    date(2025, 11, 5),
]


def fetch_schedule_for_dates(target_dates: list) -> pd.DataFrame:
    """Fetch schedule data for specific dates from ESPN API.
    
    Args:
        target_dates: List of date objects
        
    Returns:
        DataFrame with schedule information
    """
    url = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard"
    rows = []
    
    pst = timezone(timedelta(hours=-8))
    
    for target_date in target_dates:
        datestr = target_date.strftime("%Y%m%d")
        params = {"dates": datestr, "groups": "50", "limit": "500"}
        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"Failed to fetch {datestr}: {e}")
            continue
        
        for e in data.get("events", []):
            game_id = e.get("id")
            game_date_time = e.get("date")
            
            # Convert game_date_time to PST and extract date
            if game_date_time:
                try:
                    dt_utc = pd.to_datetime(game_date_time, utc=True)
                    dt_pst = dt_utc.tz_convert(pst)
                    game_date = dt_pst.date()
                except Exception:
                    game_date = game_date_time.split("T")[0] if game_date_time else None
            else:
                game_date = None
            
            away_team = home_team = None
            away_team_id = home_team_id = None
            
            competitions = e.get("competitions", [])
            if competitions:
                comps = competitions[0].get("competitors", [])
                for comp in comps:
                    if comp.get("homeAway") == "away":
                        away_team = comp.get("team", {}).get("location")
                        away_team_id = comp.get("team", {}).get("id")
                    elif comp.get("homeAway") == "home":
                        home_team = comp.get("team", {}).get("location")
                        home_team_id = comp.get("team", {}).get("id")
            
            rows.append({
                "game_id": game_id,
                "game_date": game_date,
                "game_date_time": game_date_time,
                "away_team_id": away_team_id,
                "away_team": away_team,
                "home_team_id": home_team_id,
                "home_team": home_team,
            })
    
    return pd.DataFrame(rows)


def get_game_ids_for_dates(sched: pd.DataFrame, target_dates: list) -> list:
    """Get all game IDs for the target dates.
    
    Args:
        sched: Schedule DataFrame
        target_dates: List of date objects
        
    Returns:
        List of game ID strings
    """
    sched["game_date"] = pd.to_datetime(sched["game_date"], errors="coerce")
    sched["game_date_only"] = sched["game_date"].dt.date
    
    game_ids = []
    for target_date in target_dates:
        day_games = sched[sched["game_date_only"] == target_date]
        day_game_ids = day_games["game_id"].astype(str).tolist()
        game_ids.extend(day_game_ids)
        print(f"Found {len(day_game_ids)} games for {target_date}")
    
    return game_ids


def main():
    """Main cache generation function."""
    print("=" * 60)
    print("Halftime Game - Cache Generation Script")
    print("=" * 60)
    print(f"Target dates: {TARGET_DATES[0]} to {TARGET_DATES[-1]}")
    print()
    
    # Ensure cache directory exists
    ensure_cache_dir()
    
    # Step 1: Load schedule for target dates
    print("Step 1: Loading schedule for target dates...")
    sched = fetch_schedule_for_dates(TARGET_DATES)
    if sched is None or sched.empty:
        print("ERROR: No schedule data available for target dates")
        return
    
    # Step 2: Get game IDs for target dates
    print("Step 2: Finding games for target dates...")
    game_ids = get_game_ids_for_dates(sched, TARGET_DATES)
    
    if not game_ids:
        print("ERROR: No games found for target dates")
        print(f"Schedule has {len(sched)} total rows")
        if len(sched) > 0:
            print(f"Sample dates in schedule: {sched['game_date_only'].unique()[:10]}")
        return
    
    print(f"Found {len(game_ids)} total games")
    print(f"Game IDs: {game_ids[:10]}..." if len(game_ids) > 10 else f"Game IDs: {game_ids}")
    print()
    
    # Step 3: Fetch market data
    # NOTE: get_closing_totals has a 2-day date filter that won't work for historical dates
    # For now, we'll proceed without market data - plots can still be generated
    # but won't have residual calculations (which require closing_total)
    print("Step 3: Fetching market data...")
    print("WARNING: BigQuery query filters to last 2 days only.")
    print("For historical dates (11/1-11/5), market data may not be available.")
    print("Plots will be generated without residual calculations.")
    closing_totals_raw = {}
    try:
        # Try to fetch anyway - might work if data exists
        closing_totals_raw = get_closing_totals(game_ids)
        print(f"Fetched market data for {len(closing_totals_raw)} games")
        if len(closing_totals_raw) == 0:
            print("No market data found (expected for historical dates)")
    except Exception as e:
        print(f"WARNING: Failed to fetch market data: {e}")
        print("Continuing without market data...")
        closing_totals_raw = {}
    
    # Build market data dictionaries
    closing_totals = {}
    rotation_numbers = {}
    lookahead_2h_totals = {}
    closing_spread_home = {}
    home_team_names = {}
    opening_2h_totals = {}
    closing_2h_totals = {}
    opening_2h_spreads = {}
    closing_2h_spreads = {}
    
    for gid in game_ids:
        if gid in closing_totals_raw:
            try:
                (closing_total, board, rotation_number, closing_1h_total, 
                 lookahead_2h_total, spread_home, home_team_name, 
                 opening_2h_total, closing_2h_total, opening_2h_spread, 
                 closing_2h_spread) = closing_totals_raw[gid]
                
                closing_total = float(closing_total)
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
                print(f"WARNING: Error unpacking market data for game {gid}: {e}")
    
    print()
    
    # Step 4: Generate plots for each game
    print("Step 4: Generating plots...")
    print(f"Processing {len(game_ids)} games...")
    print()
    
    # Process all games (TEST_MODE disabled for full cache generation)
    TEST_MODE = False
    if TEST_MODE:
        print(f"TEST MODE: Processing only first 20 games (out of {len(game_ids)})")
        game_ids = game_ids[:20]
    
    successful = 0
    failed = 0
    
    for idx, game_id in enumerate(game_ids, 1):
        print(f"[{idx}/{len(game_ids)}] Processing game {game_id}...", end=" ", flush=True)
        
        try:
            # Generate plot (Period 1 only, but residual_data includes full game)
            fig, residual_data = generate_plot_for_game(
                game_id,
                closing_total=closing_totals.get(game_id),
                rotation_number=rotation_numbers.get(game_id),
                lookahead_2h_total=lookahead_2h_totals.get(game_id),
                closing_spread_home=closing_spread_home.get(game_id),
                home_team_name=home_team_names.get(game_id),
                opening_2h_total=opening_2h_totals.get(game_id),
                closing_2h_total=closing_2h_totals.get(game_id),
                opening_2h_spread=opening_2h_spreads.get(game_id),
                closing_2h_spread=closing_2h_spreads.get(game_id)
            )
            
            # Allow plots without residual_data (market data may be missing for historical dates)
            if fig is None:
                print("FAILED (no plot generated)", flush=True)
                failed += 1
                continue
            
            # Warn if residual_data is missing but don't fail
            if residual_data is None:
                print(f"WARNING: No residual data for {game_id} (likely missing closing_total)", flush=True)
            
            # Save plot (Period 1 only)
            save_plot_to_cache(fig, game_id)
            
            # Save residual data (or create dummy if None)
            if residual_data is not None:
                save_residual_data_to_cache(residual_data, game_id)
            else:
                # Create dummy residual data file so dashboard doesn't crash
                import pickle
                from pathlib import Path
                dummy_residual = {
                    "median_residual_p2": None,
                    "note": "No market data available - cannot calculate correctness"
                }
                residual_path = Path("cache/plots") / f"{game_id}_residuals.pkl"
                residual_path.parent.mkdir(parents=True, exist_ok=True)
                with open(residual_path, 'wb') as f:
                    pickle.dump(dummy_residual, f)
            
            print("SUCCESS", flush=True)
            successful += 1
            
        except Exception as e:
            print(f"FAILED: {e}", flush=True, file=sys.stderr)
            failed += 1
            import traceback
            print(traceback.format_exc(), file=sys.stderr, flush=True)
    
    print()
    print("=" * 60)
    print("Cache Generation Complete")
    print("=" * 60)
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total: {len(game_ids)}")
    print()
    print("Next steps:")
    print("1. Review the generated plots in cache/plots/")
    print("2. Commit to git: git add cache/plots/ && git commit -m 'Add cached plots'")
    print("3. Push to git: git push")
    print()


if __name__ == "__main__":
    main()

