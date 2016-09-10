
import datetime

from unicodecsv import DictReader

from rdb import Entry
from labs import get_files

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
    return Entry(**raw_entry)


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
    return


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
    imgs = load_category('Images_from_Wiki_Loves_Monuments_2015_in_France')
    import pdb; pdb.set_trace()
