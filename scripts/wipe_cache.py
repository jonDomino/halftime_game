"""Wipe all cached plots and residual data"""
from pathlib import Path
import shutil

CACHE_DIR = Path("cache/plots")

def main():
    """Delete all cached plots and residual data."""
    if CACHE_DIR.exists():
        # Delete all PNG and PKL files
        deleted = 0
        for file in CACHE_DIR.glob("*.png"):
            file.unlink()
            deleted += 1
        for file in CACHE_DIR.glob("*.pkl"):
            file.unlink()
            deleted += 1
        print(f"Deleted {deleted} cache files")
    else:
        print("Cache directory does not exist")

if __name__ == "__main__":
    main()

