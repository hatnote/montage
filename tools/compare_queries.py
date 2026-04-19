#!/usr/bin/env python3
"""Compare file counts from new (file/filerevision) vs legacy (image/oldimage) query."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from montage.labs import get_files, get_files_legacy

cat = sys.argv[1] if len(sys.argv) > 1 else 'Images_from_Wiki_Loves_Monuments_2015_in_France'
print('Category:', cat)

new = get_files(cat)
new_names = set(r['img_name'] for r in new)
print('New query (file/filerevision):', len(new))

legacy = get_files_legacy(cat)
legacy_names = set(r['img_name'] for r in legacy)
print('Legacy query (image/oldimage) :', len(legacy))

only_new = new_names - legacy_names
only_legacy = legacy_names - new_names
print('Only in new query            :', len(only_new))
print('Only in legacy query         :', len(only_legacy))
if only_new:
    print('Examples only in new:', list(only_new)[:5])
if only_legacy:
    print('Examples only in legacy:', list(only_legacy)[:5])
