
import datetime

from unicodecsv import DictReader

from rdb import Entry

CSV_FULL_COLS = ['img_name',
                 'img_major_mime',
                 'img_minor_mime',
                 'img_width',
                 'img_height',
                 'img_user',
                 'img_user_text',
                 'img_timestamp']


def wpts2dt(timestamp):
    return datetime.datetime.now()


def load_full_csv(csv_file_obj):
    # TODO: streaming this for big CSVs is an unnecessary headache

    ret = []
    dr = DictReader(csv_file_obj)

    for key in CSV_FULL_COLS:
        if key not in dr.fieldnames:
            raise ValueError('missing required column "%s" in csv file' % key)

    for edict in dr:
        kw = {'name': edict['img_name'],
              'mime_major': edict['img_major_mime'],
              'mime_minor': edict['img_minor_mime'],
              'upload_user_id': edict['img_user'],
              'upload_user_text': edict['img_user_text']}
        kw['upload_date'] = wpts2dt(edict['img_timestamp'])
        kw['height'] = int(edict['img_height'])
        kw['width'] = int(edict['img_width'])
        kw['resolution'] = kw['height'] * kw['width']

        entry = Entry(**kw)
        ret.append(entry)

    return ret


def load_brief_csv(csv_file_obj):
    "Just the image names, we'll look up the rest in the DB"
    return


def load_category(category_name):
    return


"""
TODO:

* An Importer architecture. Load, normalize, verify, insert.
* Verify:
    * Images were all uploaded within the campaign window
    * No images uploaded by jurors?
* What to do when an image fails verification?

"""
