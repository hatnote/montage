# this file is only used by wmflabs for hosting

import os
# pymysql (via getpass.getuser()) evaluates a default username at import time,
# which raises OSError('No username set in the environment') in Toolforge
# buildservice containers that have no passwd entry or USER env var. Set a safe
# default before importing anything that pulls in pymysql. This does not affect
# environment selection, which is driven by MONTAGE_ENV / get_env_name().
os.environ.setdefault('USER', 'montage')

from montage.app import create_app
from montage.utils import get_env_name

env_name = get_env_name()
app = create_app(env_name=env_name)
