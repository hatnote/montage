
import pdb
import sys
import time
import os.path
import argparse

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)

sys.path.append(PROJ_PATH)

from sqlalchemy import create_engine

from montage.rdb import Base
from montage.utils import load_env_config


def drop_schema(db_url, echo=True):

    # echo="debug" also prints results of selects, etc.
    engine = create_engine(db_url, echo=echo)
    Base.metadata.drop_all(engine)

    return


def main():
    prs = argparse.ArgumentParser('drop montage db')
    add_arg = prs.add_argument
    add_arg('--db_url')
    add_arg('--debug', action="store_true", default=False)
    add_arg('--force', action="store_true", default=False)
    add_arg('--verbose', action="store_true", default=False)

    args = prs.parse_args()

    db_url = args.db_url
    if not db_url:
        # print '==  loading db_url from config'
        try:
            config = load_env_config()
        except Exception:
            print '!!  no db_url specified and could not load config file'
            raise
        else:
            db_url = config.get('db_url')

    if not args.force:
        confirmed = raw_input('??  this will drop all tables from %r.'
                              ' type yes to confirm: ' % db_url)
        if not confirmed == 'yes':
            print '--  you typed %r, aborting' % confirmed
            sys.exit(0)

    print '..  dropping all tables in %r in:' % db_url
    time.sleep(1.2)
    for x in range(3, 0, -1):
        print '.. ', x
        time.sleep(0.85)

    try:
        drop_schema(db_url=db_url, echo=args.verbose)
    except Exception:
        if not args.debug:
            raise
        pdb.post_mortem()
    else:
        print '++  schema dropped'


    return


if __name__ == '__main__':
    main()
