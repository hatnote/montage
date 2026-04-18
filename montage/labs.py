from __future__ import absolute_import
import os

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


def fetchall_from_commonswiki(query, params):
    if pymysql is None:
        raise MissingMySQLClient('could not import pymysql, check your'
                                 ' environment and restart the service')
    db_title = 'commonswiki_p'
    db_host = 'commonswiki.labsdb'
    connection = pymysql.connect(db=db_title,
                                 host=db_host,
                                 read_default_file=DB_CONFIG,
                                 charset='utf8')
    cursor = connection.cursor(pymysql.cursors.DictCursor)
    cursor.execute(query, params)
    res = cursor.fetchall()

    # looking at the schema on labs, it's all varbinary, not varchar,
    # so this block converts values
    ret = []
    for rec in res:
        new_rec = {}
        for k, v in rec.items():
            if isinstance(v, bytes):
                v = v.decode('utf8')
            new_rec[k] = v
        ret.append(new_rec)
    return ret


def get_files(category_name):
    query = '''
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
    '''.format(cols=', '.join(FILE_COLS),
               earliest_rev=_EARLIEST_REVISION_SUBQUERY)
    params = (category_name.replace(' ', '_'),)

    return fetchall_from_commonswiki(query, params)


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


def get_files_legacy(category_name):
    """Verbatim copy of the original get_files() using image/oldimage tables.

    Kept alive solely for the xfail parity test (test_get_files_parity).
    Remove together with that test after 28 May 2026 once image/oldimage are
    dropped from wikireplicas.
    """
    IMAGE_COLS = ['img_width',
                  'img_height',
                  'img_name',
                  'img_major_mime',
                  'img_minor_mime',
                  'IFNULL(oi.actor_user, ci.actor_user) AS img_user',
                  'IFNULL(oi.actor_name, ci.actor_name) AS img_user_text',
                  'IFNULL(oi_timestamp, img_timestamp) AS img_timestamp',
                  'img_timestamp AS rec_img_timestamp',
                  'ci.actor_user AS rec_img_user',
                  'ci.actor_name AS rec_img_text',
                  'oi.oi_archive_name AS oi_archive_name']
    query = '''
        SELECT {cols}
        FROM commonswiki_p.image AS i
        LEFT JOIN actor AS ci ON img_actor=ci.actor_id
        LEFT JOIN (SELECT oi_name,
                          oi_actor,
                          actor_user,
                          actor_name,
                          oi_timestamp,
                          oi_archive_name
                   FROM oldimage
                   LEFT JOIN actor ON oi_actor=actor.actor_id) AS oi ON img_name=oi.oi_name
        JOIN page ON page_namespace = 6
        AND page_title = img_name
        JOIN categorylinks ON cl_from = page_id
        AND cl_type = 'file'
        JOIN linktarget ON cl_target_id = lt_id
        AND lt_namespace = 14
        AND lt_title = %s
        GROUP BY img_name
        ORDER BY oi_timestamp ASC;
    '''.format(cols=', '.join(IMAGE_COLS))
    params = (category_name.replace(' ', '_'),)
    return fetchall_from_commonswiki(query, params)


if __name__ == '__main__':
    imgs = get_files('Images_from_Wiki_Loves_Monuments_2015_in_France')
    print(imgs)
