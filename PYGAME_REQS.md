# Pygame Requirements: Supporting `run_game.py` and `analyze_p2_stats.py`

## Overview

This document provides a comprehensive explanation of what is needed to support the two main runtime components of the Halftime Game project:

1. **`run_game.py`** - The Pygame-based desktop game application
2. **`scripts/analyze_p2_stats.py`** - Analysis script for Period 2 statistics

Both components are **read-only** - they consume pre-generated cache files and do not require the full TFS processing pipeline or data fetching capabilities.

---

## Part 1: Python Version Requirements

### Minimum Python Version
- **Python 3.8+** (required for `pathlib.Path` and modern typing support)

### Recommended Python Version
- **Python 3.9+** (better type hint support, improved performance)

### Verification
```bash
python --version
# Should show Python 3.8 or higher
```

---

## Part 2: Package Dependencies

### For `run_game.py`

#### Required Packages

1. **pygame** (>=2.5.0)
   - **Purpose**: Core game engine for rendering, window management, event handling
   - **Usage**: 
     - Window creation and display
     - Image loading and rendering
     - Keyboard/mouse event handling
     - Font rendering
     - Surface operations
   - **Install**: `pip install pygame>=2.5.0`

2. **Pillow (PIL)** (>=9.0.0)
   - **Purpose**: Image loading fallback (used if pygame fails to load PNG)
   - **Usage**: `Image.open()` as fallback in `_preload_images()`
   - **Note**: Only used if pygame's native image loader fails
   - **Install**: `pip install Pillow>=9.0.0`

3. **numpy** (>=1.23.0)
   - **Purpose**: Convert PIL Image to pygame Surface (fallback path only)
   - **Usage**: `np.array(pil_img)` → `pygame.surfarray.make_surface()`
   - **Note**: Only needed if PIL fallback is triggered
   - **Install**: `pip install numpy>=1.23.0`

#### Python Standard Library (No Installation Needed)
- `sys` - System operations, exit handling
- `pathlib.Path` - File path operations
- `pickle` - Loading residual data from `.pkl` files
- `time` - Time operations (minimal use)
- `typing` - Type hints (Dict, Optional, Tuple)

### For `analyze_p2_stats.py`

#### Required Packages
**None** - Uses only Python standard library

#### Python Standard Library Used
- `pickle` - Loading residual data from `.pkl` files
- `pathlib.Path` - File path operations for finding cache files

### Complete Dependency List

**Minimal requirements.txt for runtime:**
```txt
# Runtime dependencies (for run_game.py and analyze_p2_stats.py)
pygame>=2.5.0
Pillow>=9.0.0
numpy>=1.23.0
```

**Note**: `numpy` is technically optional (only needed for PIL fallback), but it's recommended to include it for reliability.

---

## Part 3: File Structure Requirements

### Required Directory Structure

```
halftime_game/
├── run_game.py                    # Entry point (REQUIRED)
├── app/
│   └── game_pygame.py            # Game implementation (REQUIRED)
├── scripts/
│   └── analyze_p2_stats.py       # Analysis script (REQUIRED)
└── cache/
    └── plots/                     # Cache directory (REQUIRED)
        ├── {game_id}.png          # Plot images (REQUIRED for run_game.py)
        └── {game_id}_residuals.pkl # Residual data (REQUIRED for both)
```

### File Descriptions

#### `run_game.py`
- **Location**: Root directory
- **Size**: 6 lines
- **Purpose**: Thin wrapper that calls `app.game_pygame.main()`
- **Required**: Yes

#### `app/game_pygame.py`
- **Location**: `app/` directory
- **Size**: ~339 lines
- **Purpose**: Complete Pygame game implementation
- **Required**: Yes
- **Dependencies**: pygame, PIL, numpy (via imports)

#### `scripts/analyze_p2_stats.py`
- **Location**: `scripts/` directory
- **Size**: ~86 lines
- **Purpose**: Analyzes Period 2 residual statistics from cache
- **Required**: Yes (for analysis)
- **Dependencies**: None (standard library only)

#### `cache/plots/` Directory
- **Location**: `cache/plots/` directory
- **Purpose**: Stores pre-generated cache files
- **Required**: Yes (must exist, but can be empty initially)
- **Contents**:
  - `{game_id}.png` - Plot images (required for `run_game.py`)
  - `{game_id}_residuals.pkl` - Residual data (required for both scripts)

---

## Part 4: Cache File Requirements

### For `run_game.py`

#### Required Cache Files

1. **Plot Images** (`{game_id}.png`)
   - **Format**: PNG image files
   - **Location**: `cache/plots/{game_id}.png`
   - **Purpose**: Displayed in game window
   - **Content**: Tempo visualization plots (Period 1 data)
   - **Note**: Files ending in `_residuals.png` are ignored

2. **Residual Data** (`{game_id}_residuals.pkl`)
   - **Format**: Pickle files (Python serialized data)
   - **Location**: `cache/plots/{game_id}_residuals.pkl`
   - **Purpose**: Contains correctness calculation data
   - **Required Keys**:
     - `p_value_p2` - Used to determine if Period 2 was fast or slow
     - `median_residual_p2` - Alternative metric (optional)
     - `avg_residual_p2` - Alternative metric (optional)

#### Cache File Structure

**Residual Data Dictionary Structure:**
```python
{
    'p_value_p2': float,           # Primary metric for correctness
    'median_residual_p2': float,   # Alternative metric
    'avg_residual_p2': float,      # Alternative metric
    # ... other residual data (not used by game)
}
```

**Correctness Logic:**
- `p_value_p2 < 0.5` → Period 2 was **faster** than expected
- `p_value_p2 >= 0.5` → Period 2 was **slower** than expected

### For `analyze_p2_stats.py`

#### Required Cache Files

1. **Residual Data Files** (`*_residuals.pkl`)
   - **Format**: Pickle files
   - **Location**: `cache/plots/*_residuals.pkl`
   - **Purpose**: Analyzes Period 2 statistics across all games
   - **Required Keys**:
     - `median_residual_p2` - Used for analysis
     - `p_value_p2` - Used for analysis
     - `avg_residual_p2` - Used for analysis

#### Analysis Metrics

The script analyzes three metrics:
1. **median_residual_p2**: `< 0` = faster, `>= 0` = slower
2. **p_value_p2**: `< 0.5` = faster, `>= 0.5` = slower
3. **avg_residual_p2**: `< 0` = faster, `>= 0` = slower

---

## Part 5: Runtime Requirements

### For `run_game.py`

#### System Requirements

1. **Display**: 
   - Windowed display (1200x900 pixels)
   - Supports keyboard and mouse input

2. **Memory**:
   - Preloads all plot images into memory
   - Memory usage depends on number of cached games
   - Typical: ~50-200KB per plot image

3. **File System**:
   - Read access to `cache/plots/` directory
   - Read access to all `.png` and `.pkl` files

#### Initialization Process

1. **Scan Cache Directory**:
   - Finds all `*.png` files in `cache/plots/`
   - Excludes files ending in `_residuals.png`
   - Extracts game IDs from filenames

2. **Load Residual Data**:
   - Loads `{game_id}_residuals.pkl` for each game
   - Stores in memory dictionary

3. **Preload Images**:
   - Loads all plot images into memory
   - Uses pygame's native loader (faster)
   - Falls back to PIL + numpy if pygame fails

4. **Error Handling**:
   - Exits with error if no cached plots found
   - Continues if residual data missing (graceful degradation)

#### Game Loop Requirements

- **Frame Rate**: 60 FPS
- **Input**: Keyboard (←/→ arrows, ESC) and mouse clicks
- **Display**: Updates on every frame

#### Game Features

1. **Visual Feedback**:
   - **Flash Overlay**: 100ms color flash after prediction
     - Green flash (RGB: 0, 200, 0) if Period 2 was faster
     - Red flash (RGB: 200, 0, 0) if Period 2 was slower
     - 15% opacity overlay (alpha: 38/255)
   - **Result Text Display**: Shows correctness result after 100ms delay
     - "✅ Correct! 2H went {faster/slower}"
     - "❌ Incorrect. 2H went {faster/slower}"
     - Color-coded: Green for correct, red for incorrect

2. **Auto-Advance Mechanism**:
   - Automatically advances to next game after 1.5 seconds
   - Uses `pygame.USEREVENT` timer event
   - Timer is cancelled after triggering

3. **Game Looping**:
   - When reaching the last game, loops back to first game
   - Resets all game states on loop
   - Resets score tally on loop (allows replay)

4. **State Management**:
   - Per-game state tracking (prediction_made, user_prediction, correctness)
   - Global score tally (correct/total with percentage)
   - Flash state (active, color, start_time)
   - Result display timing (result_show_time)

#### UI Rendering Details

1. **Image Scaling**:
   - Maintains aspect ratio when scaling plot images
   - Scales to fit window: `min((WINDOW_WIDTH - 40) / img_width, (WINDOW_HEIGHT - 200) / img_height)`
   - Centers scaled image in window
   - Handles images of any size

2. **Font System**:
   - **Large Font**: 48pt (title)
   - **Medium Font**: 36pt (score, buttons, result)
   - **Small Font**: 24pt (progress, instructions)
   - Uses pygame default font (None)

3. **Visual Effects**:
   - **Alpha Blending**: Used for flash overlay (15% opacity)
   - **Surface Operations**: `pygame.Surface.set_alpha()` for transparency
   - **Color Coding**: 
     - Green (100, 200, 100) for Fast button
     - Red (200, 100, 100) for Slow button
     - Black borders on buttons (3px width)

4. **Display Elements**:
   - **Title**: "Halftime Game 🏀" (top-left, large font)
   - **Score**: "Score: X/Y (Z.Z%)" (below title, medium font)
   - **Progress**: "Game X of Y" (below score, small font, gray)
   - **Plot Image**: Centered, scaled to fit
   - **Buttons**: Fast (right) and Slow (left) with keyboard hints
   - **Instructions**: "Press ← for Slow, → for Fast" (above buttons)
   - **Result Text**: Centered at bottom after prediction

#### Event System

1. **Timer Events**:
   - Uses `pygame.USEREVENT` for auto-advance
   - Timer set to 1500ms (1.5 seconds) after prediction
   - Timer cancelled after triggering (set_timer(USEREVENT, 0))

2. **Input Events**:
   - **Keyboard**:
     - `pygame.K_LEFT` (←): Predict "slow"
     - `pygame.K_RIGHT` (→): Predict "fast"
     - `pygame.K_ESCAPE`: Quit game
   - **Mouse**:
     - Left click detection with precise hitbox checking
     - Slow button: `WINDOW_WIDTH // 2 - 220` to `WINDOW_WIDTH // 2 - 20`, `button_y` to `button_y + 60`
     - Fast button: `WINDOW_WIDTH // 2 + 20` to `WINDOW_WIDTH // 2 + 220`, `button_y` to `button_y + 60`
   - **Window**:
     - `pygame.QUIT`: Close window (X button)

3. **Time-Based Delays**:
   - **Result Text Delay**: 100ms after prediction (stored in game_state['result_show_time'])
   - **Flash Duration**: 100ms (FLASH_DURATION_MS constant)
   - **Auto-Advance Delay**: 1500ms (1.5 seconds)

### For `analyze_p2_stats.py`

#### System Requirements

1. **Memory**: 
   - Minimal - loads one pickle file at a time
   - Processes files sequentially

2. **File System**:
   - Read access to `cache/plots/` directory
   - Read access to all `*_residuals.pkl` files

#### Execution Process

1. **Find Residual Files**:
   - Scans `cache/plots/` for `*_residuals.pkl` files
   - Processes each file sequentially

2. **Load and Analyze**:
   - Loads pickle file
   - Extracts Period 2 metrics
   - Counts fast vs slow for each metric

3. **Output Statistics**:
   - Prints summary statistics to console
   - Shows percentages for each metric

#### Error Handling

- Continues processing if individual files fail
- Prints error message for problematic files
- Skips games with no Period 2 data

---

## Part 6: Setup Instructions

### Step 1: Install Python Dependencies

```bash
# Install required packages
pip install pygame>=2.5.0 Pillow>=9.0.0 numpy>=1.23.0
```

Or use requirements file (if it exists):
```bash
pip install -r requirements.txt
```

### Step 2: Verify Cache Directory Exists

```bash
# Check if cache directory exists
ls cache/plots/

# If it doesn't exist, create it
mkdir -p cache/plots
```

### Step 3: Generate Cache Files (If Not Present)

**Note**: Cache files must be generated using `scripts/generate_cache.py` (which requires additional dependencies). See `DEPENDENCY_REVIEW.md` for cache generation requirements.

If cache files already exist, skip this step.

### Step 4: Verify Installation

#### Test `run_game.py`:
```bash
python run_game.py
```

**Expected Behavior**:
- Game window opens
- Shows first game plot
- Displays "Fast" and "Slow" buttons
- Responds to keyboard/mouse input

**If No Cache Files**:
- Error message: "ERROR: No cached plots found. Please run `python scripts/generate_cache.py` first."
- Exit code: 1

#### Test `analyze_p2_stats.py`:
```bash
python scripts/analyze_p2_stats.py
```

**Expected Behavior**:
- Scans cache directory
- Prints statistics to console
- Shows percentages for each metric

**If No Cache Files**:
- Prints: "Total games with P2 data: 0"
- Exit code: 0 (no error, just no data)

---

## Part 7: Detailed Dependency Analysis

### `run_game.py` Dependency Tree

```
run_game.py
└── app/game_pygame.py
    ├── pygame (external)
    ├── sys (stdlib)
    ├── pathlib.Path (stdlib)
    ├── pickle (stdlib)
    ├── PIL.Image (external - Pillow)
    ├── time (stdlib)
    ├── typing (stdlib)
    └── numpy (external - only if PIL fallback used)
```

### `analyze_p2_stats.py` Dependency Tree

```
scripts/analyze_p2_stats.py
├── pickle (stdlib)
└── pathlib.Path (stdlib)
```

**No external dependencies required!**

---

## Part 8: Cache File Format Specifications

### PNG Plot Images

- **Format**: PNG (Portable Network Graphics)
- **Color Mode**: RGB or RGBA
- **Typical Size**: 50-200KB per file
- **Dimensions**: Variable (determined by plot generation)
- **Content**: Matplotlib-generated tempo visualization plots

### Pickle Residual Data Files

- **Format**: Python pickle (binary serialization)
- **Protocol**: Default (compatible with Python 3.8+)
- **Typical Size**: 1-5KB per file
- **Structure**: Python dictionary

**Example Residual Data:**
```python
{
    'p_value_p2': 0.42,              # Primary metric
    'median_residual_p2': -1.5,      # Alternative metric
    'avg_residual_p2': -1.2,         # Alternative metric
    'total_poss_p1': 65,              # Not used by game
    'total_poss_p2': 68,              # Not used by game
    # ... other residual statistics
}
```

---

## Part 9: Error Scenarios and Handling

### `run_game.py` Error Scenarios

1. **No Cache Directory**:
   - **Error**: `FileNotFoundError` when scanning cache
   - **Handling**: Returns empty list, exits with error message

2. **No Plot Images**:
   - **Error**: "ERROR: No cached plots found..."
   - **Handling**: Exits with code 1

3. **Missing Residual Data**:
   - **Error**: None (graceful degradation)
   - **Handling**: Game continues, correctness calculation may fail

4. **Corrupted Image File**:
   - **Error**: `pygame.error` or `PIL.UnidentifiedImageError`
   - **Handling**: Skips that image, continues with others

5. **Corrupted Pickle File**:
   - **Error**: `pickle.UnpicklingError`
   - **Handling**: Prints error, continues with other files

### `analyze_p2_stats.py` Error Scenarios

1. **No Cache Directory**:
   - **Error**: `FileNotFoundError`
   - **Handling**: Returns empty list, prints "Total games with P2 data: 0"

2. **No Residual Files**:
   - **Error**: None
   - **Handling**: Prints "Total games with P2 data: 0"

3. **Corrupted Pickle File**:
   - **Error**: `pickle.UnpicklingError` or `Exception`
   - **Handling**: Prints error message, continues with other files

4. **Missing Period 2 Data**:
   - **Error**: None
   - **Handling**: Skips game, increments `no_data_count`

---

## Part 10: Performance Considerations

### `run_game.py` Performance

1. **Startup Time**:
   - Depends on number of cached games
   - Image loading: ~10-50ms per image
   - Typical: 1-5 seconds for 50-100 games

2. **Memory Usage**:
   - All images preloaded into memory
   - Typical: 5-20MB for 50-100 games
   - Scales linearly with number of games

3. **Runtime Performance**:
   - 60 FPS target
   - Minimal CPU usage (just rendering)
   - No disk I/O during gameplay (all cached)
   - Timer events handled efficiently (single USEREVENT)
   - Alpha blending for flash overlay (minimal performance impact)

### `analyze_p2_stats.py` Performance

1. **Execution Time**:
   - Depends on number of residual files
   - File loading: ~1-5ms per file
   - Typical: <1 second for 100+ games

2. **Memory Usage**:
   - Minimal - processes one file at a time
   - Typical: <10MB total

3. **Scalability**:
   - Linear time complexity O(n)
   - No performance degradation with many files

---

## Part 11: Verification Checklist

### Pre-Run Verification

- [ ] Python 3.8+ installed
- [ ] pygame >=2.5.0 installed
- [ ] Pillow >=9.0.0 installed
- [ ] numpy >=1.23.0 installed
- [ ] `cache/plots/` directory exists
- [ ] At least one `{game_id}.png` file exists (for `run_game.py`)
- [ ] At least one `{game_id}_residuals.pkl` file exists (for both)

### Post-Run Verification

**For `run_game.py`:**
- [ ] Game window opens successfully
- [ ] Plot images display correctly (scaled, centered)
- [ ] Keyboard input works (←/→ arrows, ESC)
- [ ] Mouse clicks work (precise button detection)
- [ ] Flash overlay appears after prediction (green/red, 100ms)
- [ ] Result text displays after 100ms delay
- [ ] Auto-advance works (1.5 seconds after prediction)
- [ ] Correctness calculation works (if residual data present)
- [ ] Score tracking works (with percentage display)
- [ ] Progress counter displays correctly
- [ ] Game loops back to start when reaching end
- [ ] State resets correctly on loop

**For `analyze_p2_stats.py`:**
- [ ] Script runs without errors
- [ ] Statistics print to console
- [ ] Percentages are calculated correctly
- [ ] Handles missing data gracefully

---

## Part 12: Troubleshooting

### Common Issues

1. **"No module named 'pygame'"**
   - **Solution**: `pip install pygame`

2. **"No module named 'PIL'"**
   - **Solution**: `pip install Pillow`

3. **"No cached plots found"**
   - **Solution**: Run `python scripts/generate_cache.py` first

4. **Game window doesn't open**
   - **Check**: Display server running (X11 on Linux, etc.)
   - **Check**: pygame installation: `python -c "import pygame; pygame.init()"`

5. **Images don't display**
   - **Check**: PNG files are valid (try opening in image viewer)
   - **Check**: File permissions (read access)
   - **Check**: Image scaling (should maintain aspect ratio)

6. **Pickle errors**
   - **Check**: Python version compatibility (pickle protocol)
   - **Check**: File corruption (try regenerating cache)

7. **Flash overlay doesn't appear**
   - **Check**: Residual data contains `p_value_p2`
   - **Check**: Prediction was made (game_state['prediction_made'] == True)
   - **Check**: Timer events working (pygame.USEREVENT)

8. **Auto-advance doesn't work**
   - **Check**: Timer event handling (pygame.USEREVENT)
   - **Check**: Timer cancellation (should cancel after triggering)
   - **Check**: Game state (should advance current_game_index)

9. **Game doesn't loop**
   - **Check**: Reached end of game_ids list
   - **Check**: State reset logic (should reset on loop)
   - **Check**: Score tally reset (should reset to 0/0)

---

## Summary

### Minimal Requirements for `run_game.py`
- Python 3.8+
- pygame >=2.5.0
- Pillow >=9.0.0
- numpy >=1.23.0 (recommended)
- Pre-generated cache files in `cache/plots/`

### Minimal Requirements for `analyze_p2_stats.py`
- Python 3.8+
- **No external packages required!**
- Pre-generated residual data files in `cache/plots/`

### Key Points
- Both scripts are **read-only** - they consume cache, don't generate it
- `analyze_p2_stats.py` has **zero external dependencies**
- `run_game.py` requires pygame for rendering
- Cache files must be generated separately (see `DEPENDENCY_REVIEW.md`)
- Both scripts handle missing data gracefully

### Game Features Summary
- **Visual Feedback**: 100ms color flash overlay (green/red) after prediction
- **Auto-Advance**: Automatically moves to next game after 1.5 seconds
- **Game Looping**: Loops back to start when reaching end, resets state
- **UI Elements**: Title, score (with percentage), progress counter, buttons, result text
- **Image Scaling**: Maintains aspect ratio, centers in window
- **Multiple Fonts**: Large (48pt), medium (36pt), small (24pt)
- **Event System**: Timer events for auto-advance, keyboard/mouse input
- **State Management**: Per-game state tracking, global score tally

---

**Last Updated**: Current session  
**Status**: Complete requirements documentation for Pygame runtime components

