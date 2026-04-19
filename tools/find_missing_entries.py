#!/usr/bin/env python3
"""Find which files from get_files() are missing from the entries table.

Run on beta with:
  python3 tools/find_missing_entries.py [category_name]
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from montage.labs import get_files
from montage.utils import load_env_config
from sqlalchemy import create_engine, text

cat = sys.argv[1] if len(sys.argv) > 1 else 'Images_from_Wiki_Loves_Monuments_2015_in_France'
print('Category:', cat)

# --- get filenames from wikireplica ---
files = get_files(cat)
replica_names = set(r['img_name'] for r in files)
print('get_files() count:', len(replica_names))

# --- get filenames from entries table ---
config = load_env_config()
db_url = config['db_url']
engine = create_engine(db_url)
with engine.connect() as conn:
    result = conn.execute(text('SELECT name FROM entries'))
    db_names = set(row[0] for row in result)
print('entries table count:', len(db_names))

# --- compare ---
only_replica = replica_names - db_names
only_db = db_names - replica_names

print('In get_files() but NOT in entries table:', len(only_replica))
print('In entries table but NOT in get_files():', len(only_db))

if only_replica:
    sample = sorted(only_replica)[:10]
    print('\nSample of missing files (first 10):')
    for name in sample:
        print(' ', name)

    # Check if they might be in the DB under a different case
    print('\nChecking case-insensitive matches in DB...')
    db_names_lower = {n.lower(): n for n in db_names}
    ci_matches = 0
    truly_missing = []
    for name in sorted(only_replica):
        if name.lower() in db_names_lower:
            ci_matches += 1
        else:
            truly_missing.append(name)
    print('  Have case-insensitive match in DB:', ci_matches)
    print('  Truly absent (no case match):', len(truly_missing))
    if truly_missing:
        print('\nSample of truly absent files (first 10):')
        for name in truly_missing[:10]:
            # look up this file's metadata in the replica results
            for r in files:
                if r['img_name'] == name:
                    print('  name=%s  user=%s  width=%s  height=%s  mime=%s/%s' % (
                        name, r.get('img_user_text'), r.get('img_width'),
                        r.get('img_height'), r.get('img_major_mime'), r.get('img_minor_mime')))
                    break
