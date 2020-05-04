
import pdb
import sys
import os.path
import argparse

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)

sys.path.append(PROJ_PATH)

from sqlalchemy import create_engine
from alembic.config import Config
from alembic import command

from montage.rdb import Base
from montage.utils import load_env_config


def migrate_schema(db_url, revision="head", echo=True):

    # echo="debug" also prints results of selects, etc.
    engine = create_engine(db_url, echo=echo)
    # Base.metadata.create_all(engine)

    alembic_cfg = Config(PROJ_PATH + "/alembic.ini")
    command.upgrade(alembic_cfg, revision)

    return


def main():
    prs = argparse.ArgumentParser('migrate montage db if necessary')
    add_arg = prs.add_argument
    add_arg('--db_url')
    add_arg('--debug', action="store_true", default=False)
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

    try:
        migrate_schema(db_url=db_url, echo=args.verbose)
    except Exception:
        if not args.debug:
            raise
        pdb.post_mortem()
    else:
        print '++  schema migration complete'

    return


if __name__ == '__main__':
    main()
