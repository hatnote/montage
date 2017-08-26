import os

try:
    import oursql
except ImportError:
    oursql = None


DB_CONFIG = os.path.expanduser('~/replica.my.cnf')


class MissingMySQLClient(RuntimeError):
    pass


def fetchall_from_commonswiki(query, params):
    if oursql is None:
        raise MissingMySQLClient('could not import oursql, check your'
                                 ' environment and restart the service')
    db_title = 'commonswiki_p'
    db_host = 'commonswiki.labsdb'
    connection = oursql.connect(db=db_title,
                                host=db_host,
                                read_default_file=DB_CONFIG,
                                charset=None)
    cursor = connection.cursor(oursql.DictCursor)
    cursor.execute(query, params)
    return cursor.fetchall()


def get_files(category_name):
    query = '''
    SELECT *
    FROM commonswiki_p.image
    JOIN page
    ON page_namespace = 6
    AND page_title = img_name
    JOIN categorylinks
    ON cl_from = page_id
    AND cl_type = 'file'
    AND cl_to = ?;
    '''
    params = (category_name.replace(' ', '_'),)

    results = fetchall_from_commonswiki(query, params)

    return results


def get_file_info(filename):
    query = '''
    SELECT *
    FROM commonswiki_p.image
    WHERE img_name = ?;
    '''
    params = (filename.replace(' ', '_'),)
    results = fetchall_from_commonswiki(query, params)

    return results[0]


if __name__ == '__main__':
    imgs = get_files('Images_from_Wiki_Loves_Monuments_2015_in_France')
    import pdb; pdb.set_trace()
