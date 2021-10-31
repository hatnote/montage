# -*- coding: utf-8 -*-

"""x Logging in
 - Health check
 - Coordinators
  x See a list of campaigns
  - Save edits to a campaign
  x See a list of rounds per campaign
  - Save edits to a round
  - Import photos for a round
  - Close out a round
  - Export the output from a round
  - Send notifications to coordinators & jurors (?)
 - Jurors
  x See a list of campaigns and rounds
  x See the next vote
  x Submit a vote
  x Skip a vote
  - Expoert their own votes (?)
  - Change a vote for an open round (?)

Practical design:

Because we're building on angular, most URLs return JSON, except for
login and complete_login, which give back redirects, and the root
page, which gives back the HTML basis.

# A bit of TBI design

We add privileged Users (with coordinator flag enabled). Coordinators
can create Campaigns, and see and interact only with Campaigns they've
created or been added to. Can Coordinators create other Coordinators?

"""
from __future__ import absolute_import
from .app import create_app
from .utils import get_env_name

# TODO: don't forget to update the app.py one level above on toolforge


if __name__ == '__main__':
    env_name = get_env_name()
    app = create_app(env_name=env_name)
    app.serve()
