"""Script to commit plot cache to git (for scheduled runs)"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.util.plot_cache import commit_cache_to_git, CACHE_DIR
import subprocess


def main():
    """Commit cache plots to git if there are changes."""
    print("Checking for plot cache changes...")
    
    # Check if cache directory exists
    if not CACHE_DIR.exists():
        print("No cache directory found.")
        return
    
    # Check if we're in a git repo
    result = subprocess.run(
        ['git', 'rev-parse', '--git-dir'],
        capture_output=True,
        text=True,
        cwd=Path.cwd()
    )
    if result.returncode != 0:
        print("Not in a git repository.")
        return
    
    # Commit cache
    success = commit_cache_to_git(dev_mode=True)
    if success:
        print("✅ Cache committed to git successfully!")
    else:
        print("ℹ️ No changes to commit or commit failed.")


if __name__ == "__main__":
    main()

