import os
import oursql


DB_CONFIG = os.path.expanduser('~/replica.my.cnf')


def get_images(category_name):
    db_title = 'commonswiki_p'
    db_host = 'commonswiki.labsdb'
    connection = oursql.connect(db=db_title,
                                host=db_host,
                                read_default_file=DB_CONFIG,
                                charset=None)
    cursor = connection.cursor(oursql.DictCursor)
    query = '''
    SELECT *
    FROM image
    JOIN page
    ON page_namespace = 6
    AND page_title = img_name
    JOIN categorylinks
    ON cl_from = page_id
    AND cl_type = 'file'
    AND cl_to = ?;
    '''
    params = (category_name.replace(' ', '_'),)
    cursor.execute(query, params)
    return cursor.fetchall()


if __name__ == '__main__':
    imgs = get_images('Images_from_Wiki_Loves_Monuments_2015_in_France')
    import pdb; pdb.set_trace()
