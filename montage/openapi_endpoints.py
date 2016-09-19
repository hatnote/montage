
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
import json
import yaml
import collections
from pprint import pprint

from clastic import GET
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

    def format_spec_key(path, key, value):
        return str(key).lower().replace(' ', '_'), value

    # should remap have a maxdepth? technically len(p) gives you the depth
    spec_dict = remap(spec_dict, format_spec_key)

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

    def register_route(self, route):
        pass

    def register_all_routes(self, app, autofilter=True):
        warnings = []
        routes = app.routes
        for rt in routes:
            if autofilter and not rt.methods:
                warnings.append('skipping %r, has no methods specified' % rt)
                continue
            self.register_route(rt)
        return warnings

    def get_openapi_spec_dict(self):
        from collections import OrderedDict
        ret = OrderedDict()

        spec_paths = []
        spec_defs = []

        for path in self.paths:
            pass

        ret['swagger'] = '2.0'
        ret['host'] = self.host
        ret['basePath'] = self.base_path
        ret['schemes'] = self.schemes
        ret['consumes'] = self.consumes
        ret['produces'] = self.produces
        ret['info'] = {'version': self.api_version,
                       'title': self.title,
                       'description': self.description,
                       'contact': self.contact}
        ret['paths'] = spec_paths
        ret['definitions'] = spec_defs

        return ret

    def get_openapi_spec_yaml(self):
        return yaml.dump(self.get_openapi_spec_dict(),
                         default_flow_style=False)

    def get_openapi_spec_json(self):
        return json.dumps(self.get_openapi_spec_dict(), indent=2)


_mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG


def dict_representer(dumper, data):
    return dumper.represent_dict(data.iteritems())


def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))


yaml.add_representer(collections.OrderedDict, dict_representer)
yaml.add_constructor(_mapping_tag, dict_constructor)


if __name__ == '__main__':
    attach_api_schema(get_admin_campaign)

    sb = SchemaBroker()

    print sb.get_openapi_spec_yaml()
    print
    print sb.get_openapi_spec_json()
