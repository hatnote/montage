from __future__ import absolute_import
import os
from contextlib import contextmanager

try:
    import pymysql
except ImportError:
    pymysql = None


DB_CONFIG = os.path.expanduser('~/replica.my.cnf')


FILE_COLS = ['fr.fr_width AS img_width',
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
             'file.file_id AS file_id']

# Alias "oi" mirrors the old oldimage (oi) role; here it is the earliest
# non-deleted filerevision for the file, not the oldimage table.
_EARLIEST_REVISION_SUBQUERY = '''
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


class MissingMySQLClient(RuntimeError):
    pass


# Wikireplica hosts, both on the analytics replicas and both overridable,
# e.g. when Wikimedia moves tables again. COMMONS_DB_HOST used to be the
# legacy alias commonswiki.labsdb, which points to the same s4 analytics
# replica.
COMMONS_DB_HOST = os.environ.get(
    'MONTAGE_COMMONS_DB_HOST',
    'commonswiki.analytics.db.svc.wikimedia.cloud')
# Since 2026-09-08 the Commons links tables (categorylinks, linktarget, ...)
# live on their own cluster (x4); the copies on the main Commons replica are
# no longer written, so category membership must be read from this replica.
# See https://wikitech.wikimedia.org/wiki/News/2026_Commons_links_tables_database_split
COMMONS_LINKS_DB_HOST = os.environ.get(
    'MONTAGE_COMMONS_LINKS_DB_HOST',
    'links.commonswiki.analytics.db.svc.wikimedia.cloud')

# file names per query when looking up a category's files on the main replica
FILE_LOOKUP_CHUNK_SIZE = 500


def _connect(db_host):
    if pymysql is None:
        raise MissingMySQLClient('could not import pymysql, check your'
                                 ' environment and restart the service')
    return pymysql.connect(db='commonswiki_p',
                           host=db_host,
                           read_default_file=DB_CONFIG,
                           charset='utf8',
                           cursorclass=pymysql.cursors.DictCursor)


def _decode_rows(rows):
    # looking at the schema on labs, it's all varbinary, not varchar,
    # so this block converts values
    ret = []
    for rec in rows:
        new_rec = {}
        for k, v in rec.items():
            if isinstance(v, bytes):
                v = v.decode('utf8')
            new_rec[k] = v
        ret.append(new_rec)
    return ret


@contextmanager
def commonswiki_connection(db_host=COMMONS_DB_HOST):
    """One replica connection, closed on exit. Yields fetchall(query,
    params), which runs a query on that connection and returns decoded
    dict rows, so a multi-query lookup reuses one connection."""
    connection = _connect(db_host)

    def fetchall(query, params):
        cursor = connection.cursor()
        try:
            cursor.execute(query, params)
            return _decode_rows(cursor.fetchall())
        finally:
            cursor.close()

    try:
        yield fetchall
    finally:
        connection.close()


def fetchall_from_commonswiki(query, params, db_host=COMMONS_DB_HOST):
    """Run one query on its own (closed afterwards) connection."""
    with commonswiki_connection(db_host) as fetchall:
        return fetchall(query, params)


def get_category_file_names(category_name):
    """Names of the files directly in a Commons category, read from the
    links replica (page exists on both clusters, so this stays one query).
    """
    with commonswiki_connection(COMMONS_LINKS_DB_HOST) as fetchall:
        return _category_file_names(fetchall, category_name)


def _category_file_names(fetchall, category_name):
    query = '''
        SELECT DISTINCT page_title AS file_name
        FROM categorylinks
        JOIN linktarget ON cl_target_id = lt_id
          AND lt_namespace = 14
          AND lt_title = %s
        JOIN page ON page_id = cl_from
          AND page_namespace = 6
        WHERE cl_type = 'file'
    '''
    params = (category_name.replace(' ', '_'),)
    rows = fetchall(query, params)
    return [row['file_name'] for row in rows]


def get_files_by_name(file_names):
    """File details for file names (underscored), from the main replica."""
    if not file_names:
        return []
    with commonswiki_connection(COMMONS_DB_HOST) as fetchall:
        return _files_by_name(fetchall, file_names)


def _files_query(column, count):
    """The file details query for `count` values of file.<column>; one
    query text for lookups by name and by file_id."""
    assert column in ('file_name', 'file_id')
    return '''
        SELECT DISTINCT {cols}
        FROM commonswiki_p.file AS file
        JOIN commonswiki_p.filerevision AS fr ON fr.fr_id = file.file_latest
          AND fr.fr_deleted = 0
        LEFT JOIN actor AS ci ON fr.fr_actor = ci.actor_id
        LEFT JOIN commonswiki_p.filetypes AS ft ON file.file_type = ft.ft_id
        {earliest_rev}
        WHERE file.{column} IN ({values})
          AND file.file_deleted = 0
    '''.format(cols=', '.join(FILE_COLS),
               earliest_rev=_EARLIEST_REVISION_SUBQUERY,
               column=column,
               values=', '.join(['%s'] * count))


def _files_by_name(fetchall, file_names):
    if not file_names:
        return []
    query = _files_query('file_name', len(file_names))
    return fetchall(query, tuple(file_names))


def _files_by_id(fetchall, file_ids):
    if not file_ids:
        return []
    query = _files_query('file_id', len(file_ids))
    return fetchall(query, tuple(file_ids))


def get_files_info_by_names(file_names):
    """{underscored name: file info} for the names that exist, looked up in
    chunks instead of one query per file, all on one connection."""
    names = sorted(set(name.replace(' ', '_') for name in file_names))
    ret = {}
    if not names:
        return ret
    with commonswiki_connection(COMMONS_DB_HOST) as fetchall:
        for i in range(0, len(names), FILE_LOOKUP_CHUNK_SIZE):
            chunk = names[i:i + FILE_LOOKUP_CHUNK_SIZE]
            for rec in _files_by_name(fetchall, chunk):
                ret[rec['img_name']] = rec
    return ret


def get_files_info_by_ids(file_ids):
    """{file_id: file info} for the file_ids of live files (Commons'
    file.file_id), in chunks on one connection, like
    get_files_info_by_names (hatnote/montage#510)."""
    ids = sorted(set(int(i) for i in file_ids))
    ret = {}
    if not ids:
        return ret
    with commonswiki_connection(COMMONS_DB_HOST) as fetchall:
        for i in range(0, len(ids), FILE_LOOKUP_CHUNK_SIZE):
            chunk = ids[i:i + FILE_LOOKUP_CHUNK_SIZE]
            for rec in _files_by_id(fetchall, chunk):
                ret[int(rec['file_id'])] = rec
    return ret


def get_files(category_name):
    # Two steps because category membership and file data now live on
    # different database clusters, which cannot be joined in SQL.
    # One connection per cluster for the whole lookup.
    file_names = sorted(set(get_category_file_names(category_name)))
    ret = []
    if not file_names:
        return ret
    with commonswiki_connection(COMMONS_DB_HOST) as fetchall:
        for i in range(0, len(file_names), FILE_LOOKUP_CHUNK_SIZE):
            chunk = file_names[i:i + FILE_LOOKUP_CHUNK_SIZE]
            ret.extend(_files_by_name(fetchall, chunk))
    # same order as the old single query's ORDER BY file_name (binary)
    ret.sort(key=lambda rec: rec['img_name'].encode('utf8'))
    return ret


def get_file_info(filename):
    query = '''
        SELECT {cols}
        FROM commonswiki_p.file AS file
        JOIN commonswiki_p.filerevision AS fr ON fr.fr_id = file.file_latest
          AND fr.fr_deleted = 0
        LEFT JOIN actor AS ci ON fr.fr_actor = ci.actor_id
        LEFT JOIN commonswiki_p.filetypes AS ft ON file.file_type = ft.ft_id
        {earliest_rev}
        WHERE file.file_name = %s
          AND file.file_deleted = 0
    '''.format(cols=', '.join(FILE_COLS),
               earliest_rev=_EARLIEST_REVISION_SUBQUERY)
    params = (filename.replace(' ', '_'),)
    results = fetchall_from_commonswiki(query, params)
    if results:
        return results[0]
    else:
        return None


if __name__ == '__main__':
    imgs = get_files('Images_from_Wiki_Loves_Monuments_2015_in_France')
    print(imgs)
