from __future__ import absolute_import
import os

try:
    import pymysql
except ImportError:
    pymysql = None


DB_CONFIG = os.path.expanduser('~/replica.my.cnf')


IMAGE_COLS = ['img_width',
              'img_height',
              'img_name',
              'img_major_mime',
              'img_minor_mime',
              'IFNULL(oi.actor_user, ci.actor_user) AS img_user',
              'IFNULL(oi.actor_name, ci.actor_name) AS img_user_text',
              'IFNULL(oi.oi_timestamp, img_timestamp) AS img_timestamp',
              'img_timestamp AS rec_img_timestamp',
              'ci.actor_user AS rec_img_user',
              'ci.actor_name AS rec_img_text',
              'oi.oi_archive_name AS oi_archive_name',
              # Original (first-ever) uploader fields — used for disqualification (#155)
              'orig.actor_name AS orig_upload_user_text',
              'orig.actor_user AS orig_upload_user_id',
              'orig.oi_timestamp AS orig_upload_date']

# Subquery that finds the oldest oldimage revision per file (the original upload)
ORIG_UPLOADER_SUBQUERY = """
    LEFT JOIN (
        SELECT oi_name,
               actor_user,
               actor_name,
               oi_timestamp
        FROM oldimage
        LEFT JOIN actor ON oi_actor = actor.actor_id
        WHERE oi_timestamp = (
            SELECT MIN(oi2.oi_timestamp)
            FROM oldimage oi2
            WHERE oi2.oi_name = oldimage.oi_name
        )
        GROUP BY oi_name
    ) AS orig ON img_name = orig.oi_name
"""


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
        FROM commonswiki_p.image AS i
        LEFT JOIN actor AS ci ON img_actor=ci.actor_id
        LEFT JOIN (
            SELECT oi_name,
                   oi_actor,
                   actor_user,
                   actor_name,
                   oi_timestamp,
                   oi_archive_name
            FROM oldimage
            LEFT JOIN actor ON oi_actor=actor.actor_id
            WHERE oi_timestamp = (
                SELECT MIN(oi2.oi_timestamp)
                FROM oldimage oi2
                WHERE oi2.oi_name = oldimage.oi_name
            )
        ) AS oi ON img_name=oi.oi_name
        {orig_subquery}
        JOIN page ON page_namespace = 6
        AND page_title = img_name
        JOIN categorylinks ON cl_from = page_id
        AND cl_type = 'file'
        JOIN linktarget ON cl_target_id = lt_id
        AND lt_namespace = 14
        AND lt_title = %s
        GROUP BY img_name
        ORDER BY oi_timestamp ASC;
    '''.format(cols=', '.join(IMAGE_COLS), orig_subquery=ORIG_UPLOADER_SUBQUERY)
    params = (category_name.replace(' ', '_'),)

    results = fetchall_from_commonswiki(query, params)

    return results


def get_file_info(filename):
    query = '''
        SELECT {cols}
        FROM commonswiki_p.image AS i
        LEFT JOIN actor AS ci ON img_actor=ci.actor_id
        LEFT JOIN (
            SELECT oi_name,
                   oi_actor,
                   actor_user,
                   actor_name,
                   oi_timestamp,
                   oi_archive_name
            FROM oldimage
            LEFT JOIN actor ON oi_actor=actor.actor_id
            WHERE oi_timestamp = (
                SELECT MIN(oi2.oi_timestamp)
                FROM oldimage oi2
                WHERE oi2.oi_name = oldimage.oi_name
            )
        ) AS oi ON img_name=oi.oi_name
        {orig_subquery}
        WHERE img_name = %s
        GROUP BY img_name
        ORDER BY oi_timestamp ASC;
    '''.format(cols=', '.join(IMAGE_COLS), orig_subquery=ORIG_UPLOADER_SUBQUERY)
    params = (filename.replace(' ', '_'),)
    results = fetchall_from_commonswiki(query, params)
    if results:
        return results[0]
    else:
        return None


if __name__ == '__main__':
    imgs = get_files('Images_from_Wiki_Loves_Monuments_2015_in_France')
    import pdb; pdb.set_trace()
