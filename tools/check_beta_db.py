"""
Quick verification script for PR #505 beta deployment.
Checks that file_id is populated on recently imported entries.

Usage:
    python3 tools/check_beta_db.py
"""
import sqlite3

DB = '/data/project/montage-beta/www/python/src/tmp_montage.db'
c = sqlite3.connect(DB)

total, with_file_id = c.execute('SELECT COUNT(*), COUNT(file_id) FROM entries').fetchone()
print(f'All entries  : {total} total, {with_file_id} with file_id, {total - with_file_id} NULL')

max_id = c.execute('SELECT MAX(id) FROM entries').fetchone()[0]
t, f = c.execute('SELECT COUNT(*), COUNT(file_id) FROM entries WHERE id > ?', (max_id - 5000,)).fetchone()
print(f'Last 5000    : {t} total, {f} with file_id, {t - f} NULL')

sample = c.execute('SELECT id, name, upload_user_text, file_id FROM entries ORDER BY id DESC LIMIT 5').fetchall()
print('\nMost recent entries:')
for row in sample:
    print(f'  id={row[0]}  file_id={row[3]}  uploader={row[2]}  name={row[1][:50]}')

c.close()
