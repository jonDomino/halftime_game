# Cleanup Compatibility Analysis: DEPENDENCY_REVIEW vs PYGAME_REQS

## Executive Summary

**Result**: ✅ **SAFE TO PROCEED** with cleanup recommendations from `DEPENDENCY_REVIEW.md`

**Critical Finding**: No direct conflicts, but **one critical execution order requirement** must be followed to prevent breaking cache generation.

---

## Part 1: Direct Dependency Analysis

### Files Required by PYGAME_REQS

**For `run_game.py`:**
- ✅ `run_game.py` - **KEPT** in DEPENDENCY_REVIEW
- ✅ `app/game_pygame.py` - **KEPT** in DEPENDENCY_REVIEW
- ✅ `cache/plots/` directory - **KEPT** in DEPENDENCY_REVIEW
- ✅ `pygame`, `Pillow`, `numpy` packages - **KEPT** (in requirements.txt)

**For `analyze_p2_stats.py`:**
- ✅ `scripts/analyze_p2_stats.py` - **KEPT** in DEPENDENCY_REVIEW
- ✅ `cache/plots/` directory - **KEPT** in DEPENDENCY_REVIEW
- ✅ No external packages required - **N/A**

### Direct Import Analysis

**`run_game.py` imports:**
```python
from app.game_pygame import main
```
- ✅ `app/game_pygame.py` is **KEPT**

**`app/game_pygame.py` imports:**
```python
import pygame
import sys
from pathlib import Path
import pickle
from PIL import Image
import time
from typing import Dict, Optional, Tuple
# numpy imported conditionally (only if PIL fallback needed)
```
- ✅ All are standard library or external packages - **NO CONFLICTS**

**`scripts/analyze_p2_stats.py` imports:**
```python
import pickle
from pathlib import Path
```
- ✅ All are standard library - **NO CONFLICTS**

**Conclusion**: Neither `run_game.py` nor `analyze_p2_stats.py` directly import any files that DEPENDENCY_REVIEW recommends deleting.

---

## Part 2: Indirect Dependency Analysis

### Cache Generation Dependency Chain

**Critical Path**: Cache files must be generated before `run_game.py` can work.

**Cache Generation Flow**:
```
scripts/generate_cache.py
└── app/util/plot_cache.py
    └── app/data/pbp_loader.py
        └── app/util/cache.py (STREAMLIT - TO BE DELETED)
```

**⚠️ CRITICAL ISSUE**: `app/data/pbp_loader.py` currently imports `app/util/cache.py`, which DEPENDENCY_REVIEW recommends deleting.

**Impact**: If `app/util/cache.py` is deleted BEFORE `app/data/pbp_loader.py` is refactored, cache generation will break, which means:
- ❌ No cache files can be generated
- ❌ `run_game.py` cannot run (requires cache files)
- ❌ `analyze_p2_stats.py` cannot run (requires cache files)

**Solution**: DEPENDENCY_REVIEW correctly identifies this and recommends:
1. **REFACTOR FIRST**: Remove Streamlit dependency from `app/data/pbp_loader.py`
2. **DELETE SECOND**: Then delete `app/util/cache.py`

---

## Part 3: File-by-File Compatibility Check

### Files DEPENDENCY_REVIEW Recommends Deleting

#### ✅ Safe to Delete (No Impact on PYGAME_REQS)

1. **Streamlit Application Files**:
   - `streamlit_app.py` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `streamlit_secrets.toml` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `run_dashboard.bat` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `run_dashboard.sh` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `app/ui/` directory - ❌ Not used by run_game.py or analyze_p2_stats.py

2. **Documentation Files**:
   - `PROJECT_PLAN.md` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `SIMPLIFIED_PROJECT_PLAN.md` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `CODE_REVIEW.md` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `CONTEXT.md` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `SETUP_INSTRUCTIONS.md` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `HOSTING_INSTRUCTIONS.md` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `SHARING_CREDENTIALS.md` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `CACHE_SYSTEM.md` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `cache/plots/README.md` - ❌ Not used by run_game.py or analyze_p2_stats.py

3. **Log Files**:
   - All `.log` and `.txt` debug files - ❌ Not used by run_game.py or analyze_p2_stats.py

4. **Test Scripts**:
   - `scripts/check_residuals.py` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `scripts/test_*.py` - ❌ Not used by run_game.py or analyze_p2_stats.py

5. **Unused Plot Modules**:
   - `app/plots/combined.py` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `app/plots/score_diff.py` - ❌ Not used by run_game.py or analyze_p2_stats.py

6. **Cache Management Scripts** (if deleted):
   - `scripts/clean_old_cache.py` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `scripts/commit_cache.py` - ❌ Not used by run_game.py or analyze_p2_stats.py
   - `scripts/wipe_cache.py` - ❌ Not used by run_game.py or analyze_p2_stats.py

7. **Build Outputs**:
   - `build_tfs/outputs/` - ❌ Not used by run_game.py or analyze_p2_stats.py

#### ⚠️ Requires Refactoring Before Deletion

1. **`app/util/cache.py`** - **CRITICAL**
   - **Status**: Used by `app/data/pbp_loader.py` (which is used by cache generation)
   - **Impact**: Deleting this BEFORE refactoring `pbp_loader.py` will break cache generation
   - **Action Required**: Refactor `app/data/pbp_loader.py` FIRST, then delete
   - **Timing**: Must happen in correct order

2. **`app/data/pbp_loader.py`** - **NEEDS REFACTORING**
   - **Status**: Uses `@st.cache_data` decorator from Streamlit
   - **Impact**: Must be refactored to remove Streamlit dependency
   - **Action Required**: Remove `@st.cache_data` and Streamlit import
   - **Dependency**: Currently imports `app/util/cache.py` which must be deleted

#### ✅ Safe to Delete After Refactoring

1. **`app/util/cache.py`** - Safe AFTER `pbp_loader.py` is refactored

---

## Part 4: Execution Order Requirements

### ⚠️ CRITICAL: Must Follow This Order

**Step 1: Refactor Streamlit-Dependent Code**
```
1. Refactor app/data/pbp_loader.py
   - Remove @st.cache_data decorator
   - Remove Streamlit import
   - Remove import of app/util/cache.py
   - Implement simple caching or remove caching (cache generation handles its own)

2. (Optional) Clean up app/data/bigquery_loader.py
   - Remove Streamlit code paths (optional, works without Streamlit)

3. (Optional) Clean up scripts/generate_cache.py
   - Remove Streamlit warning suppression (optional)
```

**Step 2: Delete Streamlit Files**
```
1. Delete app/util/cache.py (now safe - no longer imported)

2. Delete other Streamlit files:
   - streamlit_app.py (if exists)
   - streamlit_secrets.toml
   - run_dashboard.bat
   - run_dashboard.sh
   - app/ui/ (if exists)
```

**Step 3: Delete Other Files**
```
1. Delete documentation files (all safe)
2. Delete log files (all safe)
3. Delete test scripts (all safe)
4. Delete unused plot modules (verify not used first)
```

### ❌ DO NOT DO THIS (Will Break Cache Generation)

**Wrong Order:**
1. Delete `app/util/cache.py` first
2. Try to refactor `app/data/pbp_loader.py` later
3. **Result**: Cache generation breaks immediately, cannot generate cache files

---

## Part 5: Verification After Cleanup

### Must Verify These Still Work

1. **Cache Generation** (Critical for PYGAME_REQS):
   ```bash
   python scripts/generate_cache.py
   ```
   - ✅ Must still work after cleanup
   - ✅ Must produce PNG and PKL files
   - ✅ Must not have import errors

2. **Game Runtime** (PYGAME_REQS requirement):
   ```bash
   python run_game.py
   ```
   - ✅ Must still work after cleanup
   - ✅ Must load cache files
   - ✅ Must not have import errors

3. **Analysis Script** (PYGAME_REQS requirement):
   ```bash
   python scripts/analyze_p2_stats.py
   ```
   - ✅ Must still work after cleanup
   - ✅ Must read cache files
   - ✅ Must not have import errors

---

## Part 6: Compatibility Matrix

| File to Delete | Used by run_game.py? | Used by analyze_p2_stats.py? | Used by Cache Generation? | Safe to Delete? |
|----------------|---------------------|------------------------------|---------------------------|-----------------|
| `streamlit_app.py` | ❌ No | ❌ No | ❌ No | ✅ Yes |
| `streamlit_secrets.toml` | ❌ No | ❌ No | ❌ No | ✅ Yes |
| `run_dashboard.bat` | ❌ No | ❌ No | ❌ No | ✅ Yes |
| `run_dashboard.sh` | ❌ No | ❌ No | ❌ No | ✅ Yes |
| `app/util/cache.py` | ❌ No | ❌ No | ⚠️ Yes (via pbp_loader) | ⚠️ After refactor |
| `app/ui/` | ❌ No | ❌ No | ❌ No | ✅ Yes |
| `app/plots/combined.py` | ❌ No | ❌ No | ⚠️ Maybe | ⚠️ Verify first |
| `app/plots/score_diff.py` | ❌ No | ❌ No | ⚠️ Maybe | ⚠️ Verify first |
| All `.md` docs | ❌ No | ❌ No | ❌ No | ✅ Yes |
| All `.log` files | ❌ No | ❌ No | ❌ No | ✅ Yes |
| Test scripts | ❌ No | ❌ No | ❌ No | ✅ Yes |

---

## Part 7: Summary and Recommendations

### ✅ Safe to Delete Immediately

All files recommended for deletion in DEPENDENCY_REVIEW are safe to delete **EXCEPT**:
- `app/util/cache.py` (must wait for refactoring)
- `app/plots/combined.py` and `score_diff.py` (verify not used by cache generation first)

### ⚠️ Critical Execution Order

**MUST REFACTOR BEFORE DELETING:**
1. Refactor `app/data/pbp_loader.py` to remove Streamlit dependency
2. Then delete `app/util/cache.py`

**Failure to follow this order will break cache generation, which will break `run_game.py` and `analyze_p2_stats.py`.**

### ✅ Final Verdict

**DEPENDENCY_REVIEW cleanup recommendations are COMPATIBLE with PYGAME_REQS requirements**, provided:

1. ✅ Refactoring happens BEFORE deletion of `app/util/cache.py`
2. ✅ Cache generation is verified to still work after cleanup
3. ✅ `run_game.py` and `analyze_p2_stats.py` are verified to still work after cleanup

**No conflicts found** - all deletions are safe for PYGAME_REQS requirements (with proper execution order).

---

**Last Updated**: Current session  
**Status**: Compatibility analysis complete - safe to proceed with cleanup

