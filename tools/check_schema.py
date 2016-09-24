
import pdb
import sys
import os.path
import argparse

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)

sys.path.append(PROJ_PATH)

from sqlalchemy import create_engine

from montage.rdb import Base
from montage.utils import load_env_config, check_schema


def create_schema(db_url, echo=True):

    # echo="debug" also prints results of selects, etc.
    engine = create_engine(db_url, echo=echo)
    Base.metadata.create_all(engine)

    return


def main():
    prs = argparse.ArgumentParser('create montage db and load initial data')
    add_arg = prs.add_argument
    add_arg('--db_url')
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

    check_schema(db_url=db_url,
                 base_type=Base,
                 echo=args.verbose,
                 autoexit=True)

    return


if __name__ == '__main__':
    main()
