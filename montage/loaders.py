
import datetime
import urllib2
import json

from unicodecsv import DictReader

import rdb
from labs import get_files, get_file_info

REMOTE_UTILS_URL = 'https://tools.wmflabs.org/montage-dev/v1/utils/'

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


def load_brief_csv(csv_file_obj, source='local'):
    "Just the image names, we'll look up the rest in the DB"

    ret = []
    dr = DictReader(csv_file_obj)
    
    if source == 'remote':
        # TODO: should be chunked
        files = get_by_filename_remote([r['img_name'] for r in dr])
        
        for edict in files:
            entry = make_entry(edict)
            ret.append(entry)
        return ret
    
    for row in dr:
        file_name = row['img_name']
        end_time = row.get('Endtime')  # what's this about
        edict = get_file_info(file_name)

        if end_time:
            edict['flags'] = {'end_time': end_time}

        entry = make_entry(edict)
        ret.append(entry)

    return ret


def get_entries_from_gist_csv(raw_url, source='local'):
    resp = urllib2.urlopen(raw_url)
    try:
        ret = load_full_csv(resp)
    except ValueError as e:
        # not a full csv
        ret = load_brief_csv(resp, source=source)
    return ret


def load_by_filename(file_names, source='local'):
    ret = []
    if source == 'remote':
        files = get_by_filename_remote(file_names)
    else:
        files = []
        for file_name in file_names:
            file_info = get_file_info(file_name)
            files.append(file_info)
    for edict in files:
        entry = make_entry(edict)
        ret.append(entry)
    return ret


def load_category(category_name, source='local'):
    ret = []
    if source == 'remote':
        files = get_from_category_remote(category_name)
    else:
        files = get_files(category_name)
    for edict in files:
        entry = make_entry(edict)
        ret.append(entry)

    return ret
        

def get_from_category_remote(category_name):
    params = {'name': category_name}
    url = REMOTE_UTILS_URL + '/category'
    file_infos = get_from_remote(url, params)
    return file_infos


def get_from_remote(url, params):
    content_type = {'Content-Type': 'application/json'}
    data = json.dumps(params)
    request = urllib2.Request(url, data, content_type)
    response = urllib2.urlopen(request)
    resp_json = json.load(response)
    file_infos = resp_json['file_infos']
    return file_infos


def get_by_filename_remote(file_names):
    # TODO: should this be chunked, if there are too many file names?
    params = {'names': file_names}
    url = REMOTE_UTILS_URL + '/file'
    file_infos = get_from_remote(url, params)
    return file_infos


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
    #imgs = get_entries_from_gist_csv('https://gist.githubusercontent.com/slaporte/7433943491098d770a8e9c41252e5424/raw/9181d59224cd3335a8f434ff4683c83023f7a3f9/wlm2015_fr_12k.csv')
    import pdb; pdb.set_trace()
