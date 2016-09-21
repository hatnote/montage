
from clastic.errors import Forbidden
from boltons.strutils import slugify

from rdb import JurorDAO


def get_juror_index(rdb_session, user):
    pass


def get_juror_rounds(rdb_session, user):
    juror_dao = JurorDAO(rdb_session=rdb_session, user=user)
    rounds = juror_dao.get_all_rounds()
    if len(rounds) == 0:
        raise Forbidden('not a juror for any rounds')
    info = [rnd.to_dict() for rnd in rounds]
    return info


def get_juror_campaign(rdb_session, user, campaign_id, camp_name):
    juror_dao = JurorDAO(rdb_session=rdb_session, user=user)
    campaign = juror_dao.get_campaign(campaign_id)
    if campaign is None:
        raise Forbidden('not a juror for this campaign')
    info = {'id': campaign.id,
            'name': campaign.name,
            'rounds': [],
            'coords': [u.username for u in campaign.coords]}
    for rnd in campaign.rounds:
        info['rounds'].append(get_juror_round(rdb_session, user, rnd.id))

    info['canonical_url_name'] = slugify(info['name'], '-')
    return info


def get_juror_round(rdb_session, user, round_id):
    juror_dao = JurorDAO(rdb_session=rdb_session, user=user)
    rnd = juror_dao.get_round(round_id)
    if rnd is None:
        raise Forbidden('not a juror for this round')
    info = rnd.to_dict()
    return info
