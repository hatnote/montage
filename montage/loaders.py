
import datetime
import urllib2

from unicodecsv import DictReader

import rdb
from labs import get_files, get_file_info

CSV_FULL_COLS = ['img_name',
                 'img_major_mime',
                 'img_minor_mime',
                 'img_width',
                 'img_height',
                 'img_user',
                 'img_user_text',
                 'img_timestamp']


def wpts2dt(timestamp):
    wpts_format = '%Y%m%d%H%M%S'
    return datetime.datetime.strptime(timestamp, wpts_format)


def make_entry(edict):
    width = int(edict['img_width'])
    height = int(edict['img_height'])
    raw_entry = {'name': edict['img_name'],
                 'mime_major': edict['img_major_mime'],
                 'mime_minor': edict['img_minor_mime'],
                 'width': width,
                 'height': height,
                 'upload_user_id': edict['img_user'],
                 'upload_user_text': edict['img_user_text']}
    raw_entry['upload_date'] = wpts2dt(edict['img_timestamp'])
    raw_entry['resolution'] = width * height
    if edict.get('flags'):
        raw_entry['flags'] = edict['flags']
    return rdb.Entry(**raw_entry)


def load_full_csv(csv_file_obj):
    # TODO: streaming this for big CSVs is an unnecessary headache

    ret = []
    dr = DictReader(csv_file_obj)

    for key in CSV_FULL_COLS:
        if key not in dr.fieldnames:
            raise ValueError('missing required column "%s" in csv file' % key)

    for edict in dr:
        entry = make_entry(edict)
        ret.append(entry)

    return ret


def load_brief_csv(csv_file_obj):
    "Just the image names, we'll look up the rest in the DB"

    ret = []
    dr = DictReader(csv_file_obj)
    
    for row in dr:
        name = row['Filename']
        end_time = row.get('Endtime')
        edict = get_file_info(name)

        if end_time:
            edict['flags'] = {'end_time': end_time}

        entry = make_entry(edict)
        ret.append(entry)

    return ret


def get_entries_from_gist_csv(raw_url):
    resp = urllib2.urlopen(raw_url)
    ret = load_full_csv(resp)
    return ret


def load_category(category_name):
    ret = []
    files = get_files(category_name)

    for edict in files:
        entry = make_entry(edict)
        ret.append(entry)

    return ret


"""
TODO:

* An Importer architecture. Load, normalize, verify, insert.
* Verify:
    * Images were all uploaded within the campaign window
    * No images uploaded by jurors?
    * Duplicate entry
* What to do when an image fails verification?

"""

if __name__ == '__main__':
    #imgs = load_category('Images_from_Wiki_Loves_Monuments_2015_in_France')
    imgs = get_entries_from_gist_csv('https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/9181d59224cd3335a8f434ff4683c83023f7a3f9/wlm2015_fr_12k.csv')
    import pdb; pdb.set_trace()
