
from __future__ import absolute_import
import datetime

from io import StringIO
import csv
import json
import re

import requests
from boltons.iterutils import chunked_iter

import montage.rdb  # TODO: circular import
from .labs import get_files, get_files_info_by_names, get_files_info_by_ids
from .utils import (ImportSourceInvalid, to_unicode, requests_get,
                    requests_post)

REMOTE_UTILS_URL = 'https://montage.toolforge.org/v1/utils/'

GSHEET_URL = 'https://docs.google.com/spreadsheets/d/%s/gviz/tq?tqx=out:csv'

# seconds; a source link is fetched within the 30 s request limit
SOURCE_FETCH_TIMEOUT = 15


def wpts2dt(timestamp):
    wpts_format = '%Y%m%d%H%M%S'
    try:
        ret = datetime.datetime.strptime(timestamp, wpts_format)
    except ValueError as e:
        wpts_format = '%Y-%m-%dT%H:%M:%S'  # based on output format
        ret = datetime.datetime.strptime(timestamp, wpts_format)
    return ret


def parse_doc_id(raw_url):
    doc_id_re = re.compile(r'/spreadsheets/d/([a-zA-Z0-9-_]+)')
    #sheet_id_re = re.compile(r'[#&]gid=([0-9]+)')
    doc_id = re.findall(doc_id_re, raw_url)
    try:
        ret = doc_id[0]
    except IndexError as e:
        raise ValueError('invalid spreadsheet url "%s"' % raw_url)
    return ret


def make_entry(edict):
    width = int(edict['img_width'])
    height = int(edict['img_height'])
    raw_entry = {'name': edict['img_name'],
                 'mime_major': edict.get('img_major_mime') or None,
                 'mime_minor': edict.get('img_minor_mime') or None,
                 'width': width,
                 'height': height,
                 'upload_user_id': edict['img_user'],
                 'upload_user_text': edict['img_user_text']}
    if edict.get('oi_archive_name'):
        # The file has multiple versions
        raw_entry['flags'] = {
            'reupload': True,
            'reupload_date': wpts2dt(edict['rec_img_timestamp']),
            'reupload_user_id': edict['rec_img_user'],
            'reupload_user_text': edict['rec_img_text'],
            'archive_name': edict['oi_archive_name']}
    raw_entry['upload_date'] = wpts2dt(edict['img_timestamp'])
    raw_entry['resolution'] = width * height
    # file_id comes from Commons (labs.py); every checked import has one,
    # except dev's remote lookups where the utils endpoint returns none.
    if edict.get('file_id') is not None:
        raw_entry['file_id'] = edict['file_id']
    if edict.get('flags'):
        raw_entry['flags'] = edict['flags']
    return montage.rdb.Entry(**raw_entry)


# ---------------------------------------------------------------------------
# Import sources (hatnote/montage#510): every first-round source is fetched
# and parsed into rows here, then looked up on Commons and classified by
# import_check.py. Commons supplies all metadata; a CSV only gives names and,
# optionally, Commons file_ids (#509).
# ---------------------------------------------------------------------------

NAME_COLUMNS = ('filename', 'img_name')  # in order of preference
FILE_ID_COLUMN = 'file_id'

# a header-less list's first line is a file name, not a header, when it ends
# in a file extension (header words never do)
_FILE_EXT_RE = re.compile(r'\.[A-Za-z0-9]{2,5}$')
_FILE_ID_RE = re.compile(r'^[0-9]+$')

# Cells starting with one of these get a leading ' in Montage's CSV
# downloads, so spreadsheet programs do not run them as formulas; reading
# a CSV removes that ' again, so a download can be uploaded unchanged.
FORMULA_START_CHARS = "=+-@'"


def guard_cell(value):
    if value and value[0] in FORMULA_START_CHARS:
        return "'" + value
    return value


def unguard_cell(value):
    if len(value) > 1 and value[0] == "'" and value[1] in FORMULA_START_CHARS:
        return value[1:]
    return value


def normalise_name(name):
    """A file name as Montage and the replica store it: no File: prefix,
    underscores for spaces."""
    name = unguard_cell((name or '').strip())
    if name.startswith('File:'):
        name = name[5:].strip()
    return name.replace(' ', '_')


def parse_file_id(cell):
    """(file_id, malformed) for a file_id cell: a plain whole number above
    0, or empty. 1.49673E+08, 149,673,020 or 12.0 are malformed."""
    value = unguard_cell((cell or '').strip().strip(u'\xa0').strip())
    if not value:
        return None, False
    if _FILE_ID_RE.match(value) and int(value) > 0:
        return int(value), False
    return None, True


def _source_row(row_number, name_cell, file_id_cell=''):
    file_id, malformed = parse_file_id(file_id_cell)
    return {'row': row_number,
            'name_as_written': name_cell or '',
            'file_id_as_written': file_id_cell or '',
            'name': normalise_name(name_cell),
            'file_id': file_id,
            'malformed_file_id': malformed}


def _is_blank(row):
    return not row['name'] and not row['file_id_as_written'].strip()


def _header_key(cell):
    return cell.replace(u'\ufeff', '').strip().lower()


def _looks_like_file_name(line):
    value = line.strip().strip('"').strip()
    if value.startswith('File:'):
        value = value[5:]
    return bool(_FILE_EXT_RE.search(value))


def _line_name(line):
    """A header-less list's line: one CSV cell (a quoted name, as Google
    Sheets exports), or else the whole line, so commas in names survive."""
    try:
        cells = next(csv.reader([line]))
    except (StopIteration, csv.Error):
        cells = []
    if len(cells) == 1:
        return cells[0]
    return line.strip().strip('"')


def parse_source_rows(text):
    """(rows, columns) of a CSV or a header-less name list.

    The name column is `filename`, else `img_name`; `file_id` is optional;
    headers are matched case-insensitively, ignoring a BOM. Other columns
    are ignored (Commons supplies the metadata) and listed in
    columns['ignored']. Row numbers are spreadsheet rows (header = 1) or,
    for a header-less list, line numbers; blank rows are skipped.
    """
    columns = {'name': None, 'file_id': None, 'ignored': []}
    try:
        records = list(csv.reader(StringIO(text)))
    except csv.Error as e:
        raise ImportSourceInvalid('cannot read the CSV: %s' % (e,))
    if not records:
        return [], columns
    header = [_header_key(c) for c in records[0]]
    name_col = next((c for c in NAME_COLUMNS if c in header), None)
    rows = []
    if name_col is not None:
        name_idx = header.index(name_col)
        id_idx = header.index(FILE_ID_COLUMN) if FILE_ID_COLUMN in header else None
        columns['name'] = name_col
        columns['file_id'] = FILE_ID_COLUMN if id_idx is not None else None
        columns['ignored'] = [c.replace(u'\ufeff', '').strip()
                              for i, c in enumerate(records[0])
                              if i not in (name_idx, id_idx) and c.strip()]
        for i, record in enumerate(records[1:]):
            name = record[name_idx] if name_idx < len(record) else ''
            file_id = (record[id_idx] if id_idx is not None
                       and id_idx < len(record) else '')
            rows.append(_source_row(i + 2, name, file_id))
    else:
        lines = text.splitlines()
        if len(records[0]) > 1 and not _looks_like_file_name(lines[0]):
            raise ImportSourceInvalid(
                'no filename or img_name column: the first row has %s columns'
                ' but none is called "filename" or "img_name"'
                % len(records[0]))
        for i, line in enumerate(lines):
            rows.append(_source_row(i + 1, _line_name(line)))
    return [r for r in rows if not _is_blank(r)], columns


def parse_name_list(file_names):
    """Rows of a file list (import method `selected`): a list of names or
    one name per line; blank entries are skipped but keep their number."""
    if file_names is None:
        raise ImportSourceInvalid('no file names given')
    if isinstance(file_names, (str, bytes)):
        file_names = to_unicode(file_names).splitlines()
    rows = [_source_row(i + 1, to_unicode(name or ''))
            for i, name in enumerate(file_names)]
    return [r for r in rows if not _is_blank(r)]


def source_url(raw_url):
    """(fetch url, is a Google Sheet) for a gist / CSV / Sheet link."""
    if 'google.com' in raw_url:
        try:
            doc_id = parse_doc_id(raw_url)
        except ValueError as e:
            raise ImportSourceInvalid(str(e))
        return GSHEET_URL % doc_id, True
    if 'gist.github.com' in raw_url and 'githubusercontent' not in raw_url:
        # a gist's page -> its raw text; other links are fetched as given
        # (#208: '/raw' used to be appended to every link)
        raw_url = raw_url.replace('gist.github.com',
                                  'gist.githubusercontent.com') + '/raw'
    return raw_url, False


def fetch_source_text(raw_url):
    """The text of a gist / CSV link or a Google Sheet's CSV export. No
    Commons lookup happens here."""
    raw_url = (raw_url or '').strip()
    if not raw_url:
        raise ImportSourceInvalid('no link given')
    url, is_sheet = source_url(raw_url)
    try:
        resp = requests_get(url, timeout=SOURCE_FETCH_TIMEOUT)
    except requests.RequestException as e:
        raise ImportSourceInvalid('cannot load "%s" (%s)'
                                  % (raw_url, e.__class__.__name__))
    if resp.status_code != 200:
        raise ImportSourceInvalid('cannot load "%s" (HTTP status %s)'
                                  % (raw_url, resp.status_code))
    if is_sheet and 'text/csv' not in resp.headers.get('content-type', ''):
        raise ImportSourceInvalid('cannot load Google Sheet "%s" (is link sharing on?)'
                                  % raw_url)
    try:
        return resp.content.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ImportSourceInvalid('"%s" is not UTF-8 text' % raw_url)


def lookup_by_names(names, source='local'):
    """{normalised name: Commons file info} for the names that exist."""
    names = sorted(set(n for n in names if n))
    if not names:
        return {}
    if source == 'remote':
        file_infos, _ = get_by_filename_remote(names)
        wanted = set(names)
        found = {}
        for rec in file_infos:
            name = normalise_name(rec['img_name'])
            if name in wanted:  # infos for names not asked for are ignored
                found[name] = rec
        return found
    return get_files_info_by_names(names)


def lookup_by_ids(file_ids):
    """{file_id: Commons file info} for the file_ids of live files; on the
    wikireplica only (the public utils endpoint has no lookup by id)."""
    return get_files_info_by_ids(file_ids)


def category_records(category_name, source='local'):
    """Commons file infos of a category's files."""
    if not (category_name or '').strip():
        raise ImportSourceInvalid('no category given')
    if source == 'remote':
        return get_from_category_remote(category_name)
    return get_files(category_name)


def get_from_category_remote(category_name):
    params = {'name': category_name}
    url = REMOTE_UTILS_URL + '/category'
    file_infos, _ = get_from_remote(url, params)
    return file_infos

def get_from_remote(url, params):
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
    data = json.dumps(params)
    try:
        response = requests_post(url, data=data, headers=headers)
        resp_json = response.json()
        file_infos = resp_json['file_infos']
    except (requests.RequestException, ValueError, KeyError, TypeError) as e:
        raise ImportSourceInvalid('Commons lookup through %s failed (%s)'
                                  % (url, e.__class__.__name__))
    no_infos = resp_json.get('no_info')
    return file_infos, no_infos


def get_by_filename_remote(filenames, chunk_size=200):
    file_infos = []
    warnings = []
    for filenames_chunk in chunked_iter(filenames, chunk_size):
        params = {'names': filenames_chunk}
        url = REMOTE_UTILS_URL + '/file'
        resp, no_infos = get_from_remote(url, params)
        if no_infos:
            warnings += no_infos
        file_infos += resp
    return file_infos, warnings


"""
TODO:

* An Importer architecture. Load, normalize, verify, insert.
* Verify:
    * Images were all uploaded within the campaign window
    * No images uploaded by jurors?
    * Duplicate entry
* What to do when an image fails verification?

"""
