#!/bin/bash
# Test get_files() for duplicate filenames before attempting import.
# Issue: hatnote/montage#514
set -e
source ~/www/python/venv/bin/activate
cd ~/www/python/src
CAT="${1:-Images_from_Wiki_Loves_Monuments_2015_in_France}"
python3 - "$CAT" <<'EOF'
import sys
sys.path.insert(0, '.')
from montage.labs import get_files
cat = sys.argv[1]
print('Category:', cat)
results = get_files(cat)
print('Total rows returned:', len(results))
names = [r['img_name'] for r in results]
dupes = [n for n in names if names.count(n) > 1]
dupes_unique = sorted(set(dupes))
print('Duplicate filenames (exact):', len(dupes_unique))
if dupes_unique:
    for name in dupes_unique[:10]:
        print(' -', name)
# Case-insensitive duplicates (MariaDB utf8mb4_unicode_ci treats these as equal)
lower_names = [n.lower() for n in names]
ci_dupes = [n for n in names if lower_names.count(n.lower()) > 1]
ci_dupes_unique = sorted(set(ci_dupes))
print('Duplicate filenames (case-insensitive):', len(ci_dupes_unique))
if ci_dupes_unique:
    for name in ci_dupes_unique[:10]:
        print(' -', name)
EOF
