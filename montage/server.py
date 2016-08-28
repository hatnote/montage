"""
 - Logging in
 - Health check
 - Admins
  - See a list of campaigns
  - Save edits to a campaign
  - See a list of rounds per campaign
  - Save edits to a round
  - Import photos for a round
  - Close out a round
  - Export the output from a round
  - Send notifications to admins (?)
 - Jurors
  - See a list of campaigns and rounds
  - See the next vote
  - Submit a vote
  - Skip a vote
  - Expoert their own votes (?)
  - Change a vote for an open round (?)
"""

from clastic import Application, Middleware
from clastic.render import render_basic

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from rdb import get_campaign, get_all_campaigns, get_round


def home():
    return {'test': True}


def list_campaigns(request, rdb_session):
    user = request.values.get('user')
    campaigns = get_all_campaigns(rdb_session, user)
    return {'campaigns': [c.to_dict() for c in campaigns]}


def get_campaign_admin(request, rdb_session, campaign):
    user = request.values.get('user')
    campaign = get_campaign(rdb_session, user, id=campaign)
    return campaign.to_dict()


def get_round_admin(request, rdb_session, round, campaign=None):
    user = request.values.get('user')
    round = get_round(rdb_session, user, id=round)
    return round.to_dict()


def preview_selection(rdb_session, round, campaign=None):
    return


class DBSessionMiddleware(Middleware):
    provides = ('rdb_session',)

    def __init__(self, session_type):
        self.session_type = session_type

    def request(self, next):
        return next(rdb_session=self.session_type())


def create_app():
    routes = [('/', home, render_basic),
              ('/admin', list_campaigns, render_basic),
              ('/admin/<campaign>', get_campaign_admin, render_basic),
              ('/admin/<campaign>/<round>', get_round_admin, render_basic),
              ('/admin/<campaign>/<round>/preview',
               preview_selection,
               render_basic)]

    engine = create_engine('sqlite:///tmp_montage.db', echo=True)
    session_type = sessionmaker()
    session_type.configure(bind=engine)

    middlewares = [DBSessionMiddleware(session_type)]

    app = Application(routes, middlewares=middlewares)
    return app


if __name__ == '__main__':
    app = create_app()
    app.serve()
