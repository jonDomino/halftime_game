# TFS Kernel Dashboard - Context for New Agent

## Project Overview

This is a **Streamlit dashboard** for real-time monitoring of **Time to First Shot (TFS)** tempo in college basketball games. The dashboard visualizes game tempo using kernel smoothing, shows expected TFS based on closing totals and possession start types, and provides real-time updates every 30 seconds.

## Current State (Latest Session)

### Recent Work Completed
1. ✅ **Possession-level Expected TFS**: Implemented dynamic expected TFS calculation based on `poss_start_type` (rebound, turnover, oppo_made_shot) with different formulas for each type
2. ✅ **Dual Expected TFS Lines**: Shows both game-level (flat dashed line) and possession-level (smooth trend line) expected TFS
3. ✅ **Shading Logic**: Red/green shading compares actual kernel curve vs possession-level expected kernel (not game-level)
4. ✅ **Residual Statistics Table**: Added dedicated data table below main tempo plot showing:
   - Overall average residual
   - Average residual by possession type (Rebound, Turnover, Made Shot)
   - Percentage of possessions above expected
   - Color-coded cells (green=faster than expected, pink=slower than expected)
5. ✅ **Git History Cleanup**: Removed credentials from git history using orphan branch approach
6. ✅ **Timezone Fix**: Converted all game dates to PST at pipeline entry to fix filtering issues
7. ✅ **Possession Start Legend**: Moved from individual plots to sidebar as single legend
8. ✅ **Code Review**: Created comprehensive `CODE_REVIEW.md` documenting requirements and refactoring recommendations

### Current Status

**✅ Git Push Issue RESOLVED**: Successfully removed credentials from git history by creating a clean orphan branch and force pushing. Repository now has clean history without any credentials.

**Status:**
- ✅ Fixed: Removed `STREAMLIT_SECRETS.md` from git tracking
- ✅ Fixed: Created clean git history (orphan branch approach)
- ✅ Fixed: Force pushed clean history to remote
- ✅ Fixed: GitHub push protection now passes
- ✅ Credentials stored in Streamlit Cloud settings (not in repo)

## Key Files & Their Purpose

### Core Application
- `streamlit_app.py` - Entry point (thin wrapper)
- `app/main.py` - Main application logic (502 lines - needs refactoring)
- `app/data/` - Data loading modules
  - `schedule_loader.py` - Loads schedule from ESPN
  - `pbp_loader.py` - Loads play-by-play data (cached)
  - `status.py` - Classifies game status from PBP
  - `bigquery_loader.py` - Fetches closing totals, calculates expected TFS
  - `efg.py` - Calculates effective field goal percentage
  - `get_sched.py` - ESPN API wrapper for schedule
  - `get_pbp.py` - ESPN API wrapper for PBP

### TFS Processing
- `app/tfs/preprocess.py` - Preprocessing pipeline
- `app/tfs/compute.py` - TFS computation
- `app/tfs/change_points.py` - CUSUM change-point detection
- `builders/action_time/` - Action time processing pipeline

### Visualization
- `app/plots/tempo.py` - Main tempo plot (440 lines - needs refactoring)
  - Shows kernel-smoothed tempo curve
  - Game-level expected TFS (dashed line)
  - Possession-level expected TFS (trend line)
  - Red/green shading (actual vs possession-level expected)
  - Residual statistics table (subplot below main plot)
    - Overall average residual
    - Average residual by possession type (Rebound, Turnover, Made Shot)
    - Percentage above expected

### UI Components
- `app/ui/selectors.py` - Date, game, board selectors
- `app/ui/renderer.py` - Chart/error rendering
- `app/ui/layout.py` - Grid layout

### Configuration
- `requirements.txt` - Dependencies
- `meatloaf.json` - BigQuery credentials (NOT in git)
- `.gitignore` - Excludes credentials

## Key Features & Requirements

### Expected TFS Formulas
- **Game-level**: `27.65 - 0.08 * closing_total` (reference line)
- **Possession-level**:
  - Oppo Made Shot: `36.4397 + (-0.1025 * closing_total)`
  - Rebound: `24.2977 + (-0.0692 * closing_total)`
  - Turnover: `23.9754 + (-0.0619 * closing_total)`
  - Period Start: Uses rebound formula

### Game Status Classification
- **Early 1H**: Period 1, >600 seconds remaining
- **First Half**: Period 1, 60-600 seconds remaining
- **Halftime**: Period 1, ≤60 seconds OR period 1 ended, period 2 not started
- **Second Half**: Period 2, clock running
- **Complete**: Period 2 ended or period > 2
- **Not Started**: No PBP data

### Caching Strategy
- Game statuses: 30 seconds TTL
- PBP data: 60 seconds TTL
- Closing totals: 1 hour TTL (only query 8am-10pm PST)

### Performance Optimizations
- Parallel status checking (ThreadPoolExecutor, max 5 workers)
- Skip completed games (never re-scan)
- Throttle "Not Started" games (10 min intervals)
- Flicker-free updates using `st.empty()` containers

## Technical Debt & Known Issues

1. **`app/main.py` too large** (502 lines) - needs splitting
2. **`app/plots/tempo.py` too complex** (366 lines) - needs refactoring
3. **Duplicate code** - Expected TFS calculation repeated
4. **Magic numbers** - Cache TTLs, time restrictions hardcoded
5. **Timezone** - Uses fixed UTC-8 offset (doesn't handle DST)
6. **No tests** - Zero test coverage

See `CODE_REVIEW.md` for detailed refactoring recommendations.

## Recent Git History

```
aae6160 - Add residual statistics chart below tempo plots showing avg residual overall and by possession type, plus % above expected
f1a42d3 - Remove temporary cleanup script
eba5796 - Initial commit: TFS Kernel Dashboard (credentials removed from history)
```

**Note**: Previous history was cleaned to remove credentials. Current branch starts from clean commit.

## Next Steps (Priority Order)

1. **HIGH**: Consider refactoring based on `CODE_REVIEW.md` (especially `app/main.py` and `app/plots/tempo.py`)
2. **MEDIUM**: Add proper timezone support (handle DST automatically)
3. **MEDIUM**: Extract configuration constants to centralized config module
4. **LOW**: Add tests, improve documentation

## Important Notes

- **Credentials**: Never commit `meatloaf.json` or actual credentials
- **Streamlit Cloud**: Uses secrets from `st.secrets.bq_credentials`
- **Timezone**: All dates converted to PST at pipeline entry
- **BigQuery**: Only queries 8am-10pm PST, uses 1-hour cache
- **Refresh**: Auto-refresh every 30 seconds, manual refresh available

## Code Structure

```
dashboard/
├── app/
│   ├── data/          # Data loading (schedule, PBP, BigQuery, status, eFG)
│   ├── tfs/           # TFS computation (preprocess, compute, change_points, segments)
│   ├── plots/         # Visualization (tempo, score_diff, combined)
│   ├── ui/            # UI components (selectors, renderer, layout)
│   ├── util/          # Utilities (cache, kernel, style, time)
│   └── main.py        # Main application (needs refactoring)
├── builders/          # Action time processing pipeline
├── streamlit_app.py   # Entry point
└── CODE_REVIEW.md     # Comprehensive code review & refactoring plan
```

## Key Dependencies

- `streamlit>=1.28.0`
- `pandas>=1.5.0`
- `numpy>=1.23.0`
- `matplotlib>=3.6.0`
- `requests>=2.28.0`
- `google-cloud-bigquery>=3.11.0`

## Contact Points for Questions

- **Expected TFS formulas**: `app/data/bigquery_loader.py::calculate_expected_tfs()`
- **Status classification**: `app/data/status.py::classify_game_status_pbp()`
- **Plot rendering**: `app/plots/tempo.py::build_tempo_figure()`
- **Main logic**: `app/main.py::_render_content()`

---

**Last Updated**: Current session
**Status**: Functional, clean git history, ready for refactoring to reduce technical debt

