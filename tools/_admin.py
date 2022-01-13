from __future__ import print_function
from __future__ import absolute_import
import os
import sys

import fire

CUR_PATH = os.path.dirname(os.path.abspath(__file__))
PROJ_PATH = os.path.dirname(CUR_PATH)

sys.path.append(PROJ_PATH)

from montage.rdb import (make_rdb_session,
                         UserDAO,
                         MaintainerDAO,
                         OrganizerDAO,
                         CoordinatorDAO,
                         lookup_user)


"""Generating a command line interface with Python Fire.


It's (mostly) functional, but may be daunting if you're not familiar
with the DAOs in ../rdb.py. I haven't tested the full campaign flow,
so you may encounter a few operations that still can't be done via
CLI.


Usage:
    _admin.py user ...
    _admin.py maintainer ...
    _admin.py organizer ...
    _admin.py coordinator --round-id=<round_id:int> ... 
        OR
    _admin.py coordinator --campaign_id=<campaign_id:int> ...
    
    (ignore the other options)

Tip: try _admin.py <command> -- --interactive if you want to explore
or use the results in a REPL.

It would be nice to decorate or list the functions that I want Fire
to expose. There are a lot of internal functions that we can ignore.
""" 


class AdminTool(object):

    def __init__(self, user='Slaporte', echo=False):
        rdb_session = make_rdb_session(echo=echo)
        self.rdb_session = rdb_session
        user = lookup_user(rdb_session, user)
        self.user_dao = UserDAO(rdb_session, user)
        self.maint_dao = MaintainerDAO(self.user_dao)
        self.org_dao = OrganizerDAO(self.user_dao)

    def commit(self, func):
        def wrapper_func(*args, **kwargs):
            retval = func(*args, **kwargs)
            self.rdb_session.commit()
            return retval
        return wrapper_func

    def add_commit(self, cls):
        for attr in cls.__dict__:
            if callable(getattr(cls, attr)):
                setattr(cls, attr, self.commit(getattr(cls, attr)))
        return cls

    def user(self):
        return self.add_commit(self.user_dao)

    def maintainer(self):
        return self.add_commit(self.maint_dao)

    def organizer(self):
        return self.add_commit(self.org_dao)

    def coordinator(self, round_id=None, campaign_id=None):
        if round_id:
            print(round_id)
            coord = CoordinatorDAO.from_round(self.user_dao, round_id)
        elif campaign_id:
            coord = CoordinatorDAO.from_campaign(self.user_dao,
                                                 campaign_id)
        else:
            raise Exception('need round_id or campaign_id')
        return self.add_commit(coord)


if __name__ == '__main__':
    fire.Fire(AdminTool)
