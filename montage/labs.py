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
              'img_user',
              'img_user_text',
              'img_timestamp']


class MissingMySQLClient(RuntimeError):
    pass


def fetchall_from_commonswiki(query, params):
    if pymysql is None:
        raise MissingMySQLClient('could not import oursql, check your'
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
    FROM commonswiki_p.image
    JOIN page
    ON page_namespace = 6
    AND page_title = img_name
    JOIN categorylinks
    ON cl_from = page_id
    AND cl_type = 'file'
    AND cl_to = ?;
    '''.format(cols=', '.join(IMAGE_COLS))
    params = (category_name.replace(' ', '_'),)

    results = fetchall_from_commonswiki(query, params)

    return results


def get_file_info(filename):
    query = '''
    SELECT {cols}
    FROM commonswiki_p.image
    WHERE img_name = ?;
    '''.format(cols=', '.join(IMAGE_COLS))
    params = (filename.replace(' ', '_'),)
    results = fetchall_from_commonswiki(query, params)
    if results:
        results = results[0]
    return results


if __name__ == '__main__':
    imgs = get_files('Images_from_Wiki_Loves_Monuments_2015_in_France')
    import pdb; pdb.set_trace()
