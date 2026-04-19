#!/usr/bin/env python3
"""Check MIME type breakdown of files returned by get_files()."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from montage.labs import get_files
from collections import Counter

cat = sys.argv[1] if len(sys.argv) > 1 else 'Images_from_Wiki_Loves_Monuments_2015_in_France'
print('Category:', cat)
r = get_files(cat)
print('Total files:', len(r))
c = Counter((x.get('img_major_mime'), x.get('img_minor_mime')) for x in r)
print('\nMIME type breakdown:')
for (maj, mn), n in sorted(c.items(), key=lambda x: -x[1])[:15]:
    print('  %5d  %s/%s' % (n, maj, mn))
