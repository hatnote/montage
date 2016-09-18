
from clastic.errors import Forbidden
from boltons.strutils import slugify

from rdb import CoordinatorDAO
from server import get_admin_round

# TODO: flex

def get_admin_campaign(rdb_session, user, campaign_id):
    """
    Some non-API related facts.

    # API spec

    Summary: Get admin-level details for a campaign, identified by campaign ID.

    Request message:
       - name: campaign_id
         type: int64
         required: true

    Response model name: CampaignDetails
    Response model:
       - name: id
         type: int64
       - name: name
         type: string
       - name: rounds
         type: array
         items:
           type: RoundDetails
       - name: coordinators
         type: array
         items:
           type: CoordDetails
       - name: url_name
         type: string

    Errors:
       403: User does not have permission to access requested campaign
       404: Campaign not found

    # End API spec

    More facts
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


models = """
"""

######

import re
import yaml
from pprint import pprint
from boltons.iterutils import remap

_api_spec_start_re = re.compile('# API Spec', re.I)
_api_spec_end_re = re.compile('# End API Spec', re.I)


def attach_api_schema(func):
    parts = _api_spec_start_re.split(func.__doc__, maxsplit=1)
    if len(parts) == 1:
        # no match found, continuing
        return None
    elif len(parts) > 2:
        raise ValueError('expected only one API Spec section')

    spec_to_end = parts[1]

    spec_text = _api_spec_end_re.split(spec_to_end)[0]

    spec_dict = yaml.load(spec_text)

    def format_spec_key(key):
        return key.lower().replace(' ', '_') if hasattr(key, 'lower') else key

    # should remap have a maxdepth? technically len(p) gives you the depth
    spec_dict = remap(spec_dict,
                      lambda p, k, v: (format_spec_key(k), v))

    # pprint(spec_dict)

    func.spec_dict = spec_dict

    return spec_dict


class SchemaBroker(object):
    def __init__(self):
        self.api_version = '0.1'
        self.title = ''
        self.description = ''
        self.contact = ''  # TODO name/etc.?

        self.host = ''
        self.base_path = '/'
        self.schemes = ['http']
        self.consumes = ['application/json']
        self.produces = ['application/json']

        self.paths = []

        """
        example_path = {'get': {'description': '',
                                'operationId': 'get_rounds',
                                'produces': ['application/json'],
                                'parameters': [{'name': '<request_message_name>',
                                                'in': 'body',
                                                'description': '...',
                                                'required': True,
                                                'schema': {'$ref': '#/definitions/RoundRequestInfo'}}]}}
        """

        self.definitions = {}

    def register_endpoint_func(self, ep_func):
        pass

    def get_openapi_spec(self, fmt=None):
        spec_paths = []

        for path in self.paths:
            pass

        spec_root = {'swagger': '2.0',
                     'info': {'version': self.api_version,
                              'title': self.title,
                              'description': self.description,
                              'contact': self.contact}
                     'host': self.host,
                     'basePath': self.base_path,
                     'schemes': self.schemes,
                     'consumes': self.consumes,
                     'produces': self.produces}



if __name__ == '__main__':
    attach_api_schema(get_admin_campaign)
