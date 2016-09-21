
from clastic.errors import Forbidden
from boltons.strutils import slugify

from rdb import Campaign, CoordinatorDAO


ROOT_ADMINS = ['MahmoudHashemi', 'Slaporte', 'Yarl']


def create_campaign(user, rdb_session, request_dict):
    if user.username not in ROOT_ADMINS:
        raise Forbidden('only a root admin can create a campaign')  # for now
    camp = Campaign(name=request_dict['name'])
    rdb_session.add(camp)
    rdb_session.commit()
    return {'data': camp.to_dict()}


def edit_campaign(user_dao, campaign_id, request_dict):
    pass


def create_round(user_dao, request_dict):
    pass


def edit_round(user_dao, round_id, request_dict):
    pass


def get_admin_index(rdb_session, user):
    """
    Summary: Get admin-level details for all campaigns.

    Response model name: CampaignIndex
    Response model:
        campaigns:
            type: array
            items: 
                type: CampaignDetails

    Errors:
       403: User does not have permission to access any campaigns
    """
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    campaigns = coord_dao.get_all_campaigns()
    if len(campaigns) == 0:
        raise Forbidden('not a coordinator on any campaigns')
    data = []
    for campaign in campaigns:
        camp = get_admin_campaign(rdb_session, user, campaign.id)
        data.append(camp)
    return data


def get_admin_campaign(rdb_session, user, campaign_id):
    """
    Summary: Get admin-level details for a campaign, identified by campaign ID.

    Request model:
        campaign_id:
            type: int64

    Response model name: CampaignDetails
    Response model:
        id:
            type: int64
        name:
            type: string
        rounds:
            type: array
            items:
                type: RoundDetails
        coordinators:
            type: array
            items:
                type: CoordDetails
        url_name:
            type: string

    Errors:
       403: User does not have permission to access requested campaign
       404: Campaign not found
    """
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    campaign = coord_dao.get_campaign(campaign_id)
    if campaign is None:
        raise Forbidden('not a coordinator on this campaign')
    info = {'id': campaign.id,
            'name': campaign.name,
            'rounds': [],
            'coords': [u.username for u in campaign.coords]}
    for rnd in campaign.rounds:
        info['rounds'].append(get_admin_round(rdb_session, user, rnd.id))

    info['canonical_url_name'] = slugify(info['name'], '-')

    return info


def get_admin_round(rdb_session, user, round_id):
    """
    Summary: Get admin-level details for a round, identified by round ID.

    Request model:
        round_id:
            type: int64

    Response model name: RoundDetails
    Response model:
        id:
            type: int64
        name:
            type: string
        url_name:
            type: string
        vote_method:
            type: string
        status:
            type: string
        jurors:
            type: array
            items:
                type: UserDetails
        quorum:
            type: int64
        close_date:
            type: date-time
        campaign:
            type: CampaignInfo

    Errors:
       403: User does not have permission to access requested round
       404: Round not found
    """
    coord_dao = CoordinatorDAO(rdb_session=rdb_session, user=user)
    rnd = coord_dao.get_round(round_id)
    if rnd is None:
        raise Forbidden('not a coordinator for this round')
    # entries_info = user_dao.get_entry_info(round_id) # TODO

    # TODO: joinedload if this generates too many queries
    jurors = [{'username': rj.user.username,
               'id': rj.user.id,
               'active': rj.is_active} for rj in rnd.round_jurors]

    info = {'id': rnd.id,
            'name': rnd.name,
            'voteMethod': rnd.vote_method,
            'status': rnd.status,
            'jurors': jurors,
            'quorum': rnd.quorum,
            'sourceInfo': {
                'entryCount': None,
                'uploadersCount': None,
                'roundSource': {'id': None,
                                'title': None}},
            'closeDate': rnd.close_date,
            'campaign': rnd.campaign_id}

    info['canonical_url_name'] = slugify(info['name'], '-')

    return info


# - cancel round
# - update round
#   - no reassignment required: name, description, directions, display_settings
#   - reassignment required: quorum, active_jurors
#   - not updateable: id, open_date, close_date, vote_method, campaign_id/seq