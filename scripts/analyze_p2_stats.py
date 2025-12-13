"""Analyze Period 2 residual stats from cache.

Shows percentages based on different metrics:
- median_residual_p2: < 0 = faster, >= 0 = slower
- p_value_p2: < 0.5 = faster, >= 0.5 = slower
- avg_residual_p2: < 0 = faster, >= 0 = slower
"""
import pickle
from pathlib import Path

CACHE_DIR = Path("cache/plots")
residual_files = list(CACHE_DIR.glob("*_residuals.pkl"))

# Counters for each metric
median_faster = 0
median_slower = 0
pval_faster = 0
pval_slower = 0
avg_faster = 0
avg_slower = 0
no_data_count = 0
total = 0

for pkl_file in residual_files:
    try:
        with open(pkl_file, 'rb') as f:
            data = pickle.load(f)
        
        # Check if we have P2 data
        median_residual_p2 = data.get('median_residual_p2')
        p_value_p2 = data.get('p_value_p2')
        avg_residual_p2 = data.get('avg_residual_p2')
        
        if median_residual_p2 is None and p_value_p2 is None:
            no_data_count += 1
            continue
        
        total += 1
        
        # Count by median_residual_p2
        if median_residual_p2 is not None:
            if median_residual_p2 < 0:
                median_faster += 1
            else:
                median_slower += 1
        
        # Count by p_value_p2
        if p_value_p2 is not None:
            if p_value_p2 < 0.5:
                pval_faster += 1
            else:
                pval_slower += 1
        
        # Count by avg_residual_p2
        if avg_residual_p2 is not None:
            if avg_residual_p2 < 0:
                avg_faster += 1
            else:
                avg_slower += 1
                
    except Exception as e:
        print(f"Error reading {pkl_file}: {e}")

print("=" * 60)
print("Period 2 Residual Statistics Analysis")
print("=" * 60)
print(f"\nTotal games with P2 data: {total}")
print(f"Games with no P2 data: {no_data_count}")
print()

if total > 0:
    print("By median_residual_p2:")
    print(f"  Faster 2H (median < 0): {median_faster} ({median_faster/total*100:.1f}%)")
    print(f"  Slower 2H (median >= 0): {median_slower} ({median_slower/total*100:.1f}%)")
    print()
    
    print("By p_value_p2:")
    print(f"  Faster 2H (p-value < 0.5): {pval_faster} ({pval_faster/total*100:.1f}%)")
    print(f"  Slower 2H (p-value >= 0.5): {pval_slower} ({pval_slower/total*100:.1f}%)")
    print()
    
    print("By avg_residual_p2:")
    print(f"  Faster 2H (avg < 0): {avg_faster} ({avg_faster/total*100:.1f}%)")
    print(f"  Slower 2H (avg >= 0): {avg_slower} ({avg_slower/total*100:.1f}%)")

