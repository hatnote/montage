
from __future__ import absolute_import

import hashlib

import six.moves.urllib.parse, six.moves.urllib.error
from .utils import unicode

"""
https://upload.wikimedia.org/wikipedia/commons/8/8e/%D9%86%D9%82%D8%B4_%D8%A8%D8%B1%D8%AC%D8%B3%D8%AA%D9%87_%D8%A8%D9%84%D8%A7%D8%B4_2.JPG

https://upload.wikimedia.org/wikipedia/commons/thumb/8/8e/%D9%86%D9%82%D8%B4_%D8%A8%D8%B1%D8%AC%D8%B3%D8%AA%D9%87_%D8%A8%D9%84%D8%A7%D8%B4_2.JPG/360px-%D9%86%D9%82%D8%B4_%D8%A8%D8%B1%D8%AC%D8%B3%D8%AA%D9%87_%D8%A8%D9%84%D8%A7%D8%B4_2.JPG
"""

BASE = u'https://upload.wikimedia.org/wikipedia/commons'


def make_mw_img_url(title, size=None):
    """Returns a unicode object URL using Special:Redirect/file/ endpoint.
    
    This endpoint handles file moves/renames on Wikimedia Commons automatically.
    """
    if isinstance(title, unicode):
        url_title = six.moves.urllib.parse.quote(title.encode('utf8'))
    elif isinstance(title, bytes):
        url_title = six.moves.urllib.parse.quote(title)
    else:
        raise TypeError('image title must be bytes or unicode')

    base_url = u'https://commons.wikimedia.org/w/index.php?title=Special:Redirect/file/'
    
    if size is None:
        # No size parameter = full size
        return base_url + url_title
    elif isinstance(size, int):
        width = size
    elif str(size).lower().startswith('sm'):
        width = 240
    elif str(size).lower().startswith('med'):
        width = 480
    elif str(size).lower() == 'orig':
        # 'orig' means full size
        return base_url + url_title
    else:
        raise ValueError('size expected one of "sm", "med", "orig",'
                         ' or an integer pixel value, not %r' % size)
    
    return u'%s%s&width=%d' % (base_url, url_title, width)
