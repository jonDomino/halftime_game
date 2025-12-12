"""Clean up old cache files with _hidden/_visible suffixes.

Run this script to delete old plot cache files before regenerating with Period 1 only.
"""
from pathlib import Path

CACHE_DIR = Path("cache/plots")

def main():
    """Delete old cache files with _hidden or _visible suffixes."""
    if not CACHE_DIR.exists():
        print("Cache directory does not exist. Nothing to clean.")
        return
    
    deleted_count = 0
    
    # Find and delete old format files
    for png_file in CACHE_DIR.glob("*_hidden.png"):
        print(f"Deleting old format: {png_file.name}")
        png_file.unlink()
        deleted_count += 1
    
    for png_file in CACHE_DIR.glob("*_visible.png"):
        print(f"Deleting old format: {png_file.name}")
        png_file.unlink()
        deleted_count += 1
    
    print(f"\nDeleted {deleted_count} old cache files.")
    print("You can now run 'python scripts/generate_cache.py' to regenerate plots with Period 1 only.")

if __name__ == "__main__":
    main()

