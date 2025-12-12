"""Tempo visualization plot"""
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Optional, Tuple, Dict
from app.tfs.change_points import find_change_points
from app.tfs.segments import get_segment_lines
from app.util.kernel import gaussian_kernel_smoother
from app.util.style import get_plot_style, get_color, get_poss_start_color

# Try to import scipy.stats, fallback to simple approximation if not available
try:
    from scipy import stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    # Simple approximation of normal CDF using error function
    import math
    def norm_cdf_approx(z):
        """Approximate normal CDF using error function."""
        return 0.5 * (1 + math.erf(z / math.sqrt(2)))


# Standard deviations by period and possession start type (estimated - should be updated with actual values)
# Format: {period: {poss_start_type: std_dev}}
STD_DEVS = {
    1: {  # Period 1
        "rebound": 8.5,
        "turnover": 8.5,
        "oppo_made_shot": 10.0,
        "oppo_made_ft": 9.0,
    },
    2: {  # Period 2
        "rebound": 8.5,
        "turnover": 8.5,
        "oppo_made_shot": 10.0,
        "oppo_made_ft": 9.0,
    }
}


def calculate_p_value(mean_residual: float, n: int, std_dev: float) -> float:
    """Calculate p-value for mean residual, formatted for display.
    
    Args:
        mean_residual: Mean residual (observed - expected)
        n: Sample size
        std_dev: Population standard deviation
        
    Returns:
        p-value (0-1): Formatted for display where:
        - Higher numbers (closer to 1) = likely slow (red shading when > 0.8)
        - Lower numbers (closer to 0) = likely fast (green shading when < 0.2)
        - For slow games (positive residual): returns 1 - P_slower
        - For fast games (negative residual): returns P_faster
    """
    if n == 0 or std_dev == 0:
        return 0.5  # Default to 50% if no data
    
    # Standard error of the mean
    se = std_dev / np.sqrt(n)
    
    # z-score (expected mean is 0)
    z = mean_residual / se
    
    # Calculate p-values based on direction
    if HAS_SCIPY:
        if mean_residual > 0:
            # Slow game: P_slower = P(Z > z), display 1 - P_slower (higher = more likely slow)
            p_slower = 1 - stats.norm.cdf(z)
            return 1 - p_slower
        else:
            # Fast game: P_faster = P(Z < z), display P_faster directly (lower = more likely fast)
            p_faster = stats.norm.cdf(z)
            return p_faster
    else:
        # Use approximation if scipy not available
        if mean_residual > 0:
            # Slow game
            p_slower = 1 - norm_cdf_approx(z)
            return 1 - p_slower
        else:
            # Fast game
            p_faster = norm_cdf_approx(z)
            return p_faster


def get_std_dev(period: int, poss_start_type: Optional[str], std_devs: Optional[Dict] = None) -> float:
    """Get standard deviation for given period and possession start type.
    
    Args:
        period: Period number (1 or 2)
        poss_start_type: Possession start type
        std_devs: Optional dictionary of std devs (defaults to STD_DEVS)
        
    Returns:
        Standard deviation
    """
    if std_devs is None:
        std_devs = STD_DEVS
    
    period_key = 1 if period == 1 else 2
    poss_type = str(poss_start_type).lower() if poss_start_type else "rebound"
    
    # Default to rebound if type not found
    return std_devs.get(period_key, {}).get(poss_type, std_devs.get(period_key, {}).get("rebound", 8.5))


def calculate_combined_p_value(residuals_by_type: Dict[str, list], period: int, std_devs: Optional[Dict] = None) -> float:
    """Calculate combined p-value for overall game considering all possession types.
    
    Args:
        residuals_by_type: Dictionary mapping poss_start_type to list of residuals
        period: Period number (1 or 2)
        std_devs: Optional dictionary of std devs
        
    Returns:
        Combined p-value
    """
    if std_devs is None:
        std_devs = STD_DEVS
    
    # Calculate weighted mean and combined variance
    total_residual = 0
    total_n = 0
    combined_variance = 0
    
    for poss_type, res_list in residuals_by_type.items():
        if not res_list:
            continue
        
        n = len(res_list)
        mean_res = np.mean(res_list)
        std_dev = get_std_dev(period, poss_type, std_devs)
        
        total_residual += mean_res * n
        total_n += n
        combined_variance += (std_dev ** 2) * n
    
    if total_n == 0:
        return 0.5
    
    # Weighted mean
    overall_mean = total_residual / total_n
    
    # Combined standard error (weighted average of variances)
    combined_std = np.sqrt(combined_variance / total_n)
    
    # Calculate p-value
    return calculate_p_value(overall_mean, total_n, combined_std)


def get_team_names(df: pd.DataFrame) -> Tuple[Optional[str], Optional[str]]:
    """Extract team names from DataFrame.
    
    Args:
        df: DataFrame with team information
        
    Returns:
        Tuple of (away_team, home_team)
    """
    def try_get(fields):
        for f in fields:
            if f in df.columns and pd.notna(df[f].iloc[0]):
                return str(df[f].iloc[0])
        return None
    
    away = try_get(["away_team_name", "away_team"])
    home = try_get(["home_team_name", "home_team"])
    
    return away, home


def build_tempo_figure(
    tfs_df: pd.DataFrame,
    game_id: str,
    show_predictions: bool = False,
    game_status: Optional[str] = None,
    expected_tfs: Optional[float] = None,
    closing_total: Optional[float] = None,
    efg_first_half: Optional[float] = None,
    efg_second_half: Optional[float] = None,
    rotation_number: Optional[int] = None,
    lookahead_2h_total: Optional[float] = None,
    closing_spread_home: Optional[float] = None,
    home_team_name: Optional[str] = None,
    opening_2h_total: Optional[float] = None,
    closing_2h_total: Optional[float] = None,
    opening_2h_spread: Optional[float] = None,
    closing_2h_spread: Optional[float] = None,
    show_period_2: bool = False,
    hide_period_2_overlay: bool = False
) -> Tuple[plt.Figure, Optional[Dict]]:
    """Build tempo visualization figure.
    
    Args:
        tfs_df: TFS DataFrame (full game data - Period 1 + Period 2)
        game_id: Game identifier
        show_predictions: Whether to show predicted TFS
        game_status: Game status string
        expected_tfs: Expected TFS value (deprecated, use closing_total instead)
        closing_total: Closing total for calculating possession-level expected TFS
        efg_first_half: First half eFG%
        efg_second_half: Second half eFG%
        rotation_number: Away team rotation number (optional)
        lookahead_2h_total: Lookahead 2H total (optional)
        closing_spread_home: Closing spread from home team's perspective (optional)
        home_team_name: Home team name (optional)
        opening_2h_total: Opening 2H total (optional)
        closing_2h_total: Closing 2H total (optional)
        opening_2h_spread: Opening 2H spread (optional)
        closing_2h_spread: Closing 2H spread (optional)
        show_period_2: Whether to show Period 2 data (default: False - only show Period 1)
        hide_period_2_overlay: DEPRECATED - no longer used (kept for compatibility)
        
    Returns:
        Tuple of (Matplotlib figure, residual_data dictionary or None)
        Note: residual_data includes full game stats (P1 + P2) even if plot shows only P1
    """
    # Store full dataframe for residual calculations (need P2 stats for correctness)
    full_tfs_df = tfs_df.copy()
    
    # Filter to Period 1 only for display
    if "period_number" in full_tfs_df.columns:
        display_tfs_df = full_tfs_df[full_tfs_df["period_number"] == 1].copy()
    else:
        display_tfs_df = full_tfs_df.copy()
    
    # Validate that we have Period 1 data
    if len(display_tfs_df) == 0:
        raise ValueError(f"No Period 1 data found for game {game_id}. Cannot generate plot.")
    
    # Remove team names - just show game ID
    header = f"Game {game_id}"
    
    # Add status to header if provided
    if game_status:
        header = f"{header} [{game_status}]"
    
    # Use Period 1 data only for plotting
    x = display_tfs_df["chrono_index"].values.astype(float)
    y = display_tfs_df["action_time"].values.astype(float)
    
    # Validate arrays are not empty
    if len(x) == 0 or len(y) == 0:
        raise ValueError(f"Empty Period 1 arrays for game {game_id}. x length: {len(x)}, y length: {len(y)}")
    
    # Create smooth grid (only for Period 1)
    if len(x) > 0:
        grid = np.linspace(x.min(), x.max(), 200)
        gx, gy = gaussian_kernel_smoother(x, y, bandwidth=5, grid=grid)
    else:
        grid = np.array([])
        gx = np.array([])
        gy = np.array([])
    
    # Find change points (only for Period 1)
    cps = find_change_points(y) if len(y) > 0 else []
    
    # Get segment lines (only for Period 1)
    segments = get_segment_lines(display_tfs_df)
    
    # Get style
    style = get_plot_style()
    
    # Calculate score_diff from Period 1 scores (if available)
    score_diff = None
    if "away_score" in full_tfs_df.columns and "home_score" in full_tfs_df.columns and "period_number" in full_tfs_df.columns:
        period_1_data = full_tfs_df[full_tfs_df["period_number"] == 1]
        if len(period_1_data) > 0:
            # Get max scores from period 1
            max_away_score = period_1_data["away_score"].max()
            max_home_score = period_1_data["home_score"].max()
            if pd.notna(max_away_score) and pd.notna(max_home_score):
                score_diff = abs(float(max_away_score) - float(max_home_score))
    
    # Calculate residuals early if we have closing_total (needed for subplot)
    # Use full dataframe for residual calculations (includes Period 1 + Period 2)
    # NOTE: If closing_total is None, we still return a figure but no residual_data
    # This allows plots to be generated even without market data
    residual_data: Optional[Dict] = None
    if closing_total is not None and len(full_tfs_df) > 0:
        try:
            from app.data.bigquery_loader import calculate_expected_tfs
            
            # Verify Period 2 data exists in full_tfs_df
            if "period_number" in full_tfs_df.columns:
                period_2_data = full_tfs_df[full_tfs_df["period_number"] >= 2]
                if len(period_2_data) == 0:
                    print(f"WARNING: No Period 2 data found in full_tfs_df for game {game_id}. Cannot calculate P2 residual stats.", file=sys.stderr, flush=True)
            
            # Calculate residuals for each possession, tracking by period and type
            residuals = []
            residuals_p1 = []
            residuals_p2 = []
            
            # Track by type and period
            residuals_by_type_p1 = {"rebound": [], "turnover": [], "oppo_made_shot": [], "oppo_made_ft": [], "other": []}
            residuals_by_type_p2 = {"rebound": [], "turnover": [], "oppo_made_shot": [], "oppo_made_ft": [], "other": []}
            
            above_exp_count_by_type_p1 = {"rebound": 0, "turnover": 0, "oppo_made_shot": 0, "oppo_made_ft": 0, "other": 0}
            above_exp_count_by_type_p2 = {"rebound": 0, "turnover": 0, "oppo_made_shot": 0, "oppo_made_ft": 0, "other": 0}
            total_count_by_type_p1 = {"rebound": 0, "turnover": 0, "oppo_made_shot": 0, "oppo_made_ft": 0, "other": 0}
            total_count_by_type_p2 = {"rebound": 0, "turnover": 0, "oppo_made_shot": 0, "oppo_made_ft": 0, "other": 0}
            
            above_exp_count = 0
            above_exp_count_p1 = 0
            above_exp_count_p2 = 0
            
            for idx in range(len(full_tfs_df)):
                actual_tfs = float(full_tfs_df.iloc[idx]["action_time"])
                poss_type = None
                period_num = None
                if "poss_start_type" in full_tfs_df.columns:
                    poss_type_val = full_tfs_df.iloc[idx]["poss_start_type"]
                    if pd.notna(poss_type_val) and poss_type_val is not None:
                        poss_type = str(poss_type_val).lower()
                if "period_number" in full_tfs_df.columns:
                    period_num_val = full_tfs_df.iloc[idx]["period_number"]
                    if pd.notna(period_num_val):
                        period_num = int(period_num_val)
                
                expected_tfs = calculate_expected_tfs(float(closing_total), poss_type, period_num, score_diff)
                residual = actual_tfs - expected_tfs
                residuals.append(residual)
                
                # Track by period
                if period_num == 1:
                    residuals_p1.append(residual)
                    if residual > 0:
                        above_exp_count_p1 += 1
                elif period_num and period_num >= 2:
                    residuals_p2.append(residual)
                    if residual > 0:
                        above_exp_count_p2 += 1
                
                # Track by type and period
                if poss_type in residuals_by_type_p1:
                    if period_num == 1:
                        residuals_by_type_p1[poss_type].append(residual)
                        total_count_by_type_p1[poss_type] += 1
                        if residual > 0:
                            above_exp_count_by_type_p1[poss_type] += 1
                    elif period_num and period_num >= 2:
                        residuals_by_type_p2[poss_type].append(residual)
                        total_count_by_type_p2[poss_type] += 1
                        if residual > 0:
                            above_exp_count_by_type_p2[poss_type] += 1
                else:
                    if period_num == 1:
                        residuals_by_type_p1["other"].append(residual)
                        total_count_by_type_p1["other"] += 1
                        if residual > 0:
                            above_exp_count_by_type_p1["other"] += 1
                    elif period_num and period_num >= 2:
                        residuals_by_type_p2["other"].append(residual)
                        total_count_by_type_p2["other"] += 1
                        if residual > 0:
                            above_exp_count_by_type_p2["other"] += 1
                
                # Count above/below (overall)
                if residual > 0:
                    above_exp_count += 1
            
            # Calculate overall statistics
            avg_residual = np.mean(residuals) if residuals else 0.0
            median_residual = np.median(residuals) if residuals else 0.0
            total_poss = len(residuals)
            pct_above = (above_exp_count / total_poss * 100) if total_poss > 0 else 0.0
            
            # Calculate Period 1 statistics
            avg_residual_p1 = np.mean(residuals_p1) if residuals_p1 else 0.0
            median_residual_p1 = np.median(residuals_p1) if residuals_p1 else 0.0
            total_poss_p1 = len(residuals_p1)
            pct_above_p1 = (above_exp_count_p1 / total_poss_p1 * 100) if total_poss_p1 > 0 else 0.0
            
            # Calculate Period 2 statistics
            # CRITICAL: median_residual_p2 is used to determine if user prediction was correct
            # median_residual_p2 > 0 means P2 was SLOWER than expected (user should predict "slow")
            # median_residual_p2 < 0 means P2 was FASTER than expected (user should predict "fast")
            avg_residual_p2 = np.mean(residuals_p2) if residuals_p2 else 0.0
            median_residual_p2 = np.median(residuals_p2) if residuals_p2 else 0.0
            total_poss_p2 = len(residuals_p2)
            pct_above_p2 = (above_exp_count_p2 / total_poss_p2 * 100) if total_poss_p2 > 0 else 0.0
            
            # Validate that we have Period 2 data for correctness calculation
            if total_poss_p2 == 0:
                print(f"WARNING: No Period 2 residual data calculated for game {game_id}. Cannot determine correctness.", file=sys.stderr, flush=True)
            
            # Calculate statistics by type for Period 1
            avg_by_type_p1 = {}
            median_by_type_p1 = {}
            pct_above_by_type_p1 = {}
            count_by_type_p1 = {}
            for poss_type, res_list in residuals_by_type_p1.items():
                if res_list:
                    avg_by_type_p1[poss_type] = np.mean(res_list)
                    median_by_type_p1[poss_type] = np.median(res_list)
                    pct_above_by_type_p1[poss_type] = (above_exp_count_by_type_p1[poss_type] / total_count_by_type_p1[poss_type] * 100) if total_count_by_type_p1[poss_type] > 0 else 0.0
                    count_by_type_p1[poss_type] = total_count_by_type_p1[poss_type]
            
            # Calculate statistics by type for Period 2
            avg_by_type_p2 = {}
            median_by_type_p2 = {}
            pct_above_by_type_p2 = {}
            count_by_type_p2 = {}
            for poss_type, res_list in residuals_by_type_p2.items():
                if res_list:
                    avg_by_type_p2[poss_type] = np.mean(res_list)
                    median_by_type_p2[poss_type] = np.median(res_list)
                    pct_above_by_type_p2[poss_type] = (above_exp_count_by_type_p2[poss_type] / total_count_by_type_p2[poss_type] * 100) if total_count_by_type_p2[poss_type] > 0 else 0.0
                    count_by_type_p2[poss_type] = total_count_by_type_p2[poss_type]
            
            # Calculate overall statistics by type (for backward compatibility)
            avg_by_type = {}
            median_by_type = {}
            pct_above_by_type = {}
            count_by_type = {}
            for poss_type in ["rebound", "turnover", "oppo_made_shot", "oppo_made_ft", "other"]:
                all_res = residuals_by_type_p1.get(poss_type, []) + residuals_by_type_p2.get(poss_type, [])
                if all_res:
                    avg_by_type[poss_type] = np.mean(all_res)
                    median_by_type[poss_type] = np.median(all_res)
                    total_count = total_count_by_type_p1.get(poss_type, 0) + total_count_by_type_p2.get(poss_type, 0)
                    above_count = above_exp_count_by_type_p1.get(poss_type, 0) + above_exp_count_by_type_p2.get(poss_type, 0)
                    pct_above_by_type[poss_type] = (above_count / total_count * 100) if total_count > 0 else 0.0
                    count_by_type[poss_type] = total_count
            
            # Calculate p-values
            # Overall p-values
            p_value_p1 = calculate_combined_p_value(residuals_by_type_p1, period=1) if residuals_p1 else 0.5
            p_value_p2 = calculate_combined_p_value(residuals_by_type_p2, period=2) if residuals_p2 else 0.5
            p_value_gm = calculate_combined_p_value(
                {k: residuals_by_type_p1.get(k, []) + residuals_by_type_p2.get(k, []) 
                 for k in ["rebound", "turnover", "oppo_made_shot", "oppo_made_ft", "other"]},
                period=1  # Use period 1 std devs as default for combined
            ) if residuals else 0.5
            
            # P-values by type for Period 1
            p_value_by_type_p1 = {}
            for poss_type, res_list in residuals_by_type_p1.items():
                if res_list:
                    std_dev = get_std_dev(1, poss_type)
                    p_value_by_type_p1[poss_type] = calculate_p_value(np.mean(res_list), len(res_list), std_dev)
            
            # P-values by type for Period 2
            p_value_by_type_p2 = {}
            for poss_type, res_list in residuals_by_type_p2.items():
                if res_list:
                    std_dev = get_std_dev(2, poss_type)
                    p_value_by_type_p2[poss_type] = calculate_p_value(np.mean(res_list), len(res_list), std_dev)
            
            # P-values by type overall (game)
            p_value_by_type = {}
            for poss_type in ["rebound", "turnover", "oppo_made_shot", "oppo_made_ft", "other"]:
                all_res = residuals_by_type_p1.get(poss_type, []) + residuals_by_type_p2.get(poss_type, [])
                if all_res:
                    # Use period 1 std dev as default for combined
                    std_dev = get_std_dev(1, poss_type)
                    p_value_by_type[poss_type] = calculate_p_value(np.mean(all_res), len(all_res), std_dev)
            
            residual_data = {
                # Overall (Game)
                "avg_residual": avg_residual,
                "median_residual": median_residual,
                "pct_above": pct_above,
                "total_poss": total_poss,
                "p_value": p_value_gm,
                # Period 1
                "avg_residual_p1": avg_residual_p1,
                "median_residual_p1": median_residual_p1,
                "pct_above_p1": pct_above_p1,
                "total_poss_p1": total_poss_p1,
                "p_value_p1": p_value_p1,
                # Period 2
                "avg_residual_p2": avg_residual_p2,
                "median_residual_p2": median_residual_p2,
                "pct_above_p2": pct_above_p2,
                "total_poss_p2": total_poss_p2,
                "p_value_p2": p_value_p2,
                # By type (overall)
                "avg_by_type": avg_by_type,
                "median_by_type": median_by_type,
                "pct_above_by_type": pct_above_by_type,
                "count_by_type": count_by_type,
                "p_value_by_type": p_value_by_type,
                # By type Period 1
                "avg_by_type_p1": avg_by_type_p1,
                "median_by_type_p1": median_by_type_p1,
                "pct_above_by_type_p1": pct_above_by_type_p1,
                "count_by_type_p1": count_by_type_p1,
                "p_value_by_type_p1": p_value_by_type_p1,
                # By type Period 2
                "avg_by_type_p2": avg_by_type_p2,
                "median_by_type_p2": median_by_type_p2,
                "pct_above_by_type_p2": pct_above_by_type_p2,
                "count_by_type_p2": count_by_type_p2,
                "p_value_by_type_p2": p_value_by_type_p2,
            }
        except Exception as e:
            # If calculation fails, skip residual chart
            import traceback
            print(f"Error calculating residual statistics: {e}")
            print(traceback.format_exc())
    
    # Create figure with subplots if we have residual data, otherwise single plot
    if residual_data:
        fig, axes = plt.subplots(2, 1, figsize=(style["figsize"][0], style["figsize"][1] * 1.3), 
                                 height_ratios=[3, 1], sharex=False)
        ax = axes[0]
        ax_residual = axes[1]
    else:
        fig, ax = plt.subplots(figsize=style["figsize"])
        ax_residual = None
    
    # Plot raw data with color-coding by poss_start_type
    if "poss_start_type" in full_tfs_df.columns:
        # Group by poss_start_type and plot each group with different color
        # Don't add labels to main legend - they'll be in separate legend
        poss_start_types = ["rebound", "turnover", "oppo_made_shot", "oppo_made_ft", None]
        
        for poss_type in poss_start_types:
            # Use display_tfs_df (Period 1 only) for mask to match x and y arrays
            mask = display_tfs_df["poss_start_type"] == poss_type
            if mask.any():
                ax.scatter(
                    x[mask],
                    y[mask],
                    alpha=style["alpha_scatter"],
                    s=style["scatter_size"],
                    color=get_poss_start_color(poss_type),
                    label=None  # No label in main legend
                )
    else:
        # Fallback if poss_start_type not available
        ax.scatter(
            x, y,
            alpha=style["alpha_scatter"],
            s=style["scatter_size"],
            label="Raw TFS"
        )
    
    # Plot smoothed line
    ax.plot(
        gx, gy,
        linewidth=style["linewidth"],
        label="Average Tempo (TFS)",
        color=get_color("primary")
    )
    
    # Add segment lines
    for seg_x, label, seg_style in segments:
        ax.axvline(x=seg_x, **seg_style)
    
    # Add change points
    for i, cp in enumerate(cps):
        if 0 <= cp < len(x):
            ax.axvline(
                x[cp],
                color=get_color("change_point"),
                linestyle=":",
                linewidth=2,
                alpha=0.9,
                label="Change Point" if i == 0 else None
            )
    
    # Add predictions if requested
    if show_predictions:
        from app.tfs.predict import predict_tfs_next
        pred, conf_hi, conf_lo = predict_tfs_next(tfs_df, n_ahead=12)
        pred_x = np.arange(len(x), len(x) + len(pred)) + 1
        
        ax.plot(pred_x, pred, '--', color=get_color("secondary"), linewidth=2, label="Predicted TFS")
        ax.fill_between(pred_x, conf_lo, conf_hi, alpha=0.2, color=get_color("secondary"))
    
    # Calculate game-level expected TFS (flat line for reference)
    game_level_exp_tfs = None
    if closing_total is not None:
        from app.data.bigquery_loader import calculate_expected_tfs
        # Calculate game-level expected TFS (no poss_start_type)
        game_level_exp_tfs = calculate_expected_tfs(float(closing_total), None)
        
        # Draw the game-level expected TFS line (solid, thin, dark gray, dashed)
        ax.axhline(
            y=game_level_exp_tfs,
            color="darkgray",
            linestyle="--",
            linewidth=1,
            alpha=0.6,
            label=f"Game-Level Expected TFS ({game_level_exp_tfs:.1f}s)"
        )
    
    # Calculate and plot possession-level expected TFS trend
    # Use Period 1 data only for display (matches x and y arrays)
    exp_gx, exp_gy = None, None
    if closing_total is not None and len(display_tfs_df) > 0:
        try:
            # Calculate expected TFS for each possession in Period 1 only
            # Make sure we iterate in the same order as display_tfs_df (which matches x and y)
            exp_tfs_values = []
            for idx in range(len(display_tfs_df)):
                poss_type = None
                period_num = 1  # Always Period 1 for display
                if "poss_start_type" in display_tfs_df.columns:
                    poss_type_val = display_tfs_df.iloc[idx]["poss_start_type"]
                    # Handle NaN/None values
                    if pd.notna(poss_type_val) and poss_type_val is not None:
                        poss_type = str(poss_type_val).lower()
                # Use Period 1 score_diff (calculated earlier)
                exp_tfs = calculate_expected_tfs(float(closing_total), poss_type, period_num, score_diff)
                exp_tfs_values.append(exp_tfs)
            
            exp_tfs_array = np.array(exp_tfs_values)
            
            # Smooth the expected TFS trend using the same kernel smoother
            # Use the same grid points as the kernel curve (Period 1 only)
            if len(exp_tfs_array) > 0 and len(x) > 0:
                exp_gx, exp_gy = gaussian_kernel_smoother(x, exp_tfs_array, bandwidth=5, grid=grid)
        except Exception as e:
            # If there's an error, fall back to old behavior
            import traceback
            print(f"Error calculating possession-level expected TFS: {e}")
            print(traceback.format_exc())
            exp_gx, exp_gy = None, None
    
    # Plot possession-level expected TFS trend and apply shading
    if exp_gx is not None and exp_gy is not None:
        # Plot the expected TFS trend line
        ax.plot(
            exp_gx, exp_gy,
            color="darkgray",
            linestyle="-",
            linewidth=1.5,
            alpha=0.8,
            label="Expected TFS (by Poss. Type)"
        )
        
        # Add colored shading based on kernel curve vs expected TFS trend
        # Red shading: area between exp_tfs trend and curve when curve > exp_tfs (tempo slower than expected)
        # Green shading: area between curve and exp_tfs trend when curve < exp_tfs (tempo faster than expected)
        
        # Use where parameter to only fill where condition is true (prevents connecting disconnected regions)
        # Red shading: where actual curve is above expected trend (slower tempo)
        above_mask = gy > exp_gy
        if above_mask.any():
            ax.fill_between(
                gx,
                exp_gy,  # lower bound (expected trend)
                gy,      # upper bound (actual curve)
                where=above_mask,  # only fill where condition is true
                color="red",
                alpha=0.15,
                interpolate=False,  # Don't interpolate across gaps
                label="Slower than Expected" if not (gy < exp_gy).any() else None
            )
        
        # Green shading: where actual curve is below expected trend (faster tempo)
        below_mask = gy < exp_gy
        if below_mask.any():
            ax.fill_between(
                gx,
                gy,      # lower bound (actual curve)
                exp_gy,  # upper bound (expected trend)
                where=below_mask,  # only fill where condition is true
                color="green",
                alpha=0.15,
                interpolate=False,  # Don't interpolate across gaps
                label="Faster than Expected" if not (gy > exp_gy).any() else None
            )
    
    # Fallback: if closing_total not available but expected_tfs is (for backward compatibility)
    elif expected_tfs is not None:
        # Draw the expected TFS line (solid, thin, dark gray)
        ax.axhline(
            y=expected_tfs,
            color="darkgray",
            linestyle="--",
            linewidth=1,
            alpha=0.6,
            label=f"Expected TFS ({expected_tfs:.1f}s)"
        )
    
    # Score overlay removed - don't show scores to game player
    
    # Add eFG% annotations if available
    efg_text = []
    if efg_first_half is not None:
        efg_text.append(f"1H eFG%: {efg_first_half:.1%}")
    if efg_second_half is not None:
        efg_text.append(f"2H eFG%: {efg_second_half:.1%}")
    
    if efg_text:
        # Add text box in upper left corner
        efg_str = " | ".join(efg_text)
        ax.text(
            0.02, 0.98, efg_str,
            transform=ax.transAxes,
            fontsize=10,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8),
            fontweight='bold'
        )
    
    # Build residual statistics text for display (if needed)
    residual_stats_text = None
    if residual_data:
        type_labels = {
            "rebound": "Reb",
            "turnover": "TO",
            "oppo_made_shot": "Made",
            "oppo_made_ft": "FT",
            "other": "Other"
        }
        
        stats_parts = [f"Avg Residual: {residual_data['avg_residual']:+.1f}s"]
        
        # Add by-type residuals
        type_parts = []
        for poss_type in ["rebound", "turnover", "oppo_made_shot", "oppo_made_ft"]:
            if poss_type in residual_data['avg_by_type']:
                type_parts.append(f"{type_labels[poss_type]}: {residual_data['avg_by_type'][poss_type]:+.1f}s")
        if type_parts:
            stats_parts.append(" | ".join(type_parts))
        
        # Add percentages
        pct_below = 100 - residual_data['pct_above']
        stats_parts.append(f"Above: {residual_data['pct_above']:.1f}% | Below: {pct_below:.1f}%")
        
        residual_stats_text = " | ".join(stats_parts)
    
    # Styling
    ax.set_title(f"{header}\nAverage Tempo (TFS)", fontsize=style["fontsize_title"])
    ax.set_xlabel("Possession")
    ax.set_ylabel("Time to First Shot (seconds)")
    
    # Create main legend (for lines, change points, etc.)
    ax.legend(loc="upper right", fontsize=style["fontsize_legend"])
    
    # Add residual statistics table below if we have residual data
    if ax_residual is not None and residual_data:
        # Prepare data for table with columns: Metric, P1 Count, P2 Count, Gm Count, P1 Mean, P2 Mean, Gm Mean, P1 Median, P2 Median, Gm Median, P1 % Slower, P2 % Slower, Gm % Slower
        type_labels_display = {
            "oppo_made_shot": "Made Shot",
            "oppo_made_ft": "Made FT",
            "rebound": "Rebound",
            "turnover": "Turnover"
        }
        
        # Build table data: rows are Overall, Made Shot, Made FT, Rebound, Turnover
        table_data = []
        
        # Helper function to format value or return "-" if not available
        def fmt_val(val, default="-"):
            if val is None or (isinstance(val, float) and np.isnan(val)):
                return default
            return val
        
        # Overall row - reordered: Metric, P1 (Cnt, Mean, Med, Slow%, P-val), P2 (Cnt, Mean, Med, Slow%, P-val), Gm (Cnt, Mean, Med, Slow%, P-val)
        table_data.append([
            "Overall",
            str(residual_data.get('total_poss_p1', 0)),
            f"{residual_data.get('avg_residual_p1', 0):+.1f}s" if residual_data.get('total_poss_p1', 0) > 0 else "-",
            f"{residual_data.get('median_residual_p1', 0):+.1f}s" if residual_data.get('total_poss_p1', 0) > 0 else "-",
            f"{residual_data.get('pct_above_p1', 0):.1f}%" if residual_data.get('total_poss_p1', 0) > 0 else "-",
            f"{residual_data.get('p_value_p1', 0.5)*100:.1f}%" if residual_data.get('total_poss_p1', 0) > 0 else "-",
            str(residual_data.get('total_poss_p2', 0)),
            f"{residual_data.get('avg_residual_p2', 0):+.1f}s" if residual_data.get('total_poss_p2', 0) > 0 else "-",
            f"{residual_data.get('median_residual_p2', 0):+.1f}s" if residual_data.get('total_poss_p2', 0) > 0 else "-",
            f"{residual_data.get('pct_above_p2', 0):.1f}%" if residual_data.get('total_poss_p2', 0) > 0 else "-",
            f"{residual_data.get('p_value_p2', 0.5)*100:.1f}%" if residual_data.get('total_poss_p2', 0) > 0 else "-",
            str(residual_data.get('total_poss', 0)),
            f"{residual_data.get('avg_residual', 0):+.1f}s",
            f"{residual_data.get('median_residual', 0):+.1f}s",
            f"{residual_data.get('pct_above', 0):.1f}%",
            f"{residual_data.get('p_value', 0.5)*100:.1f}%"
        ])
        
        # Add possession type rows (Made Shot, Made FT, Rebound, Turnover)
        for poss_type in ["oppo_made_shot", "oppo_made_ft", "rebound", "turnover"]:
            count_p1 = residual_data['count_by_type_p1'].get(poss_type, 0)
            count_p2 = residual_data['count_by_type_p2'].get(poss_type, 0)
            count_gm = residual_data['count_by_type'].get(poss_type, 0)
            
            if count_gm > 0:  # Only add row if there's data
                avg_p1 = residual_data['avg_by_type_p1'].get(poss_type, 0.0) if count_p1 > 0 else None
                avg_p2 = residual_data['avg_by_type_p2'].get(poss_type, 0.0) if count_p2 > 0 else None
                avg_gm = residual_data['avg_by_type'].get(poss_type, 0.0)
                
                median_p1 = residual_data['median_by_type_p1'].get(poss_type, 0.0) if count_p1 > 0 else None
                median_p2 = residual_data['median_by_type_p2'].get(poss_type, 0.0) if count_p2 > 0 else None
                median_gm = residual_data['median_by_type'].get(poss_type, 0.0)
                
                pct_p1 = residual_data['pct_above_by_type_p1'].get(poss_type, 0.0) if count_p1 > 0 else None
                pct_p2 = residual_data['pct_above_by_type_p2'].get(poss_type, 0.0) if count_p2 > 0 else None
                pct_gm = residual_data['pct_above_by_type'].get(poss_type, 0.0)
                
                p_val_p1 = residual_data.get('p_value_by_type_p1', {}).get(poss_type, 0.5) if count_p1 > 0 else None
                p_val_p2 = residual_data.get('p_value_by_type_p2', {}).get(poss_type, 0.5) if count_p2 > 0 else None
                p_val_gm = residual_data.get('p_value_by_type', {}).get(poss_type, 0.5)
                
                table_data.append([
                    type_labels_display[poss_type],
                    str(count_p1),
                    f"{avg_p1:+.1f}s" if avg_p1 is not None else "-",
                    f"{median_p1:+.1f}s" if median_p1 is not None else "-",
                    f"{pct_p1:.1f}%" if pct_p1 is not None else "-",
                    f"{p_val_p1*100:.1f}%" if p_val_p1 is not None else "-",
                    str(count_p2),
                    f"{avg_p2:+.1f}s" if avg_p2 is not None else "-",
                    f"{median_p2:+.1f}s" if median_p2 is not None else "-",
                    f"{pct_p2:.1f}%" if pct_p2 is not None else "-",
                    f"{p_val_p2*100:.1f}%" if p_val_p2 is not None else "-",
                    str(count_gm),
                    f"{avg_gm:+.1f}s",
                    f"{median_gm:+.1f}s",
                    f"{pct_gm:.1f}%",
                    f"{p_val_gm*100:.1f}%"
                ])
        
        # Create table with 16 columns - ordered: Metric, then all P1, then all P2, then all Gm
        col_labels = ["Metric", "P1 Cnt", "P1 Mean", "P1 Med", "P1 Slow%", "P1 P-val",
                     "P2 Cnt", "P2 Mean", "P2 Med", "P2 Slow%", "P2 P-val",
                     "Gm Cnt", "Gm Mean", "Gm Med", "Gm Slow%", "Gm P-val"]
        table = ax_residual.table(
            cellText=table_data,
            colLabels=col_labels,
            cellLoc='center',
            loc='center',
            bbox=[0, 0, 1, 1]
        )
        
        # Style the table
        table.auto_set_font_size(False)
        table.set_fontsize(7)  # Smaller font to fit more columns
        table.scale(1, 2)
        
        # Style header row (row 0 in matplotlib table)
        for j in range(len(col_labels)):
            table[(0, j)].set_facecolor('#4472C4')
            table[(0, j)].set_text_props(weight='bold', color='white')
        
        # Color code data cells
        for i, row in enumerate(table_data):
            row_idx = i + 1  # Data rows start at index 1 (after header)
            # Color code Mean columns (indices 2, 6, 10) - P1 Mean, P2 Mean, Gm Mean
            for col_idx in [2, 6, 10]:
                if col_idx < len(row) and row[col_idx] != "-":
                    try:
                        val = float(row[col_idx].replace("s", ""))
                        if val > 0:
                            table[(row_idx, col_idx)].set_facecolor('#ffcccc')  # Light red
                        else:
                            table[(row_idx, col_idx)].set_facecolor('#ccffcc')  # Light green
                    except:
                        pass
            
            # Color code Median columns (indices 3, 7, 11) - P1 Med, P2 Med, Gm Med
            for col_idx in [3, 7, 11]:
                if col_idx < len(row) and row[col_idx] != "-":
                    try:
                        val = float(row[col_idx].replace("s", ""))
                        if val > 0:
                            table[(row_idx, col_idx)].set_facecolor('#ffcccc')  # Light red
                        else:
                            table[(row_idx, col_idx)].set_facecolor('#ccffcc')  # Light green
                    except:
                        pass
            
            # Color code % Slower columns (indices 4, 8, 12) - P1 Slow%, P2 Slow%, Gm Slow%
            for col_idx in [4, 8, 12]:
                if col_idx < len(row) and row[col_idx] != "-":
                    try:
                        val = float(row[col_idx].replace("%", ""))
                        if val > 50:
                            table[(row_idx, col_idx)].set_facecolor('#ffcccc')  # Light red
                        else:
                            table[(row_idx, col_idx)].set_facecolor('#ccffcc')  # Light green
                    except:
                        pass
            
            # Column 0: Metric column (light gray)
            table[(row_idx, 0)].set_facecolor('#F0F0F0')
            
            # Color code P-value columns (indices 5, 10, 15) - P1 P-val, P2 P-val, Gm P-val
            # Higher numbers = likely slow (red), lower numbers = likely fast (green)
            for col_idx in [5, 10, 15]:
                if col_idx < len(row) and row[col_idx] != "-":
                    try:
                        p_val_text = row[col_idx]
                        if "%" in p_val_text:
                            p_val = float(p_val_text.replace("%", "")) / 100.0
                            if p_val > 0.8:
                                # High p-value = likely slow - red shading
                                table[(row_idx, col_idx)].set_facecolor('#FFE6E6')  # Light red
                            elif p_val < 0.2:
                                # Low p-value = likely fast - green shading
                                table[(row_idx, col_idx)].set_facecolor('#E6FFE6')  # Light green
                            else:
                                table[(row_idx, col_idx)].set_facecolor('white')
                        else:
                            table[(row_idx, col_idx)].set_facecolor('white')
                    except (ValueError, IndexError):
                        table[(row_idx, col_idx)].set_facecolor('white')
            
            # Count columns (1, 6, 11) - P1 Cnt, P2 Cnt, Gm Cnt - white background
            for col_idx in [1, 6, 11]:
                table[(row_idx, col_idx)].set_facecolor('#FFFFFF')
        
        # Remove axes for table
        ax_residual.axis('off')
        ax_residual.set_title(f'Residual Statistics', fontsize=10, fontweight='bold', pad=10)
        
        # Set x-axis label on main plot
        ax.set_xlabel("Possession", fontsize=10)
    
    # Add residual statistics text at the bottom of main plot (if no subplot)
    elif residual_stats_text:
        ax.text(
            0.5, -0.12, residual_stats_text,
            transform=ax.transAxes,
            fontsize=9,
            horizontalalignment='center',
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.7),
            family='monospace'
        )
        ax.set_xlabel("Possession")
    else:
        ax.set_xlabel("Possession")
    
    # Add rotation number text in top-left margin (outside plot area)
    if rotation_number is not None:
        fig.text(
            0.02, 0.98,  # Top-left corner in figure coordinates
            f"Roto: {rotation_number}",
            fontsize=9,
            color='#0a0a0a',  # Very dark, almost black
            horizontalalignment='left',
            verticalalignment='top',
            transform=fig.transFigure  # Use figure coordinates
        )
    
    # Add closing total, lookahead 2H total, and spread in top-right above plot
    y_pos = 0.98  # Start position at top-right
    line_height = 0.025  # Vertical spacing between lines
    
    if closing_total is not None:
        fig.text(
            0.98, y_pos,
            f"Total: {closing_total:.1f}",
            fontsize=9,
            color='#0a0a0a',
            horizontalalignment='right',
            verticalalignment='top',
            transform=fig.transFigure
        )
        y_pos -= line_height
    
    if lookahead_2h_total is not None:
        fig.text(
            0.98, y_pos,
            f"2H Looka: {lookahead_2h_total:.1f}",
            fontsize=9,
            color='#0a0a0a',
            horizontalalignment='right',
            verticalalignment='top',
            transform=fig.transFigure
        )
        y_pos -= line_height
    
    # Team name and spread removed from top right - don't show to game player
    
    # Add 2H Open/Close/Spread table immediately to the left of the Total/Looka/Spread text
    y_pos_2h = 0.98
    if opening_2h_total is not None or closing_2h_total is not None or closing_2h_spread is not None:
        if opening_2h_total is not None:
            open_str = f"{opening_2h_total:.1f}"
            if open_str.endswith('.0'):
                open_str = open_str[:-2]
            fig.text(
                0.75, y_pos_2h,
                f"2H Open: {open_str}",
                fontsize=9,
                color='#0a0a0a',
                horizontalalignment='right',
                verticalalignment='top',
                transform=fig.transFigure
            )
            y_pos_2h -= line_height
        
        if closing_2h_total is not None:
            close_str = f"{closing_2h_total:.1f}"
            if close_str.endswith('.0'):
                close_str = close_str[:-2]
            fig.text(
                0.75, y_pos_2h,
                f"2H Close: {close_str}",
                fontsize=9,
                color='#0a0a0a',
                horizontalalignment='right',
                verticalalignment='top',
                transform=fig.transFigure
            )
            y_pos_2h -= line_height
        
        if closing_2h_spread is not None:
            spread_2h_str = f"{closing_2h_spread:.1f}"
            if spread_2h_str.endswith('.0'):
                spread_2h_str = spread_2h_str[:-2]
            fig.text(
                0.75, y_pos_2h,
                f"2H Spread: {spread_2h_str}",
                fontsize=9,
                color='#0a0a0a',
                horizontalalignment='right',
                verticalalignment='top',
                transform=fig.transFigure
            )
    
    # No overlay needed - plot only shows Period 1 data
    
    fig.tight_layout()
    return fig, residual_data

