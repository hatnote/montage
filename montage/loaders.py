
import datetime
import StringIO
import json
import re

from boltons.iterutils import chunked_iter
from unicodecsv import DictReader
import requests

import rdb
from labs import get_files, get_file_info

REMOTE_UTILS_URL = 'https://montage.toolforge.org/v1/utils/'

GSHEET_URL = 'https://docs.google.com/spreadsheets/d/%s/gviz/tq?tqx=out:csv'

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
    try:
        ret = datetime.datetime.strptime(timestamp, wpts_format)
    except ValueError as e:
        wpts_format = '%Y-%m-%dT%H:%M:%S'  # based on output format
        ret = datetime.datetime.strptime(timestamp, wpts_format)
    return ret


def parse_doc_id(raw_url):
    doc_id_re = re.compile(r'/spreadsheets/d/([a-zA-Z0-9-_]+)')
    #sheet_id_re = re.compile(r'[#&]gid=([0-9]+)')
    doc_id = re.findall(doc_id_re, raw_url)
    try:
        ret = doc_id[0]
    except IndexError as e:
        raise ValueError('invalid spreadsheet url "%s"' % raw_url)
    return ret


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
    if edict.get('oi_archive_name'):
        # The file has multiple versions
        raw_entry['flags'] = {
            'reupload': True,
            'reupload_date': wpts2dt(edict['rec_img_timestamp']),
            'reupload_user_id': edict['rec_img_user'],
            'reupload_user_text': edict['rec_img_text'],
            'archive_name': edict['oi_archive_name']}
    raw_entry['upload_date'] = wpts2dt(edict['img_timestamp'])
    raw_entry['resolution'] = width * height
    if edict.get('flags'):
        raw_entry['flags'] = edict['flags']
    return rdb.Entry(**raw_entry)


def load_full_csv(csv_file_obj, source='remote'):
    # TODO: streaming this for big CSVs is an unnecessary headache

    ret = []
    warnings = []

    dr = DictReader(csv_file_obj)

    if 'filename' in dr.fieldnames:
        return load_partial_csv(dr, source=source)

    for key in CSV_FULL_COLS:
        if key not in dr.fieldnames:
            raise ValueError('missing required column "%s" in csv file' % key)

    for edict in dr:
        try:
            entry = make_entry(edict)
        except TypeError as e:
            warnings.append((edict, e))
        else:
            ret.append(entry)

    return ret, warnings


def load_partial_csv(dr, source='remote'):
    ret = []
    warnings = []
    file_names = [r['filename'] for r in dr]
    file_names_obj = StringIO.StringIO('\n'.join(file_names))
    return load_name_list(file_names_obj, source=source)


def load_name_list(file_obj, source='local'):
    """ Just the file names, and we'll look up the rest"""

    ret = []
    warnings = []

    rl = file_obj.readlines()

    # clean up the filenames
    for i, filename in enumerate(rl):
        filename = filename.strip()
        if filename.startswith('File:'):
            filename = filename[5:]
        rl[i] = filename

    edicts = []

    if source == 'remote':
        edicts, warnings = get_by_filename_remote(rl)
    else:
        for filename in rl:
            file_info = get_file_info(filename)
            if file_info is not None:
                edict, warnings = file_info
                edicts.append(edict)

    for edict in edicts:
        try:
            entry = make_entry(edict)
        except TypeError as e:
            warnings.append((edict, e))
        else:
            ret.append(entry)

    return ret, warnings

def get_entries_from_csv(raw_url, source='local'):
    if 'google.com' in raw_url:
        return get_entries_from_gsheet(raw_url, source)
    return get_entries_from_gist(raw_url, source)

def get_entries_from_gist(raw_url, source='local'):
    if 'githubusercontent' not in raw_url:
        raw_url = raw_url.replace('gist.github.com',
                                  'gist.githubusercontent.com') + '/raw'
    resp = requests.get(raw_url)

    try:
        ret, warnings = load_full_csv(StringIO.StringIO(resp.content))
    except ValueError as e:
        # not a full csv
        ret, warnings = load_name_list(StringIO.StringIO(resp.content), source=source)

    return ret, warnings


def get_entries_from_gsheet(raw_url, source='local'):
    #TODO: add support for sheet tabs
    doc_id = parse_doc_id(raw_url)
    url = GSHEET_URL % doc_id
    resp = requests.get(url)

    if not 'text/csv' in resp.headers['content-type']:
        raise ValueError('cannot load Google Sheet "%s" (is link sharing on?)' % raw_url)

    try:
        ret, warnings = load_full_csv(StringIO.StringIO(resp.content), source=source)
    except ValueError:
        try:
            ret, warnings = load_partial_csv(resp)  # TODO: load_partial_csv expects a dictreader, did this ever work?
        except ValueError:
            file_names = [fn.strip('\"') for fn in resp.content.split('\n')]
            file_names_obj = StringIO.StringIO('\n'.join(file_names))
            ret, warnings = load_name_list(file_names_obj, source=source)

    return ret, warnings


def load_by_filename(filenames, source='local'):
    entries = []
    warnings = []
    if source == 'remote':
        files, warnings = get_by_filename_remote(filenames)
    else:
        files = []
        for filename in filenames:
            file_info = get_file_info(filename)
            if file_info is not None:
                files.append(file_info)
            else:
                warnings.append(
                    'file "%s" does not exist, please check that its name is spelled correctly, '
                    'that it has not been renamed or removed' % (filename,)
                )
    for edict in files:
        entry = make_entry(edict)
        entries.append(entry)
    return entries, warnings


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
    file_infos, _ = get_from_remote(url, params)
    return file_infos


def get_from_remote(url, params):
    headers = {'Content-Type': 'application/json'}
    data = json.dumps(params)
    response = requests.post(url, data=data, headers=headers)
    resp_json = response.json()
    file_infos = resp_json['file_infos']
    no_infos = resp_json.get('no_info')
    return file_infos, no_infos


def get_by_filename_remote(filenames, chunk_size=200):
    file_infos = []
    warnings = []
    for filenames_chunk in chunked_iter(filenames, chunk_size):
        params = {'names': filenames_chunk}
        url = REMOTE_UTILS_URL + '/file'
        resp, no_infos = get_from_remote(url, params)
        if no_infos:
            # print '!! info missing for %s' % no_infos
            warnings += no_infos
        file_infos += resp
    return file_infos, warnings


"""
TODO:

* An Importer architecture. Load, normalize, verify, insert.
* Verify:
    * Images were all uploaded within the campaign window
    * No images uploaded by jurors?
    * Duplicate entry
* What to do when an image fails verification?

"""
