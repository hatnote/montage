from __future__ import absolute_import
import os

try:
    import pymysql
except ImportError:
    pymysql = None


DB_CONFIG = os.path.expanduser('~/replica.my.cnf')


# Column mapping for the new file/filerevision schema on wikireplica.
# The old image/oldimage tables are being removed (deadline: 28 May 2026,
# see https://phabricator.wikimedia.org/T123582 and hatnote/montage#504).
#
# Mapping summary:
#   image  -> file  (img_* cols -> file_* cols, img_actor -> file_actor)
#   oldimage -> filerevision  (oi_* cols -> fr_* cols, oi_actor -> fr_actor)
FILE_COLS = ['fi.file_width AS img_width',
             'fi.file_height AS img_height',
             'fi.file_name AS img_name',
             'fi.file_media_type AS img_major_mime',
             'fi.file_minor_mime AS img_minor_mime',
             'IFNULL(fr.actor_user, ci.actor_user) AS img_user',
             'IFNULL(fr.actor_name, ci.actor_name) AS img_user_text',
             'IFNULL(fr.fr_timestamp, fi.file_timestamp) AS img_timestamp',
             'fi.file_timestamp AS rec_img_timestamp',
             'ci.actor_user AS rec_img_user',
             'ci.actor_name AS rec_img_text',
             'fr.fr_archive_name AS oi_archive_name']


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

    # schema on labs is varbinary, not varchar, so decode each value
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
    # Migrated from image/oldimage to file/filerevision (see issue #504)
    query = '''
        SELECT {cols}
        FROM commonswiki_p.`file` AS fi
        LEFT JOIN actor AS ci ON fi.file_actor=ci.actor_id
        LEFT JOIN (SELECT fr_name,
                          fr_actor,
                          actor_user,
                          actor_name,
                          fr_timestamp,
                          fr_archive_name
                   FROM filerevision
                   LEFT JOIN actor ON fr_actor=actor.actor_id) AS fr ON fi.file_name=fr.fr_name
        JOIN page ON page_namespace = 6
        AND page_title = fi.file_name
        JOIN categorylinks ON cl_from = page_id
        AND cl_type = 'file'
        JOIN linktarget ON cl_target_id = lt_id
        AND lt_namespace = 14
        AND lt_title = %s
        GROUP BY fi.file_name
        ORDER BY fr.fr_timestamp ASC;
    '''.format(cols=', '.join(FILE_COLS))
    params = (category_name.replace(' ', '_'),)

    results = fetchall_from_commonswiki(query, params)

    return results


def get_file_info(filename):
    # Migrated from image/oldimage to file/filerevision (see issue #504)
    query = '''
        SELECT {cols}
        FROM commonswiki_p.`file` AS fi
        LEFT JOIN actor AS ci ON fi.file_actor=ci.actor_id
        LEFT JOIN (SELECT fr_name,
                          fr_actor,
                          actor_user,
                          actor_name,
                          fr_timestamp,
                          fr_archive_name
                   FROM filerevision
                   LEFT JOIN actor ON fr_actor=actor.actor_id) AS fr ON fi.file_name=fr.fr_name
        WHERE fi.file_name = %s
        GROUP BY fi.file_name
        ORDER BY fr.fr_timestamp ASC;
    '''.format(cols=', '.join(FILE_COLS))
    params = (filename.replace(' ', '_'),)
    results = fetchall_from_commonswiki(query, params)
    if results:
        return results[0]
    else:
        return None


if __name__ == '__main__':
    imgs = get_files('Images_from_Wiki_Loves_Monuments_2015_in_France')
    print('got %d images' % len(imgs))
