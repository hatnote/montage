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
              'IFNULL(oi_timestamp, img_timestamp) AS img_timestamp',
              'img_timestamp AS rec_img_timestamp',
              'ci.actor_user AS rec_img_user',
              'ci.actor_name AS rec_img_text',
              'oi.oi_archive_name AS oi_archive_name']


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
    return cursor.fetchall()


def get_files(category_name):
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
        AND cl_to = %s
        GROUP BY img_name
        ORDER BY oi_timestamp ASC;
    '''.format(cols=', '.join(IMAGE_COLS))
    params = (category_name.replace(' ', '_'),)

    results = fetchall_from_commonswiki(query, params)

    return results


def get_file_info(filename):
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
        WHERE img_name = %s
        GROUP BY img_name
        ORDER BY oi_timestamp ASC;
    '''.format(cols=', '.join(IMAGE_COLS))
    params = (filename.replace(' ', '_'),)
    results = fetchall_from_commonswiki(query, params)
    if results:
        results = results[0]
    return results


if __name__ == '__main__':
    imgs = get_files('Images_from_Wiki_Loves_Monuments_2015_in_France')
    import pdb; pdb.set_trace()
