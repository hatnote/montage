
from __future__ import print_function
from __future__ import absolute_import
import pdb
import sys
import os.path
import argparse

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)

sys.path.append(PROJ_PATH)

from montage.rdb import Base
from montage.utils import load_env_config, check_schema, get_import_mode


def check_import_mode(config):
    """Exit 2 if the configured import mode (MONTAGE_IMPORT_MODE, or
    import_mode in the YAML config) is unknown. The web app refuses to
    start on one (hatnote/montage#621), so tools/deploy.sh runs this
    before it restarts the webservice: a typo aborts the deploy instead of
    taking the site down."""
    try:
        mode = get_import_mode(config)
    except ValueError as e:
        print('!!  %s' % (e,))
        sys.exit(2)
    print('++  import mode ok: %s' % (mode,))
    return mode


def main(argv=None):
    prs = argparse.ArgumentParser('create montage db and load initial data')
    add_arg = prs.add_argument
    add_arg('--db_url')
    add_arg('--verbose', action="store_true", default=False)

    args = prs.parse_args(argv)

    db_url = args.db_url
    if not db_url:
        try:
            config = load_env_config()
        except Exception:
            print('!!  no db_url specified and could not load config file')
            raise
        else:
            check_import_mode(config)
            db_url = config.get('db_url')
    else:
        print('--  import mode not checked (--db_url given, no config loaded)')

    check_schema(db_url=db_url,
                 base_type=Base,
                 echo=args.verbose,
                 autoexit=True)

    return


if __name__ == '__main__':
    main()
