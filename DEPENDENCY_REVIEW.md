# Dependency Review for `run_game.py`

## Executive Summary

This document provides a thorough review of dependencies needed to run `python run_game.py` and identifies files that can be safely deleted for cleanup.

**Key Finding**: `run_game.py` is a lightweight Pygame-based game that loads pre-generated plot images from cache. It has minimal runtime dependencies but relies on a cache generation pipeline that requires more dependencies.

**⚠️ IMPORTANT: Streamlit is NO LONGER SUPPORTED** - All Streamlit-dependent files must be removed or refactored to remove Streamlit dependencies.

**Note on Caching Modules**: Keep all caching modules (e.g., `app/util/plot_cache.py`) even if not directly invoked by `run_game.py`, as their outputs (cached plots and residual data) are used by the game.

**Note on Analysis Scripts**: Keep `scripts/analyze_p2_stats.py` - it's the only analysis script needed (not directly supporting run_game, but required for the project).

---

## Part 1: What `run_game.py` Actually Does

### Entry Point
- **File**: `run_game.py` (6 lines)
- **Function**: Thin wrapper that calls `app.game_pygame.main()`

### Core Game Module
- **File**: `app/game_pygame.py` (339 lines)
- **Purpose**: Pygame-based desktop application for the Halftime Game
- **Key Functionality**:
  1. Scans `cache/plots/` directory for pre-generated PNG plot images
  2. Loads residual data from `cache/plots/{game_id}_residuals.pkl` files
  3. Displays plots in a Pygame window
  4. Handles user predictions (Fast/Slow) via keyboard or mouse
  5. Calculates correctness using `p_value_p2` from residual data
  6. Tracks score and advances through games

### Critical Dependency: Pre-Generated Cache

**The game REQUIRES pre-generated cache files:**
- `cache/plots/{game_id}.png` - Plot images (Period 1 only, showing tempo trends)
- `cache/plots/{game_id}_residuals.pkl` - Residual data (contains `p_value_p2` for correctness)

**Cache Generation**: Must run `scripts/generate_cache.py` BEFORE running the game.

---

## Part 2: Runtime Dependencies for `run_game.py`

### Direct Dependencies (Required to Run)

#### Python Standard Library
- `sys` - System operations, exit handling
- `pathlib.Path` - File path operations
- `pickle` - Loading residual data from `.pkl` files
- `time` - Time operations (imported but minimal use)
- `typing` - Type hints (Dict, Optional, Tuple)

#### Third-Party Packages (Runtime)
1. **pygame** (>=2.5.0)
   - Core game engine
   - Window management, event handling, image loading
   - Font rendering, surface operations
   - **Usage**: All game rendering and interaction

2. **Pillow (PIL)** (>=9.0.0)
   - Image loading fallback (if pygame can't load PNG)
   - **Usage**: `Image.open()` as fallback in `_preload_images()`
   - **Note**: Only used if pygame fails to load an image

3. **numpy** (implicit, via PIL fallback)
   - Only needed if PIL fallback is triggered
   - Used to convert PIL Image to pygame Surface
   - **Usage**: `np.array(pil_img)` → `pygame.surfarray.make_surface()`

### Minimal Runtime Requirements

**To run `run_game.py`, you only need:**
```python
# Core runtime dependencies
pygame>=2.5.0
Pillow>=9.0.0
numpy>=1.23.0  # Only if PIL fallback is used
```

**That's it!** The game is self-contained and only reads from cache.

---

## Part 3: Cache Generation Dependencies

### Why Cache Generation Matters

The game cannot run without pre-generated cache files. The cache generation script (`scripts/generate_cache.py`) requires a much larger dependency set.

### Cache Generation Pipeline

**Script**: `scripts/generate_cache.py`

**Process Flow**:
1. Fetches schedule from ESPN API
2. Fetches play-by-play (PBP) data from ESPN API
3. Fetches market data from BigQuery (closing totals, spreads)
4. Preprocesses PBP data (adds possession context, action times)
5. Computes Time to First Shot (TFS) for each possession
6. Generates tempo plots using matplotlib
7. Calculates residual statistics (Period 1, Period 2, Game-level)
8. Saves plots as PNG files
9. Saves residual data as pickle files

### Dependencies for Cache Generation

#### Data Fetching
- **requests** (>=2.28.0) - ESPN API calls
- **google-cloud-bigquery** (>=3.11.0) - Market data queries
- **pandas** (>=1.5.0) - Data manipulation

#### Data Processing
- **pandas** (>=1.5.0) - Core data processing
- **numpy** (>=1.23.0) - Numerical operations
- **build_tfs/** modules - TFS computation pipeline

#### Visualization
- **matplotlib** (>=3.6.0) - Plot generation
- **scipy** (optional) - Statistical functions (p-value calculation)
  - Has fallback if scipy not available

#### TFS Processing Pipeline (`build_tfs/`)
- **pandas** - Data processing
- **numpy** - Numerical operations
- **requests** - ESPN API calls

### Full Dependency List for Cache Generation

```python
# Data fetching
requests>=2.28.0
google-cloud-bigquery>=3.11.0

# Data processing
pandas>=1.5.0
numpy>=1.23.0

# Visualization
matplotlib>=3.6.0
scipy>=1.9.0  # Optional but recommended

# Runtime (for game)
pygame>=2.5.0
Pillow>=9.0.0
```

---

## Part 4: Module Dependency Analysis

### Modules Used by `run_game.py`

#### Direct Imports
- `app/game_pygame.py` - The game itself (self-contained)

#### Indirect Dependencies (via cache generation)
The game doesn't import these at runtime, but they're needed to generate cache:

**Data Loading**:
- `app/data/get_pbp.py` - ESPN PBP API wrapper
- `app/data/get_sched.py` - ESPN schedule API wrapper
- `app/data/bigquery_loader.py` - BigQuery market data (has optional Streamlit support, but works without it)
- ⚠️ **`app/data/pbp_loader.py`** - PBP loading with caching (**USES STREAMLIT - MUST BE REFACTORED**)
- `app/data/schedule_loader.py` - Schedule loading
- `app/data/status.py` - Game status classification
- `app/data/efg.py` - Effective field goal calculation

**TFS Processing**:
- `app/tfs/preprocess.py` - PBP preprocessing
- `app/tfs/compute.py` - TFS computation
- `app/tfs/change_points.py` - CUSUM change-point detection
- `app/tfs/segments.py` - Segment line calculations
- `app/tfs/predict.py` - Prediction utilities (if used)

**Visualization**:
- `app/plots/tempo.py` - Main tempo plot generation
- `app/plots/score_diff.py` - Score differential plots (if used)
- `app/plots/combined.py` - Combined plots (if used)

**Utilities**:
- ✅ `app/util/plot_cache.py` - **KEEP** - Cache management utilities (outputs used by run_game)
- `app/util/kernel.py` - Kernel smoothing functions
- `app/util/style.py` - Plot styling
- ❌ **`app/util/cache.py`** - **STREAMLIT-ONLY - MUST BE DELETED** (used by `pbp_loader.py` which needs refactoring)

**Note on Caching Modules**: Keep all caching modules (e.g., `app/util/plot_cache.py`) even if not directly invoked by `run_game.py`, as their outputs (cached plots and residual data files) are used by the game.

**Configuration**:
- `app/config.py` - Configuration constants

**Build TFS Pipeline**:
- `build_tfs/` - Entire directory needed for TFS computation

---

## Part 5: Files That Can Be Deleted

### ⚠️ CRITICAL: Streamlit Removal (NO LONGER SUPPORTED)

**Complete List of Streamlit-Dependent Files:**

| File | Status | Action Required |
|------|--------|-----------------|
| `streamlit_app.py` | Streamlit entry point | ❌ DELETE (if exists) |
| `streamlit_secrets.toml` | Streamlit config | ❌ DELETE |
| `run_dashboard.bat` | Streamlit launcher | ❌ DELETE |
| `run_dashboard.sh` | Streamlit launcher | ❌ DELETE |
| `app/util/cache.py` | Streamlit-only module | ❌ DELETE IMMEDIATELY |
| `app/ui/` directory | Streamlit UI components | ❌ DELETE (if exists) |
| `app/data/pbp_loader.py` | Uses `@st.cache_data` | ⚠️ REFACTOR (remove Streamlit) |
| `app/data/bigquery_loader.py` | Optional Streamlit support | ⚠️ OPTIONAL CLEANUP |
| `scripts/generate_cache.py` | Streamlit warning suppression | ⚠️ OPTIONAL CLEANUP |

**Impact Analysis:**
- `app/util/cache.py` is **Streamlit-only** and must be deleted
- `app/data/pbp_loader.py` **depends on** `app/util/cache.py` and must be refactored
- `app/data/bigquery_loader.py` has optional Streamlit but works without it (low priority)
- `scripts/generate_cache.py` suppresses Streamlit warnings but doesn't require it (low priority)

---

**All Streamlit-dependent files must be removed or refactored.**

#### Streamlit Application Files (DELETE IMMEDIATELY)
- ❌ **`streamlit_app.py`** - Streamlit entry point (if exists) - **DELETE**
- ❌ **`streamlit_secrets.toml`** - Streamlit secrets configuration - **DELETE**
- ❌ **`run_dashboard.bat`** - Batch script for Streamlit dashboard - **DELETE**
- ❌ **`run_dashboard.sh`** - Shell script for Streamlit dashboard - **DELETE**

#### Streamlit-Dependent Code Modules (MUST BE REFACTORED OR DELETED)
- ❌ **`app/util/cache.py`** - **STREAMLIT-ONLY MODULE - DELETE**
  - **Status**: Entire file is a Streamlit caching wrapper
  - **Impact**: Used by `app/data/pbp_loader.py` (which also needs refactoring)
  - **Action Required**: Delete this file and refactor `pbp_loader.py` to remove Streamlit dependency

- ⚠️ **`app/data/pbp_loader.py`** - **USES STREAMLIT - MUST BE REFACTORED**
  - **Status**: Uses `@st.cache_data` decorator from Streamlit
  - **Impact**: Required by `app/util/plot_cache.py` for cache generation
  - **Action Required**: Remove `@st.cache_data` decorator and Streamlit import. Implement simple in-memory caching or remove caching (cache generation script handles its own caching)
  - **Dependency**: Currently imports `app/util/cache.py` which must be deleted

#### Streamlit UI Components (DELETE IF EXISTS)
- ❌ **`app/ui/`** directory (if exists) - Streamlit UI components - **DELETE**
  - `selectors.py`, `renderer.py`, `layout.py` - Not needed for Pygame game

#### Files with Optional Streamlit Support (REVIEW - MAY NEED CLEANUP)
- ⚠️ **`app/data/bigquery_loader.py`** - Has optional Streamlit imports but works without Streamlit
  - **Status**: Uses try/except to handle missing Streamlit, falls back to file-based credentials
  - **Action Required**: Can keep as-is, but consider removing Streamlit code paths for cleaner code
  - **Impact**: Low priority - works without Streamlit

- ⚠️ **`scripts/generate_cache.py`** - Suppresses Streamlit warnings but doesn't require Streamlit
  - **Status**: Has code to suppress Streamlit logging warnings
  - **Action Required**: Can remove Streamlit warning suppression code after Streamlit is fully removed
  - **Impact**: Low priority - doesn't break anything

### Unused Scripts

#### Analysis/Testing Scripts
- ✅ **`scripts/analyze_p2_stats.py`** - **KEEP** - Analysis script for Period 2 statistics
  - **Status**: Only analysis script needed (not directly supporting run_game, but required for project)
  - **Purpose**: Analyzes Period 2 residual stats from cache
  - **Decision**: Keep - this is the only analysis script needed

- ❌ **`scripts/check_residuals.py`** - Residual checking (not needed for game)
- ❌ **`scripts/test_one_game_simple.py`** - Test script
- ❌ **`scripts/test_single_game.py`** - Test script

#### Cache Management Scripts (Optional - keep if useful)
- ⚠️ **`scripts/clean_old_cache.py`** - Cache cleanup utility
- ⚠️ **`scripts/commit_cache.py`** - Git commit utility
- ⚠️ **`scripts/wipe_cache.py`** - Cache deletion utility
  - **Decision**: Keep if you want cache management utilities, otherwise delete

### Documentation Files (Review and Keep/Delete)

**Note**: This section is now covered in detail above. See "Shell Scripts and Batch Files" and "Documentation Files (.md)" sections for complete analysis.

### Log Files (Delete)
- ❌ **`cache_build.log`** - Log file
- ❌ **`cache_run.log`** - Log file
- ❌ **`quick_test.log`** - Log file
- ❌ **`test_run.log`** - Log file
- ❌ **`debug_full.txt`** - Debug output
- ❌ **`debug_output.txt`** - Debug output

### Build Output Files (Review)
- ⚠️ **`build_tfs/outputs/`** - TFS processing outputs
  - **Decision**: Keep if needed for debugging, otherwise delete
  - Files like `401827508_simple.csv`, `401827508.csv` - Example outputs

### Configuration Files (Keep)
- ✅ **`requirements.txt`** - Python dependencies (update to reflect minimal runtime needs)
- ✅ **`meatloaf.json`** - BigQuery credentials (needed for cache generation)
- ✅ **`build_tfs/requirements.txt`** - Build dependencies
- ✅ **`app/config.py`** - Configuration constants

### Unused Plot Modules (Review)
- ⚠️ **`app/plots/combined.py`** - Combined plots (not used by game)
- ⚠️ **`app/plots/score_diff.py`** - Score differential plots (not used by game)
  - **Decision**: Keep if cache generation uses them, otherwise delete

### Shell Scripts and Batch Files (DELETE - Streamlit Only)

#### Batch Files (.bat)
- ❌ **`run_dashboard.bat`** - **DELETE** - Streamlit dashboard launcher script
  - **Content**: Runs `streamlit run streamlit_app.py` on network
  - **Status**: Not needed for Pygame game

#### Shell Scripts (.sh)
- ❌ **`run_dashboard.sh`** - **DELETE** - Streamlit dashboard launcher script
  - **Content**: Runs `streamlit run streamlit_app.py` on network
  - **Status**: Not needed for Pygame game

### Documentation Files (.md) - Aggressive Cleanup

**Principle**: Keep only documentation that directly supports `run_game.py` or cache generation. Delete all outdated planning docs, Streamlit-specific docs, and historical context.

#### DELETE - Outdated Planning/Implementation Docs
- ❌ **`PROJECT_PLAN.md`** - **DELETE** - Outdated implementation plan for Streamlit dashboard
  - **Content**: Step-by-step plan for implementing Halftime Game in Streamlit
  - **Status**: Project pivoted to Pygame, no longer relevant

- ❌ **`SIMPLIFIED_PROJECT_PLAN.md`** - **DELETE** - Outdated simplified plan for Streamlit dashboard
  - **Content**: Simplified plan for cache generation + Streamlit dashboard
  - **Status**: Project pivoted to Pygame, no longer relevant

- ❌ **`CODE_REVIEW.md`** - **DELETE** - Code review for Streamlit dashboard
  - **Content**: Comprehensive code review of TFS Kernel Dashboard (Streamlit app)
  - **Status**: Outdated, references Streamlit architecture

- ❌ **`CONTEXT.md`** - **DELETE** - Context documentation for Streamlit dashboard
  - **Content**: Project overview and current state for Streamlit dashboard
  - **Status**: Outdated, references Streamlit features and architecture

#### DELETE - Streamlit-Specific Setup/Hosting Docs
- ❌ **`SETUP_INSTRUCTIONS.md`** - **DELETE** - Git setup instructions for Streamlit dashboard
  - **Content**: Git initialization and Streamlit setup instructions
  - **Status**: Outdated, references Streamlit and old project structure

- ❌ **`HOSTING_INSTRUCTIONS.md`** - **DELETE** - Streamlit hosting guide
  - **Content**: Instructions for hosting Streamlit dashboard (local network, Streamlit Cloud, ngrok)
  - **Status**: Not needed for Pygame desktop app

#### REVIEW - May Have Useful Info (Delete if Outdated)
- ⚠️ **`SHARING_CREDENTIALS.md`** - **REVIEW/DELETE** - BigQuery credentials sharing guide
  - **Content**: How to share BigQuery credentials with colleagues
  - **Status**: References Streamlit but has useful BigQuery credential info
  - **Decision**: Delete if credentials are already set up, otherwise keep temporarily

- ⚠️ **`CACHE_SYSTEM.md`** - **REVIEW/DELETE** - Cache system documentation
  - **Content**: Documents plot cache system, references Streamlit dashboard
  - **Status**: Has useful cache info but references Streamlit features
  - **Decision**: Delete if cache system is self-explanatory, otherwise extract useful parts

- ⚠️ **`cache/plots/README.md`** - **REVIEW/DELETE** - Cache directory README
  - **Content**: Documents cache directory structure, references Streamlit dashboard
  - **Status**: Has cache structure info but references Streamlit
  - **Decision**: Delete if cache structure is obvious, otherwise keep minimal version

#### KEEP - Reference Documentation (Mark as Reference Only)
- ✅ **`HALFTIME_GAME_SPEC.md`** - **KEEP** - Original game specification
  - **Content**: Complete specification for Halftime Game (original requirements)
  - **Status**: Useful reference for understanding game requirements
  - **Note**: Mark as reference only, project has evolved

- ✅ **`build_tfs/README.md`** - **KEEP** - TFS processing module documentation
  - **Content**: Documentation for TFS processing pipeline
  - **Status**: Useful for understanding cache generation dependencies

- ✅ **`build_tfs/TFS_CONTEXT.md`** - **KEEP** - TFS technical context
  - **Content**: Technical specification of TFS computation
  - **Status**: Useful reference for understanding TFS pipeline

#### UPDATE REQUIRED
- ⚠️ **`README.md`** - **UPDATE** - Main project README
  - **Content**: Currently describes "TFS Kernel Dashboard" (Streamlit app)
  - **Status**: Must be updated to reflect Pygame game
  - **Action**: Rewrite to document `run_game.py` and cache generation

- ✅ **`DEPENDENCY_REVIEW.md`** - **KEEP** - This document
  - **Content**: Dependency analysis and cleanup guide
  - **Status**: Current cleanup documentation

---

## Part 6: Dependency Summary Tables

### Runtime Dependencies (for `run_game.py`)

| Package | Version | Purpose | Required? |
|---------|---------|---------|-----------|
| pygame | >=2.5.0 | Game engine, rendering | ✅ Yes |
| Pillow | >=9.0.0 | Image loading fallback | ✅ Yes |
| numpy | >=1.23.0 | PIL fallback conversion | ⚠️ Only if PIL fallback used |

### Cache Generation Dependencies

| Package | Version | Purpose | Required? |
|---------|---------|-----------|-----------|
| pandas | >=1.5.0 | Data processing | ✅ Yes |
| numpy | >=1.23.0 | Numerical operations | ✅ Yes |
| matplotlib | >=3.6.0 | Plot generation | ✅ Yes |
| requests | >=2.28.0 | ESPN API calls | ✅ Yes |
| google-cloud-bigquery | >=3.11.0 | Market data | ✅ Yes |
| scipy | >=1.9.0 | Statistical functions | ⚠️ Optional (has fallback) |

### Module Dependencies

#### Required for Game Runtime
- `app/game_pygame.py` - Game implementation
- `cache/plots/` - Pre-generated cache (must exist)

#### Required for Cache Generation
- `app/data/` - Data loading modules
- `app/tfs/` - TFS processing modules
- `app/plots/tempo.py` - Plot generation
- `app/util/plot_cache.py` - Cache utilities
- `app/util/kernel.py` - Kernel smoothing
- `app/util/style.py` - Plot styling
- `app/config.py` - Configuration
- `build_tfs/` - TFS computation pipeline

---

## Part 7: Recommended Cleanup Actions

### High Priority (Safe to Delete)

1. **Delete Streamlit files (CRITICAL - NO LONGER SUPPORTED)**:
   ```
   - streamlit_app.py (if exists)
   - streamlit_secrets.toml
   - run_dashboard.bat
   - run_dashboard.sh
   - app/util/cache.py (STREAMLIT-ONLY - DELETE)
   - app/ui/ (if exists - STREAMLIT UI COMPONENTS)
   ```

1b. **Delete outdated documentation (AGGRESSIVE CLEANUP)**:
   ```
   - PROJECT_PLAN.md (outdated Streamlit plan)
   - SIMPLIFIED_PROJECT_PLAN.md (outdated Streamlit plan)
   - CODE_REVIEW.md (outdated Streamlit code review)
   - CONTEXT.md (outdated Streamlit context)
   - SETUP_INSTRUCTIONS.md (outdated Streamlit setup)
   - HOSTING_INSTRUCTIONS.md (Streamlit hosting guide)
   - SHARING_CREDENTIALS.md (review - delete if credentials already set up)
   - CACHE_SYSTEM.md (review - delete if cache is self-explanatory)
   - cache/plots/README.md (review - delete if cache structure is obvious)
   ```

2. **Refactor Streamlit-dependent code (REQUIRED)**:
   ```
   - app/data/pbp_loader.py (remove @st.cache_data and Streamlit import)
   - app/data/bigquery_loader.py (optional: remove Streamlit code paths)
   - scripts/generate_cache.py (optional: remove Streamlit warning suppression)
   ```

3. **Delete log files**:
   ```
   - cache_build.log
   - cache_run.log
   - quick_test.log
   - test_run.log
   - debug_full.txt
   - debug_output.txt
   ```

4. **Delete test scripts** (KEEP analyze_p2_stats.py):
   ```
   - scripts/check_residuals.py
   - scripts/test_one_game_simple.py
   - scripts/test_single_game.py
   ```
   
   **Note**: `scripts/analyze_p2_stats.py` should be KEPT - it's the only analysis script needed.

### Medium Priority (Review First)

5. **Review and potentially delete**:
   - `app/plots/combined.py` (if not used)
   - `app/plots/score_diff.py` (if not used)
   - `build_tfs/outputs/` (example outputs, not needed)

6. **Review documentation**:
   - Update `README.md` to reflect Pygame game (not Streamlit)
   - Consolidate or archive planning documents
   - Remove outdated setup/hosting instructions

### Low Priority (Optional)

7. **Optional cache management scripts**:
   - Keep `scripts/clean_old_cache.py`, `commit_cache.py`, `wipe_cache.py` if useful
   - Otherwise delete

---

## Part 8: Updated `requirements.txt` Recommendations

### Minimal Runtime Requirements (for game only)

```txt
# Runtime dependencies (for running the game)
pygame>=2.5.0
Pillow>=9.0.0
numpy>=1.23.0
```

### Full Requirements (for cache generation + game)

```txt
# Runtime dependencies (for running the game)
pygame>=2.5.0
Pillow>=9.0.0

# Build-time dependencies (for generating cache)
pandas>=1.5.0
numpy>=1.23.0
matplotlib>=3.6.0
requests>=2.28.0
google-cloud-bigquery>=3.11.0
scipy>=1.9.0  # Optional but recommended for p-value calculations
```

**⚠️ IMPORTANT**: Remove `streamlit` from `requirements.txt` if it exists. Streamlit is no longer supported.

---

## Part 9: Critical Path Analysis

### What Happens When You Run `python run_game.py`?

1. **`run_game.py`** imports `app.game_pygame.main()`
2. **`app/game_pygame.py`** initializes:
   - Scans `cache/plots/` for `*.png` files (excludes `*_residuals.png`)
   - Loads `{game_id}_residuals.pkl` files
   - Preloads all plot images into memory
3. **Game loop**:
   - Displays current game plot
   - Waits for user input (keyboard/mouse)
   - Calculates correctness from residual data
   - Advances to next game

### What Happens If Cache Doesn't Exist?

- Game exits with error: `"ERROR: No cached plots found. Please run 'python scripts/generate_cache.py' first."`

### What Happens If Residual Data Missing?

- Game continues but correctness calculation may fail
- Code handles missing residual data gracefully (checks for `None`)

---

## Part 10: Module Import Tree (for Cache Generation)

### Cache Generation Import Chain

```
scripts/generate_cache.py
├── app/util/plot_cache.py
│   ├── app/plots/tempo.py
│   │   ├── app/tfs/change_points.py
│   │   ├── app/tfs/segments.py
│   │   ├── app/util/kernel.py
│   │   └── app/util/style.py
│   ├── app/data/pbp_loader.py
│   │   ├── app/data/get_pbp.py
│   │   └── ❌ app/util/cache.py (Streamlit - MUST BE DELETED)
│   ├── app/data/status.py
│   ├── app/data/bigquery_loader.py
│   │   └── app/config.py
│   ├── app/data/efg.py
│   ├── app/tfs/preprocess.py
│   │   └── build_tfs/builders/action_time/* (all modules)
│   └── app/tfs/compute.py
│       └── build_tfs/builders/action_time/build_tfs_detailed.py
└── requests (ESPN API)
```

**Key Insight**: Cache generation requires the entire TFS processing pipeline, but the game itself only needs the cache files.

**⚠️ STREAMLIT REMOVAL NOTE**: `app/data/pbp_loader.py` currently depends on `app/util/cache.py` (Streamlit-only). This dependency must be removed by refactoring `pbp_loader.py` to remove Streamlit caching.

---

## Part 11: Final Recommendations

### Keep These (Required)

**Core Game**:
- ✅ `run_game.py`
- ✅ `app/game_pygame.py`
- ✅ `cache/plots/` (generated cache)

**Cache Generation**:
- ✅ `scripts/generate_cache.py` (needs Streamlit warning cleanup)
- ✅ `app/data/` (all modules, but `pbp_loader.py` needs refactoring)
- ✅ `app/tfs/` (all modules)
- ✅ `app/plots/tempo.py`
- ✅ `app/util/plot_cache.py` (caching module - outputs used by run_game)
- ✅ `app/util/kernel.py`
- ✅ `app/util/style.py`
- ✅ `app/config.py`
- ✅ `build_tfs/` (entire directory)

**Analysis Scripts:**
- ✅ `scripts/analyze_p2_stats.py` (KEEP - only analysis script needed, not directly supporting run_game but required)

**Configuration**:
- ✅ `requirements.txt`
- ✅ `meatloaf.json` (for BigQuery)

### Delete These (Not Needed)

**Streamlit Files (CRITICAL - NO LONGER SUPPORTED)**:
- ❌ `streamlit_app.py` (if exists)
- ❌ `streamlit_secrets.toml`
- ❌ `run_dashboard.bat` (**DELETE - Streamlit launcher**)
- ❌ `run_dashboard.sh` (**DELETE - Streamlit launcher**)
- ❌ `app/util/cache.py` (**STREAMLIT-ONLY - DELETE IMMEDIATELY**)
- ❌ `app/ui/` directory (if exists - Streamlit UI components)

**Outdated Documentation (DELETE - Project Pivoted Multiple Times)**:
- ❌ `PROJECT_PLAN.md` (outdated Streamlit implementation plan)
- ❌ `SIMPLIFIED_PROJECT_PLAN.md` (outdated Streamlit plan)
- ❌ `CODE_REVIEW.md` (outdated Streamlit code review)
- ❌ `CONTEXT.md` (outdated Streamlit context)
- ❌ `SETUP_INSTRUCTIONS.md` (outdated Streamlit setup)
- ❌ `HOSTING_INSTRUCTIONS.md` (Streamlit hosting guide)
- ⚠️ `SHARING_CREDENTIALS.md` (review - delete if credentials already set up)
- ⚠️ `CACHE_SYSTEM.md` (review - delete if cache is self-explanatory)
- ⚠️ `cache/plots/README.md` (review - delete if cache structure is obvious)

**Streamlit-Dependent Code (MUST BE REFACTORED)**:
- ⚠️ `app/data/pbp_loader.py` - Remove `@st.cache_data` and Streamlit import
- ⚠️ `app/data/bigquery_loader.py` - Optional: Remove Streamlit code paths
- ⚠️ `scripts/generate_cache.py` - Optional: Remove Streamlit warning suppression

**Log Files**:
- ❌ All `.log` and `.txt` debug files

**Test/Analysis Scripts**:
- ✅ `scripts/analyze_p2_stats.py` (**KEEP** - only analysis script needed)
- ❌ `scripts/check_residuals.py`
- ❌ `scripts/test_*.py`

**Unused Plot Modules** (if confirmed unused):
- ❌ `app/plots/combined.py`
- ❌ `app/plots/score_diff.py`

### Review These (Decision Needed)

**Documentation**:
- ⚠️ **UPDATE REQUIRED**: `README.md` - Rewrite for Pygame game (currently describes Streamlit dashboard)
- ✅ **KEEP**: `HALFTIME_GAME_SPEC.md` - Original spec (useful reference)
- ✅ **KEEP**: `build_tfs/README.md` - TFS processing docs
- ✅ **KEEP**: `build_tfs/TFS_CONTEXT.md` - TFS technical context
- ⚠️ **REVIEW**: `SHARING_CREDENTIALS.md` - Delete if credentials already set up
- ⚠️ **REVIEW**: `CACHE_SYSTEM.md` - Delete if cache system is self-explanatory
- ⚠️ **REVIEW**: `cache/plots/README.md` - Delete if cache structure is obvious

**Cache Management**:
- ⚠️ Keep or delete `scripts/clean_old_cache.py`, `commit_cache.py`, `wipe_cache.py`

**Build Outputs**:
- ⚠️ Delete `build_tfs/outputs/` if not needed for debugging

---

## Part 12: Verification Checklist

After cleanup, verify:

- [ ] `python run_game.py` runs successfully
- [ ] Game loads plots from `cache/plots/`
- [ ] Game loads residual data from `cache/plots/*_residuals.pkl`
- [ ] User can make predictions (Fast/Slow)
- [ ] Correctness calculation works
- [ ] Score tracking works
- [ ] `python scripts/generate_cache.py` still works (if needed)
- [ ] Cache generation produces valid PNG and PKL files
- [ ] No import errors when running either script

---

## Summary

**Runtime for `run_game.py`**: Minimal - only pygame, Pillow, and numpy (if PIL fallback used).

**Cache Generation**: Requires full TFS processing pipeline with pandas, numpy, matplotlib, requests, BigQuery client, and all `app/` and `build_tfs/` modules.

**⚠️ CRITICAL CLEANUP - Streamlit Removal**: 
- **DELETE IMMEDIATELY**: `app/util/cache.py`, `streamlit_secrets.toml`, `run_dashboard.bat`, `run_dashboard.sh`, `streamlit_app.py` (if exists), `app/ui/` (if exists)
- **MUST REFACTOR**: `app/data/pbp_loader.py` to remove Streamlit dependency (`@st.cache_data` decorator)
- **OPTIONAL CLEANUP**: Remove Streamlit code paths from `app/data/bigquery_loader.py` and Streamlit warning suppression from `scripts/generate_cache.py`

**⚠️ AGGRESSIVE DOCUMENTATION CLEANUP** (Project Pivoted Multiple Times):
- **DELETE**: All outdated planning docs (`PROJECT_PLAN.md`, `SIMPLIFIED_PROJECT_PLAN.md`, `CODE_REVIEW.md`, `CONTEXT.md`)
- **DELETE**: All Streamlit-specific setup/hosting docs (`SETUP_INSTRUCTIONS.md`, `HOSTING_INSTRUCTIONS.md`)
- **REVIEW/DELETE**: `SHARING_CREDENTIALS.md`, `CACHE_SYSTEM.md`, `cache/plots/README.md` (delete if outdated or obvious)
- **KEEP**: `HALFTIME_GAME_SPEC.md` (reference), `build_tfs/README.md`, `build_tfs/TFS_CONTEXT.md` (technical docs)
- **UPDATE REQUIRED**: `README.md` - Rewrite for Pygame game

**General Cleanup**: Safe to delete log files, test scripts, and unused plot modules. Review documentation and cache management scripts.

---

## Quick Reference: Complete File Deletion List

### High Priority - Delete Immediately

**Streamlit Files:**
- `streamlit_app.py` (if exists)
- `streamlit_secrets.toml`
- `run_dashboard.bat`
- `run_dashboard.sh`
- `app/util/cache.py`
- `app/ui/` (if exists)

**Log Files:**
- `cache_build.log`
- `cache_run.log`
- `quick_test.log`
- `test_run.log`
- `debug_full.txt`
- `debug_output.txt`

**Test/Analysis Scripts:**
- ✅ `scripts/analyze_p2_stats.py` (**KEEP** - only analysis script needed)
- ❌ `scripts/check_residuals.py`
- ❌ `scripts/test_one_game_simple.py`
- ❌ `scripts/test_single_game.py`

### Medium Priority - Delete (Outdated Documentation)

**Outdated Planning Docs:**
- `PROJECT_PLAN.md`
- `SIMPLIFIED_PROJECT_PLAN.md`
- `CODE_REVIEW.md`
- `CONTEXT.md`

**Streamlit-Specific Docs:**
- `SETUP_INSTRUCTIONS.md`
- `HOSTING_INSTRUCTIONS.md`

**Review Then Delete:**
- `SHARING_CREDENTIALS.md` (delete if credentials already set up)
- `CACHE_SYSTEM.md` (delete if cache is self-explanatory)
- `cache/plots/README.md` (delete if cache structure is obvious)

### Low Priority - Review Then Delete

**Unused Plot Modules:**
- `app/plots/combined.py` (if not used by cache generation)
- `app/plots/score_diff.py` (if not used by cache generation)

**Cache Management Scripts:**
- `scripts/clean_old_cache.py` (delete if not needed)
- `scripts/commit_cache.py` (delete if not needed)
- `scripts/wipe_cache.py` (delete if not needed)

**Build Outputs:**
- `build_tfs/outputs/` (delete example outputs)

### Keep (Required or Useful)

**Core Game:**
- `run_game.py`
- `app/game_pygame.py`
- `cache/plots/` (generated cache)

**Cache Generation:**
- `scripts/generate_cache.py`
- All `app/` modules (except Streamlit-dependent ones)
- All `build_tfs/` modules
- `app/util/plot_cache.py` (caching module - outputs used by run_game)

**Analysis Scripts:**
- `scripts/analyze_p2_stats.py` (KEEP - only analysis script needed)

**Documentation:**
- `HALFTIME_GAME_SPEC.md` (reference)
- `build_tfs/README.md` (technical docs)
- `build_tfs/TFS_CONTEXT.md` (technical docs)
- `DEPENDENCY_REVIEW.md` (this document)

**Configuration:**
- `requirements.txt`
- `meatloaf.json` (BigQuery credentials)
- `app/config.py`

**Update Required:**
- `README.md` (rewrite for Pygame game)

