"""Check residual data files"""
import pickle
from pathlib import Path

p = Path('cache/plots')
files = list(p.glob('*_residuals.pkl'))
print(f'Found {len(files)} residual files')

if files:
    d = pickle.load(open(files[0], 'rb'))
    print(f'Sample keys: {list(d.keys())[:10]}')
    print(f'Has median_residual_p2: {"median_residual_p2" in d}')
    if 'median_residual_p2' in d:
        print(f'median_residual_p2 value: {d.get("median_residual_p2")}')
    if 'note' in d:
        print(f'Note: {d.get("note")}')

