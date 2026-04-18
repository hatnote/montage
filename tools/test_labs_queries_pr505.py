"""
Standalone test script for PR #505 (migrate-image-to-filerevision).

Can be run on the CURRENT beta branch — no PR code needed, no DB migration needed.
Does NOT import from montage at all. Requires only pymysql (already on Toolforge).

Usage on Toolforge:
    python test_labs_queries_standalone.py

Tests the new file/filerevision queries against the live wikireplica and compares
them to the current image/oldimage queries to verify parity before deploying the PR.
"""

import os
import sys

try:
    import pymysql
except ImportError:
    print('ERROR: pymysql not available')
    sys.exit(1)

DB_CONFIG = os.path.expanduser('~/replica.my.cnf')
CATEGORY = 'Images_from_Wiki_Loves_Monuments_2015_in_France'
REUPLOADED_FILE = 'Albert_Einstein_Head.jpg'

PASS = '\033[92mPASS\033[0m'
FAIL = '\033[91mFAIL\033[0m'

errors = []

def check(label, condition, detail=''):
    if condition:
        print(f'  {PASS}  {label}')
    else:
        print(f'  {FAIL}  {label}' + (f': {detail}' if detail else ''))
        errors.append(label)


def query(sql, params):
    connection = pymysql.connect(
        db='commonswiki_p',
        host='commonswiki.labsdb',
        read_default_file=DB_CONFIG,
        charset='utf8',
    )
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    ret = []
    for row in rows:
        ret.append({k: (v.decode('utf8') if isinstance(v, bytes) else v)
                    for k, v in row.items()})
    connection.close()
    return ret


# ---------------------------------------------------------------------------
# New query (file/filerevision/filetypes) — mirrors PR #505 labs.py
# ---------------------------------------------------------------------------
NEW_COLS = [
    'fr.fr_width AS img_width',
    'fr.fr_height AS img_height',
    'file.file_name AS img_name',
    'ft.ft_major_mime AS img_major_mime',
    'ft.ft_minor_mime AS img_minor_mime',
    'IFNULL(oi.actor_user, ci.actor_user) AS img_user',
    'IFNULL(oi.actor_name, ci.actor_name) AS img_user_text',
    'IFNULL(oi.fr_timestamp, fr.fr_timestamp) AS img_timestamp',
    'fr.fr_timestamp AS rec_img_timestamp',
    'ci.actor_user AS rec_img_user',
    'ci.actor_name AS rec_img_text',
    'oi.fr_archive_name AS oi_archive_name',
    'file.file_id AS file_id',
]

EARLIEST_REV = '''
    LEFT JOIN (
        SELECT fr2.fr_id, fr2.fr_file, fr2.fr_timestamp, fr2.fr_archive_name,
               a.actor_user, a.actor_name
        FROM commonswiki_p.filerevision fr2
        LEFT JOIN actor a ON fr2.fr_actor = a.actor_id
        WHERE fr2.fr_id = (
            SELECT MIN(fr3.fr_id)
            FROM commonswiki_p.filerevision fr3
            WHERE fr3.fr_file = fr2.fr_file
              AND fr3.fr_deleted = 0
        )
    ) AS oi ON oi.fr_file = file.file_id
'''

NEW_CATEGORY_SQL = '''
    SELECT {cols}
    FROM commonswiki_p.file AS file
    JOIN commonswiki_p.filerevision AS fr ON fr.fr_id = file.file_latest
      AND fr.fr_deleted = 0
    LEFT JOIN actor AS ci ON fr.fr_actor = ci.actor_id
    LEFT JOIN commonswiki_p.filetypes AS ft ON file.file_type = ft.ft_id
    {earliest_rev}
    JOIN page ON page_namespace = 6
      AND page_title = file.file_name
    JOIN categorylinks ON cl_from = page_id
      AND cl_type = 'file'
    JOIN linktarget ON cl_target_id = lt_id
      AND lt_namespace = 14
      AND lt_title = %s
    WHERE file.file_deleted = 0
    ORDER BY file.file_name ASC
'''.format(cols=', '.join(NEW_COLS), earliest_rev=EARLIEST_REV)

NEW_FILE_SQL = '''
    SELECT {cols}
    FROM commonswiki_p.file AS file
    JOIN commonswiki_p.filerevision AS fr ON fr.fr_id = file.file_latest
      AND fr.fr_deleted = 0
    LEFT JOIN actor AS ci ON fr.fr_actor = ci.actor_id
    LEFT JOIN commonswiki_p.filetypes AS ft ON file.file_type = ft.ft_id
    {earliest_rev}
    WHERE file.file_name = %s
      AND file.file_deleted = 0
'''.format(cols=', '.join(NEW_COLS), earliest_rev=EARLIEST_REV)


# ---------------------------------------------------------------------------
# Old query (image/oldimage) — verbatim copy of current labs.py
# ---------------------------------------------------------------------------
OLD_CATEGORY_SQL = '''
    SELECT img_width, img_height, img_name, img_major_mime, img_minor_mime,
           IFNULL(oi.actor_user, ci.actor_user) AS img_user,
           IFNULL(oi.actor_name, ci.actor_name) AS img_user_text,
           IFNULL(oi_timestamp, img_timestamp) AS img_timestamp,
           img_timestamp AS rec_img_timestamp,
           ci.actor_user AS rec_img_user,
           ci.actor_name AS rec_img_text,
           oi.oi_archive_name AS oi_archive_name
    FROM commonswiki_p.image AS i
    LEFT JOIN actor AS ci ON img_actor = ci.actor_id
    LEFT JOIN (
        SELECT oi_name, oi_actor, actor_user, actor_name,
               oi_timestamp, oi_archive_name
        FROM oldimage
        LEFT JOIN actor ON oi_actor = actor.actor_id
    ) AS oi ON img_name = oi.oi_name
    JOIN page ON page_namespace = 6 AND page_title = img_name
    JOIN categorylinks ON cl_from = page_id
      AND cl_type = 'file'
    JOIN linktarget ON cl_target_id = lt_id
      AND lt_namespace = 14
      AND lt_title = %s
    GROUP BY img_name
    ORDER BY oi_timestamp ASC
'''


# ---------------------------------------------------------------------------
# Test 1: parity
# ---------------------------------------------------------------------------
print(f'\n[1] Parity: {CATEGORY}')
new_rows = query(NEW_CATEGORY_SQL, (CATEGORY.replace(' ', '_'),))
old_rows = query(OLD_CATEGORY_SQL, (CATEGORY.replace(' ', '_'),))
new_names = {r['img_name'] for r in new_rows}
old_names = {r['img_name'] for r in old_rows}
only_new = new_names - old_names
only_old = old_names - new_names
print(f'    New query : {len(new_names)} files')
print(f'    Old query : {len(old_names)} files')
check('Same file count', len(new_names) == len(old_names),
      f'only_in_new={only_new}, only_in_old={only_old}')
check('No files only in new', not only_new, str(only_new))
check('No files only in old', not only_old, str(only_old))


# ---------------------------------------------------------------------------
# Test 2: required keys present
# ---------------------------------------------------------------------------
print(f'\n[2] Result row shape')
required_keys = ['img_name', 'img_major_mime', 'img_minor_mime', 'img_width',
                 'img_height', 'img_user', 'img_user_text', 'img_timestamp',
                 'rec_img_timestamp', 'rec_img_user', 'rec_img_text',
                 'oi_archive_name', 'file_id']
if new_rows:
    for key in required_keys:
        check(f'Key present: {key}', key in new_rows[0])
else:
    print('  SKIP  (no results)')


# ---------------------------------------------------------------------------
# Test 3: file_id populated
# ---------------------------------------------------------------------------
print(f'\n[3] file_id populated')
if new_rows:
    with_id = [r for r in new_rows if r.get('file_id') is not None]
    check('At least one row has file_id', len(with_id) > 0)
    check('All rows have file_id', len(with_id) == len(new_rows),
          f'{len(new_rows) - len(with_id)} missing')


# ---------------------------------------------------------------------------
# Test 4: attribution on a known reuploaded file
# ---------------------------------------------------------------------------
print(f'\n[4] Attribution: {REUPLOADED_FILE}')
rows = query(NEW_FILE_SQL, (REUPLOADED_FILE.replace(' ', '_'),))
check('get_file_info returns a result', len(rows) == 1)
if rows:
    info = rows[0]
    check('img_user_text (original uploader) set', bool(info.get('img_user_text')))
    check('rec_img_text (latest uploader) set', bool(info.get('rec_img_text')))
    check('Original and latest uploader differ',
          info.get('img_user_text') != info.get('rec_img_text'),
          f'both = {repr(info.get("img_user_text"))}')
    check('oi_archive_name truthy', bool(info.get('oi_archive_name')),
          repr(info.get('oi_archive_name')))
    check('file_id set', info.get('file_id') is not None)
    print(f'    Original uploader : {info.get("img_user_text")}')
    print(f'    Latest uploader   : {info.get("rec_img_text")}')
    print(f'    file_id           : {info.get("file_id")}')


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
if errors:
    print(f'FAILED — {len(errors)} check(s):')
    for e in errors:
        print(f'  - {e}')
    sys.exit(1)
else:
    print('All checks passed.')
