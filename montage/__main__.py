# -*- coding: utf-8 -*-

from __future__ import absolute_import

if __name__ == '__main__':
    from .app import create_app
    from .utils import get_env_name

    # TODO: don't forget to update the app.py one level above on toolforge

    env_name = get_env_name()
    app = create_app(env_name=env_name)
    app.serve()
