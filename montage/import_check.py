# -*- coding: utf-8 -*-
"""Checked imports (hatnote/montage#510).

Every first-round import source (CSV / gist / Google Sheet link, file
list, category) is first *checked*: fetched, looked up on Commons (by
file_id where a row has one, else by name) and classified row by row. The
result is kept as a JSON file under a random token; the import then reads
exactly that list, without fetching the source or asking Commons again.

Row statuses:

  ok                 found on Commons, imported
  renamed            found by file_id under another name: imported under
                     Commons' current name (information)
  duplicate          the same Commons file as an earlier row: imported once
  unknown_name       no file_id and the name is not on Commons: left out,
                     warning
  unknown_file_id    the file_id is not on Commons: blocks
  malformed_file_id  the file_id is not a plain whole number: blocks
  page_id            a bare number (no name) that is a File: page's page ID,
                     not a file_id: blocks
  revision_id        a bare number that is a revision ID of a File: page: blocks
  ambiguous_id       a bare number that is one file's file_id and another
                     File: page's page or revision ID: blocks
  same_name          a different Commons file whose name the database treats
                     as equal to another's (utf8mb4_unicode_ci): blocks a
                     list import (CSV, gist, Sheet, file list); in a category
                     the first file is kept and the others left out
  same_name_existing a file whose name the database treats as equal to that
                     of another file already in Montage, where entries.name
                     has a unique index (beta, fresh installs; production
                     has none, #650): blocks a list import; left out of a
                     category

The check file holds the campaign id, the source, each row as written and
Commons' data per file (including Commons uploader names); no Montage user.
"""
from __future__ import absolute_import

import os
import re
import csv
import json
import hashlib
import secrets
import datetime
import tempfile
import unicodedata
from io import StringIO
from collections import Counter

from sqlalchemy import text

from .loaders import (fetch_source_text, parse_source_rows, parse_name_list,
                      pasted_csv_text,
                      lookup_by_names, lookup_by_ids, lookup_other_ids,
                      category_records,
                      guard_cell)
from .utils import (PROJ_PATH, get_env_name, ImportSourceInvalid,
                    ImportCheckBlocked, ImportCheckExpired)

FORMAT = 1

CHECKED_METHODS = ('csv', 'gistcsv', 'category', 'selected')
LIST_METHODS = ('csv', 'gistcsv', 'selected')  # same-name pairs block these

BLOCKING_STATUSES = ('unknown_file_id', 'malformed_file_id', 'page_id',
                     'revision_id', 'ambiguous_id', 'same_name',
                     'same_name_existing')
IMPORTED_STATUSES = ('ok', 'renamed')
ALL_STATUSES = ('ok', 'renamed', 'duplicate', 'unknown_name',
                'unknown_file_id', 'malformed_file_id', 'page_id', 'revision_id',
                'ambiguous_id', 'same_name', 'same_name_existing')

# A check can be imported for an hour: files are renamed and deleted on
# Commons all the time, and the check and the save happen in one sitting.
CHECK_VALID_FOR = datetime.timedelta(hours=1)
# A check file is deleted after at most this long; until then its downloads
# (upload file, issues report) work. Every use of the folder cleans up.
CHECK_FILE_MAX_AGE = datetime.timedelta(days=7)
ISSUES_SHOWN = 1000       # non-ok rows in the check response; the file has all
BLOCKING_ROWS_SHOWN = 10  # rows named in a "blocked" error
WARNING_ROWS_SHOWN = 50   # rows named per import warning

# The same-name check (one switch). Two different files whose names the
# database compares as equal cannot both be stored where entries.name has a
# unique index (#645), and are easily confused by everyone else.
SAME_NAME_CHECK = True
SAME_NAME_COLLATION = 'utf8mb4_unicode_ci'  # entries.name's collation
SAME_NAME_CHUNK_SIZE = 500

ENV_NAME = get_env_name()
DEFAULT_CHECK_DIR = os.path.join(PROJ_PATH, 'tmp', 'import_checks')
# Only local development may use the default folder inside the checkout;
# everywhere else the folder must be configured, on storage that all pods
# (and the import worker) share.
DEFAULT_CHECK_DIR_ENVS = ('dev', 'devtest')
DEPLOYED_ENVS = ('beta', 'prod', 'devlabs')
MAX_CHECK_FILES = 5000  # oldest check files beyond this are deleted

_TOKEN_RE = re.compile(r'^[A-Za-z0-9_-]{32}$')
# the only files Montage writes in the folder (and may delete)
_CHECK_FILE_RE = re.compile(r'^(?:[A-Za-z0-9_-]{32}|\.tmp-.+)\.json$')


def lookup_source():
    """Where Commons is looked up: the wikireplica, except in local dev,
    which asks production's public utils endpoint (as rdb.py does)."""
    return 'remote' if ENV_NAME == 'dev' else 'local'


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def _iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%SZ')


def _parse_iso(value):
    dt = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ')
    return dt.replace(tzinfo=datetime.timezone.utc)


# ---------------------------------------------------------------------------
# The check
# ---------------------------------------------------------------------------

def run_check(request_dict, campaign_id, source='local', rdb_session=None,
              now=None):
    """Fetch, look up and classify an import source; returns the check
    result (a JSON-serialisable dict). Writes nothing."""
    request_dict = request_dict or {}
    import_method = request_dict.get('import_method')
    if import_method not in CHECKED_METHODS:
        raise ImportSourceInvalid('cannot check import method %r' % (import_method,))
    columns = {'name': None, 'file_id': None, 'ignored': []}
    if import_method in ('csv', 'gistcsv'):
        if import_method == 'gistcsv':
            url = request_dict.get('gist_url') or request_dict.get('csv_url')
        else:
            url = request_dict.get('csv_url')
        rows, columns = parse_source_rows(fetch_source_text(url))
        source_info = {'csv_url': url}
        rows = _classify_list(rows, source)
    elif import_method == 'selected':
        file_names = request_dict.get('file_names')
        pasted_csv = pasted_csv_text(file_names)
        if pasted_csv is not None:  # e.g. the check's download, pasted
            rows, columns = parse_source_rows(pasted_csv)
            source_info = {'file_names': pasted_csv.splitlines()}
        else:
            rows = parse_name_list(file_names)
            source_info = {'file_names': [r['name_as_written'] for r in rows]}
        rows = _classify_list(rows, source)
    else:
        category = request_dict.get('category')
        records = category_records(category, source)
        source_info = {'category': category}
        rows = [_row({'row': i + 1, 'name_as_written': rec['img_name'],
                      'file_id_as_written': ''}, 'ok', rec=rec)
                for i, rec in enumerate(records)]
    _mark_duplicates(rows)
    if SAME_NAME_CHECK:
        _mark_same_names(rows, import_method, rdb_session)
        if rdb_session is not None and _name_must_be_unique(rdb_session):
            _mark_names_taken(rows, import_method, rdb_session)
    now = now or _utcnow()
    return {'format': FORMAT,
            'checked_at': _iso(now),
            'campaign_id': campaign_id,
            'import_method': import_method,
            'source': source_info,
            'lookup': source,
            'columns': columns,
            'rows': rows}


def _row(src, status, rec=None, reason='', file_id=None, code=None, params=()):
    """One checked row. `reason` is English (API users, logs); `reason_code`
    and `reason_params` let the frontend show it translated
    (montage-round-check-reason-<code> with the params)."""
    commons_name = rec['img_name'] if rec else None
    if rec and rec.get('file_id') is not None:
        file_id = int(rec['file_id'])
    return {'row': src['row'],
            'name_as_written': src['name_as_written'],
            'file_id_as_written': src['file_id_as_written'],
            'commons_name': commons_name,
            'file_id': file_id,
            'status': status,
            'reason': reason,
            'reason_code': code,
            'reason_params': [str(p) for p in params],
            'group': None,
            'commons': rec}


def _classify_list(rows, source):
    """Statuses of a CSV / file list's rows, looked up on Commons."""
    ids = [r['file_id'] for r in rows if r['file_id'] is not None]
    by_id = lookup_by_ids(ids) if ids and source != 'remote' else {}
    # dev (remote): the public utils endpoint has no lookup by file_id, so
    # rows with a file_id are looked up by name and their ids compared
    names = [r['name'] for r in rows
             if r['name'] and not r['malformed_file_id']
             and (r['file_id'] is None or source == 'remote')]
    by_name = lookup_by_names(names, source)
    # a bare number (no name) may be a page ID or revision ID someone found
    # on Commons; nothing confirms it is a file_id
    bare = [r['file_id'] for r in rows if r['file_id'] is not None and not r['name']]
    others = lookup_other_ids(bare) if bare and source != 'remote' else {}

    ret = []
    for r in rows:
        other = others.get(r['file_id']) if not r['name'] else None
        rec = by_id.get(r['file_id']) if other else None
        if other and (rec is None or rec['img_name'] != other['name']):
            ret.append(_other_id_row(r, other, rec))
        elif r['malformed_file_id']:
            cell = r['file_id_as_written'].strip()
            ret.append(_row(r, 'malformed_file_id',
                            reason='"%s" is not a file ID: a file ID is a whole'
                            ' number, without dots, commas or E+' % cell,
                            code='malformed-file-id', params=[cell]))
        elif r['file_id'] is not None and source == 'remote':
            rec = by_name.get(r['name'])
            if rec and rec.get('file_id') is not None and int(rec['file_id']) == r['file_id']:
                ret.append(_row(r, 'ok', rec=rec))
            else:
                ret.append(_row(r, 'unknown_file_id', file_id=r['file_id'],
                                reason='dev: compared by name only; file ID %s'
                                ' not confirmed' % r['file_id'],
                                code='dev-name-only', params=[r['file_id']]))
        elif r['file_id'] is not None:
            rec = by_id.get(r['file_id'])
            if rec is None:
                ret.append(_row(r, 'unknown_file_id', file_id=r['file_id'],
                                reason='no file on Commons has file ID %s (deleted,'
                                ' or a wrong number)' % r['file_id'],
                                code='unknown-file-id', params=[r['file_id']]))
            elif not r['name']:
                ret.append(_row(r, 'ok', rec=rec,
                                reason='no name given; Commons name used',
                                code='name-from-commons', params=[rec['img_name']]))
            elif rec['img_name'] == r['name']:
                ret.append(_row(r, 'ok', rec=rec))
            else:
                ret.append(_row(r, 'renamed', rec=rec,
                                reason=u'renamed on Commons: %s → %s'
                                % (r['name'], rec['img_name']),
                                code='renamed', params=[r['name'], rec['img_name']]))
        else:
            rec = by_name.get(r['name'])
            if rec is not None:
                ret.append(_row(r, 'ok', rec=rec))
            else:
                ret.append(_row(r, 'unknown_name',
                                reason='"%s" is not on Commons: check the'
                                ' spelling (renamed or deleted?)' % r['name'],
                                code='unknown-name', params=[r['name']]))
    return ret


_ID_KINDS = {'page_id': 'the page ID', 'revision_id': 'a revision ID'}


def _other_id_row(r, other, rec):
    """A bare number that is a File: page's page ID or revision ID."""
    num, page = r['file_id'], 'File:' + other['name']
    if rec is not None:
        return _row(r, 'ambiguous_id', file_id=num,
                    reason='%s is the file ID of %s but also %s of %s; write'
                    ' the file name instead, so it is clear which file is meant'
                    % (num, rec['img_name'], _ID_KINDS[other['kind']], page),
                    code='ambiguous-id', params=[num, rec['img_name'], other['name']])
    if other['kind'] == 'revision_id':
        reason = ('%s is a revision ID (one edit of the page %s), not a file ID;'
                  ' write the file name instead: %s' % (num, page, other['name']))
    else:
        reason = ('%s is the page ID of %s, not a file ID; write the file name'
                  ' instead: %s' % (num, page, other['name']))
    return _row(r, other['kind'], file_id=num, reason=reason,
                code=other['kind'].replace('_', '-'), params=[num, other['name']])


def _file_key(row):
    if row['file_id'] is not None:
        return ('file_id', row['file_id'])
    return ('name', row['commons_name'])


def _mark_duplicates(rows):
    """The same Commons file listed twice (same name, or an old name and
    its file_id): imported once, from its first row."""
    first_row = {}
    for r in rows:
        if r['status'] not in IMPORTED_STATUSES:
            continue
        key = _file_key(r)
        if key in first_row:
            r['status'] = 'duplicate'
            r['reason'] = 'the same file as row %s; imported once' % first_row[key]
            r['reason_code'] = 'duplicate'
            r['reason_params'] = [str(first_row[key])]
            r['commons'] = None
        else:
            first_row[key] = r['row']


def _mark_same_names(rows, import_method, rdb_session):
    candidates = [r for r in rows if r['status'] in IMPORTED_STATUSES]
    keys = same_name_keys([r['commons_name'] for r in candidates], rdb_session)
    groups = {}
    for r in candidates:
        groups.setdefault(keys[r['commons_name']], []).append(r)
    group_id = 0
    for members in groups.values():
        if len(members) < 2:
            continue
        group_id += 1
        if import_method in LIST_METHODS:
            for r in members:
                others = [m for m in members if m is not r]
                r['status'] = 'same_name'
                r['group'] = group_id
                r['reason'] = ('Montage cannot tell this name apart from: %s'
                               % ', '.join('%s (row %s)' % (m['commons_name'], m['row'])
                                           for m in others))
                # params: name, row, name, row, ... of the other files
                r['reason_code'] = 'same-name'
                r['reason_params'] = [str(v) for m in others
                                      for v in (m['commons_name'], m['row'])]
                r['commons'] = None
        else:
            # category: keep the first in binary name order, as before
            members.sort(key=lambda m: m['commons_name'].encode('utf8'))
            kept = members[0]
            kept['group'] = group_id
            for r in members[1:]:
                r['status'] = 'same_name'
                r['group'] = group_id
                r['reason'] = ('left out: Montage cannot tell this name apart'
                               ' from %s, which is imported' % kept['commons_name'])
                r['reason_code'] = 'same-name-category'
                r['reason_params'] = [kept['commons_name']]
                r['commons'] = None


def _name_must_be_unique(rdb_session):
    """True where entries.name has a unique index: there a name the
    database treats as equal to an existing row's cannot be stored."""
    from .rdb import entries_name_is_unique
    return entries_name_is_unique(rdb_session)


def _existing_entries(rdb_session, names):
    """(name, file_id) of the entries rows the database matches for these
    names, by its own comparison (utf8mb4_unicode_ci on MariaDB: case,
    accents, е/ё); uses the unique index on entries.name."""
    from .rdb import Entry
    ret = []
    names = sorted(set(names))
    for i in range(0, len(names), SAME_NAME_CHUNK_SIZE):
        chunk = names[i:i + SAME_NAME_CHUNK_SIZE]
        ret.extend(rdb_session.query(Entry.name, Entry.file_id)
                   .filter(Entry.name.in_(chunk)).all())
    return [(name, file_id) for name, file_id in ret]


def _mark_names_taken(rows, import_method, rdb_session):
    """Rows whose name the database treats as equal to that of another file
    already in Montage (#510; beta, 2026-10-10). The same file (same
    file_id) is reused by the import, and so is an old row of exactly this
    name without a file_id (rdb._add_entries_by_file_id); anything else
    would fail on the unique index."""
    candidates = [r for r in rows if r['status'] in IMPORTED_STATUSES]
    if not candidates:
        return
    existing = _existing_entries(rdb_session, [r['commons_name'] for r in candidates])
    if not existing:
        return
    keys = same_name_keys([r['commons_name'] for r in candidates]
                          + [name for name, _ in existing], rdb_session)
    by_key = {}
    for name, file_id in existing:
        by_key.setdefault(keys[name], []).append((name, file_id))
    for r in candidates:
        matches = by_key.get(keys[r['commons_name']], [])
        if any(file_id == r['file_id']
               or (file_id is None and name == r['commons_name'])
               for name, file_id in matches):
            continue  # reused by the import
        if not matches:
            continue
        taken = matches[0][0]
        r['status'] = 'same_name_existing'
        r['commons'] = None
        if import_method in LIST_METHODS:
            r['reason'] = ('Montage already has a different file named %s and'
                           ' cannot tell the two names apart; remove this row'
                           % taken)
            r['reason_code'] = 'same-name-existing'
        else:
            r['reason'] = ('left out: Montage already has a different file named'
                           ' %s and cannot tell the two names apart' % taken)
            r['reason_code'] = 'same-name-existing-category'
        r['reason_params'] = [taken]


def same_name_keys(names, rdb_session=None):
    """{name: comparison key}: two names with equal keys are the same name
    for Montage's database (entries.name, utf8mb4_unicode_ci).

    On MariaDB/MySQL the database computes the keys itself with
    WEIGHT_STRING, so they are exactly its comparison (no table is read).
    Anywhere else (SQLite in tests and local dev) a Python approximation is
    used, for tests only: it folds case and drops accents, so е/ё and й/и
    compare equal as in utf8mb4_unicode_ci, but ß/ss, æ/ae and other
    expansions do not."""
    names = sorted(set(names))
    if not names:
        return {}
    dialect = rdb_session.get_bind().dialect.name if rdb_session is not None else None
    if dialect in ('mysql', 'mariadb'):
        return _database_keys(rdb_session, names)
    if ENV_NAME in DEPLOYED_ENVS:
        raise RuntimeError('the same-name check needs the MariaDB session on %s'
                           ' (got %r)' % (ENV_NAME, dialect))
    if dialect not in (None, 'sqlite'):
        raise RuntimeError('no same-name comparison for database %r' % (dialect,))
    return {name: _test_only_approximate_key(name) for name in names}


def _database_keys(rdb_session, names):
    ret = {}
    for i in range(0, len(names), SAME_NAME_CHUNK_SIZE):
        chunk = names[i:i + SAME_NAME_CHUNK_SIZE]
        cols = ', '.join('WEIGHT_STRING(CONVERT(:n%d USING utf8mb4) COLLATE %s) AS w%d'
                         % (j, SAME_NAME_COLLATION, j) for j in range(len(chunk)))
        params = {'n%d' % j: name for j, name in enumerate(chunk)}
        row = rdb_session.execute(text('SELECT ' + cols), params).fetchone()
        if row is None or any(cell is None for cell in row):
            raise RuntimeError('the database returned no comparison key for a name')
        for j, name in enumerate(chunk):
            ret[name] = bytes(row[j])
    return ret


def _test_only_approximate_key(name):
    """TEST-ONLY stand-in for the database's utf8mb4_unicode_ci comparison
    (SQLite has none). Never used against MariaDB."""
    decomposed = unicodedata.normalize('NFKD', name)
    stripped = u''.join(c for c in decomposed if not unicodedata.combining(c))
    return stripped.lower()


# ---------------------------------------------------------------------------
# Reading a check result
# ---------------------------------------------------------------------------

def counts(result):
    found = Counter(r['status'] for r in result['rows'])
    return {status: found.get(status, 0) for status in ALL_STATUSES}


def blocking_rows(result):
    """Rows that block the import, recomputed from the rows."""
    if result['import_method'] not in LIST_METHODS:
        return []
    return [r for r in result['rows'] if r['status'] in BLOCKING_STATUSES]


def importable(result):
    return [r for r in result['rows']
            if r['status'] in IMPORTED_STATUSES and r['commons'] is not None]


def raise_if_blocked(result):
    blocked = blocking_rows(result)
    if not blocked:
        return
    detail = ('%s %s the import. Fix the source, then check the source again.'
              % (len(blocked), 'row blocks' if len(blocked) == 1 else 'rows block'))
    lines = ['row %s: %s' % (r['row'], r['reason']) for r in blocked[:BLOCKING_ROWS_SHOWN]]
    if len(blocked) > BLOCKING_ROWS_SHOWN:
        lines.append('... and %s more' % (len(blocked) - BLOCKING_ROWS_SHOWN))
    raise ImportCheckBlocked(detail + '\n' + '\n'.join(lines))


def _listed(lines):
    shown = [u'- ' + line for line in lines[:WARNING_ROWS_SHOWN]]
    if len(lines) > WARNING_ROWS_SHOWN:
        shown.append(u'- ... and %s more' % (len(lines) - WARNING_ROWS_SHOWN))
    return u'\n'.join(shown)


def _files(n):
    return '1 file' if n == 1 else '%s files' % n


def import_warnings(result):
    """Warnings for the import response: a list of one-key dicts, like
    the other import warnings. (The round form shows the check's rows,
    translated, instead.)"""
    ret = []
    rows = result['rows']
    unknown = [r['reason'] for r in rows if r['status'] == 'unknown_name']
    if unknown:
        ret.append({'import issues': u'%s not on Commons, left out:\n%s'
                    % (_files(len(unknown)), _listed(unknown))})
    renamed = [r['reason'] for r in rows if r['status'] == 'renamed']
    if renamed:
        ret.append({'renamed': u'%s imported under their current name on'
                    u' Commons:\n%s' % (_files(len(renamed)), _listed(renamed))})
    left_out = [u'%s (%s)' % (r['commons_name'] or r['name_as_written'], r['reason'])
                for r in rows if r['status'] in ('same_name', 'same_name_existing')]
    if left_out:
        ret.append({'same name': u'%s left out:\n%s'
                    % (_files(len(left_out)), _listed(left_out))})
    return ret


def source_params(result, token=None):
    """round_sources.params for the import, from the check (not from the
    import request), with a fingerprint of the check: the token itself is
    not stored, because round sources are shown on public pages."""
    params = dict(result['source'])
    if token:
        params[CHECK_ID_KEY] = check_fingerprint(token)
    return params


CHECK_ID_KEY = 'check_id'


def check_fingerprint(token):
    return hashlib.sha256(token.encode('ascii')).hexdigest()[:12]


def describe_source(result):
    src = result['source']
    if 'category' in src:
        return 'category (%s)' % src['category']
    if 'csv_url' in src:
        return 'csv (%r)' % src['csv_url']
    return 'file list (%s names)' % len(src.get('file_names', []))


def summarize(result, token):
    """The check endpoint's response."""
    issues = [{k: v for k, v in r.items() if k != 'commons'}
              for r in result['rows'] if r['status'] != 'ok']
    groups = {}
    for r in result['rows']:
        if r['group'] is not None:
            groups.setdefault(r['group'], []).append(
                {'row': r['row'], 'name_as_written': r['name_as_written'],
                 'commons_name': r['commons_name'], 'file_id': r['file_id'],
                 'status': r['status']})
    checked_at = _parse_iso(result['checked_at'])
    return {'token': token,
            'checked_at': result['checked_at'],
            'expires_at': _iso(checked_at + CHECK_VALID_FOR),
            'import_method': result['import_method'],
            'source': result['source'],
            'columns': result['columns'],
            'counts': counts(result),
            'blocking': bool(blocking_rows(result)),
            'total_rows': len(result['rows']),
            'importable_count': len(importable(result)),
            'issues': issues[:ISSUES_SHOWN],
            'issues_total': len(issues),
            'issues_truncated': len(issues) > ISSUES_SHOWN,
            'same_name_groups': [groups[k] for k in sorted(groups)]}


def upload_csv(result):
    """The download: a ready-to-use upload file with the columns filename
    (Commons' current name) and file_id, one row per file the import would
    take. Uploading it again passes the check unchanged. Cells that a
    spreadsheet would run as a formula get a leading ' (removed again when
    Montage reads the file)."""
    out = StringIO()
    writer = csv.writer(out, lineterminator='\n')
    writer.writerow(['filename', 'file_id'])
    for r in importable(result):
        writer.writerow([guard_cell(r['commons_name']),
                         '' if r['file_id'] is None else r['file_id']])
    return out.getvalue().encode('utf8')


ISSUES_COLUMNS = ['row', 'name', 'file_id', 'commons_name', 'status', 'reason']


def issues_csv(result):
    """Every row that is not ok, as a report (the upload file leaves them
    out, and the form shows at most ISSUES_SHOWN)."""
    out = StringIO()
    writer = csv.writer(out, lineterminator='\n')
    writer.writerow(ISSUES_COLUMNS)
    for r in result['rows']:
        if r['status'] == 'ok':
            continue
        writer.writerow([r['row'], guard_cell(r['name_as_written']),
                         guard_cell(r['file_id_as_written']),
                         guard_cell(r['commons_name'] or ''), r['status'],
                         guard_cell(r['reason'])])
    return out.getvalue().encode('utf8')


# ---------------------------------------------------------------------------
# Check files
# ---------------------------------------------------------------------------

def check_dir(config):
    return ((config or {}).get('import_check_path')
            or os.environ.get('MONTAGE_IMPORT_CHECK_PATH')
            or DEFAULT_CHECK_DIR)


def check_dir_problem(config, env_name):
    """Why the app must not start, or None. The folder must be configured
    outside local development, absolute, writable, and Montage's own: the
    cleanup deletes old check files in it."""
    configured = ((config or {}).get('import_check_path')
                  or os.environ.get('MONTAGE_IMPORT_CHECK_PATH'))
    if not configured:
        if env_name in DEFAULT_CHECK_DIR_ENVS:
            return None
        return ('MONTAGE_IMPORT_CHECK_PATH is not set: env %r needs a folder for'
                ' import checks that all pods share, e.g.'
                ' /data/project/<tool>/import_checks' % env_name)
    if not os.path.isabs(configured):
        return 'MONTAGE_IMPORT_CHECK_PATH %r must be an absolute path' % configured
    if os.path.isdir(configured):
        if not os.access(configured, os.W_OK | os.X_OK):
            return 'MONTAGE_IMPORT_CHECK_PATH %r is not writable' % configured
        others = [n for n in os.listdir(configured) if not _CHECK_FILE_RE.match(n)]
        if others:
            return ('MONTAGE_IMPORT_CHECK_PATH %r contains other files (%s): use a'
                    ' folder of its own, e.g. .../import_checks'
                    % (configured, ', '.join(sorted(others)[:3])))
        return None
    parent = os.path.dirname(configured.rstrip(os.sep))
    if not (os.path.isdir(parent) and os.access(parent, os.W_OK | os.X_OK)):
        return ('MONTAGE_IMPORT_CHECK_PATH %r does not exist and cannot be created'
                % configured)
    return None


def check_dir_warning(config, env_name):
    """A note for the startup log, or None."""
    folder = check_dir(config)
    if env_name in DEPLOYED_ENVS and not folder.startswith('/data/project/'):
        return ('import check folder %s is not under /data/project/: other pods and'
                ' a restarted pod will not see its files' % folder)
    return None


def _check_files(folder):
    return [n for n in os.listdir(folder) if _CHECK_FILE_RE.match(n)]


def _cleanup(folder, now):
    """Delete check files older than CHECK_FILE_MAX_AGE, and the oldest beyond
    MAX_CHECK_FILES. Nothing else in the folder is touched."""
    cutoff = (now - CHECK_FILE_MAX_AGE).timestamp()
    kept = []
    for name in _check_files(folder):
        path = os.path.join(folder, name)
        try:
            mtime = os.path.getmtime(path)
            if mtime < cutoff:
                os.remove(path)
            elif _TOKEN_RE.match(name[:-5]):
                kept.append((mtime, path))
        except FileNotFoundError:  # another process cleaned up first
            pass
    kept.sort()
    for _, path in kept[:max(0, len(kept) - MAX_CHECK_FILES + 1)]:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def _ensure_folder(folder):
    """Create the folder (mode 0700) if it is missing; an existing folder
    keeps its mode."""
    if os.path.isdir(folder):
        return
    os.makedirs(os.path.dirname(folder.rstrip(os.sep)) or '.', exist_ok=True)
    try:
        os.mkdir(folder, 0o700)
        os.chmod(folder, 0o700)  # mkdir's mode is filtered by the umask
    except FileExistsError:  # created by another process meanwhile
        pass


def cleanup(config, now=None):
    """Clean up the check folder (see _cleanup), if it exists. Runs on
    every check, import and download, and when the app starts."""
    folder = check_dir(config)
    if os.path.isdir(folder):
        _cleanup(folder, now or _utcnow())


def _age_text(age):
    hours = int(age.total_seconds() // 3600)
    if hours % 24 == 0:
        return '%s days' % (hours // 24) if hours != 24 else '1 day'
    return '%s hours' % hours if hours != 1 else '1 hour'


def save(result, config, now=None):
    """Write the check result to a new check file; returns its token.
    Deletes old check files first (see _cleanup)."""
    folder = check_dir(config)
    _ensure_folder(folder)
    _cleanup(folder, now or _utcnow())
    token = secrets.token_urlsafe(24)
    fd, tmp_path = tempfile.mkstemp(dir=folder, prefix='.tmp-', suffix='.json')
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(result, f, separators=(',', ':'), ensure_ascii=False,
                      default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, os.path.join(folder, token + '.json'))
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise
    return token


def _method_family(import_method):
    return 'csv' if import_method in ('csv', 'gistcsv') else import_method


def load(token, config, campaign_id, import_method=None, now=None,
         max_age=CHECK_VALID_FOR):
    """The check result for a token, if it exists, is younger than max_age
    (an import: CHECK_VALID_FOR; a download: CHECK_FILE_MAX_AGE) and was
    made for this campaign (and import method)."""
    now = now or _utcnow()
    cleanup(config, now)
    expired = 'check not found or expired, please check the source again'
    if not isinstance(token, str) or not _TOKEN_RE.match(token):
        raise ImportCheckExpired(expired)
    folder = os.path.realpath(check_dir(config))
    path = os.path.realpath(os.path.join(folder, token + '.json'))
    if not path.startswith(folder + os.sep):
        raise ImportCheckExpired(expired)
    try:
        with open(path, encoding='utf-8') as f:
            result = json.load(f)
        checked_at = _parse_iso(result['checked_at'])
    except (OSError, ValueError, KeyError, TypeError):
        raise ImportCheckExpired(expired)
    if result.get('format') != FORMAT:
        raise ImportCheckExpired(expired)
    if now - checked_at > max_age:
        raise ImportCheckExpired('check expired (older than %s), please check'
                                 ' the source again' % _age_text(max_age))
    if result.get('campaign_id') != campaign_id:
        raise ImportCheckExpired('this check was made for another campaign,'
                                 ' please check the source again')
    if import_method and _method_family(result.get('import_method')) != _method_family(import_method):
        raise ImportCheckExpired('this check was made for another import'
                                 ' source, please check the source again')
    return result
