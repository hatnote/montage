
import urllib
import hashlib

"""
https://upload.wikimedia.org/wikipedia/commons/8/8e/%D9%86%D9%82%D8%B4_%D8%A8%D8%B1%D8%AC%D8%B3%D8%AA%D9%87_%D8%A8%D9%84%D8%A7%D8%B4_2.JPG

https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/%D9%86%D9%82%D8%B4_%D8%A8%D8%B1%D8%AC%D8%B3%D8%AA%D9%87_%D8%A8%D9%84%D8%A7%D8%B4_2.JPG/360px-%D9%86%D9%82%D8%B4_%D8%A8%D8%B1%D8%AC%D8%B3%D8%AA%D9%87_%D8%A8%D9%84%D8%A7%D8%B4_2.JPG
"""

BASE = u'https://upload.wikimedia.org/wikipedia/commons'


def make_mw_img_url(title, size=None):
    "returns a unicode object URL"
    if isinstance(title, unicode):
        thash = hashlib.md5(title.encode('utf8')).hexdigest()
        url_title = urllib.quote(title.encode('utf8'))
    elif isinstance(title, bytes):
        thash = hashlib.md5(title).hexdigest()
        url_title = urllib.quote(title)
    else:
        raise TypeError('image title must be bytes or unicode')

    if size is None:
        size = 'orig'
    elif isinstance(size, int):
        size = '%spx' % size
    elif str(size).lower().startswith('sm'):
        size = '240px'
    elif str(size).lower().startswith('med'):
        size = '480px'

    if size != 'orig' and not str(size).endswith('px'):
        raise ValueError('size expected one of "sm", "med", "orig",'
                         ' or an integer pixel value, not %r' % size)

    if size == 'orig':
        parts = [BASE, thash[:1], thash[:2], url_title]
    else:
        parts = [BASE, 'thumb', thash[:1], thash[:2],
                 url_title, '%s-%s' % (size, url_title)]

    return u'/'.join(parts)
