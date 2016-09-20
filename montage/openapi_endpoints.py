
from clastic.errors import Forbidden
from boltons.strutils import slugify

from rdb import CoordinatorDAO
from server import get_admin_round

# TODO: support "required"

# TODO: clastic add a bind-time middleware callback (application
# creation fails unless middleware signs off on success)


def get_admin_campaign(rdb_session, user, campaign_id):
    """
    Some non-API related facts.

    # API spec

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
from boltons.strutils import under2camel
from boltons.iterutils import remap

_api_spec_start_re = re.compile('# API Spec', re.I)
_api_spec_end_re = re.compile('# End API Spec', re.I)


def extract_api_spec(func):
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

    return spec_dict


def _pprint_od(od):
    ded = remap(od, lambda p, k, v: (k, dict(v) if isinstance(v, dict) else v))
    pprint(ded)


class APISpecMiddleware(object):
    pass


class APISpecBroker(object):
    def __init__(self, title='', description='', contact_name='',
                 extra_defs=None):
        self.api_version = '0.1'
        self.title = title
        self.description = description
        self.contact = {'name': contact_name}

        self.host = 'localhost'
        self.base_path = '/'
        self.schemes = ['http']
        self.consumes = ['application/json']
        self.produces = ['application/json']

        self.routes = []
        self.path_map = collections.OrderedDict()

        self.def_map = collections.OrderedDict()
        if extra_defs:
            if isinstance(extra_defs, basestring):
                extra_defs = yaml.load(extra_defs)
                self.def_map.update(extra_defs)

        # TODO: base defs for error model etc.
        return

    def register_route(self, route, autoskip=True):
        warnings = []  # TODO: better warning system
        if route in self.routes:
            return warnings
        if autoskip and not route.methods:
            warnings.append('skipping %r, no methods specified' % route)
            return warnings
        endpoint_func = route.endpoint
        spec_dict = extract_api_spec(endpoint_func)
        if not spec_dict:
            return []  # TODO

        path = route.pattern  # TODO: curly-brace formatted
        op_id = route.endpoint.func_name
        cc_op_id = under2camel(op_id)

        _pprint_od(dict(spec_dict))

        param_list = []  # TODO: url path params

        req_def_name = spec_dict.get('request_model_name')
        if req_def_name:
            self.def_map[req_def_name] = None

        req_def = spec_dict.get('request_model')
        if req_def:
            default_req_def_name = '%sRequestModel' % (cc_op_id,)
            req_def_name = req_def_name or default_req_def_name
            req_param = {'name': op_id + '_request_message',
                         'in': 'body',
                         'description': 'JSON request message for %s' % op_id,
                         'required': True,
                         'schema': {'$ref': '#/definitions/' + req_def_name}}
            param_list.append(req_param)

            self.def_map[req_def_name] = req_def

        resp_map = collections.OrderedDict()

        resp_def_name = spec_dict.get('response_model_name')
        if resp_def_name:
            self.def_map[resp_def_name] = None

        resp_def = spec_dict.get('response_model')

        if resp_def:
            default_resp_def_name = '%sResponseModel' % (cc_op_id,)
            resp_def_name = resp_def_name or default_resp_def_name
            # TODO: response_summary?
            resp_dict = {'description': 'JSON response message for %s' % op_id,
                         'schema': {'$ref': '#/definitions/' + resp_def_name}}
            self.def_map[resp_def_name] = resp_def
            resp_map['200'] = resp_dict

        path_dict = {'description': spec_dict.get('summary', ''),
                     'operationId': op_id,
                     'produces': spec_dict.get('produces', self.produces),
                     'parameters': param_list,
                     'responses': resp_map}
        # TODO: errors

        for method in sorted(route.methods):
            if method == 'HEAD':
                continue
            m_dict = self.path_map.setdefault(path, collections.OrderedDict())
            m_dict[method] = path_dict
        self.routes.append(route)
        return []

    def register_app_routes(self, app, autoskip=True):
        warnings = []
        for rt in app.routes:
            ws = self.register_route(rt, autoskip=autoskip)
            warnings.extend(ws)
        return warnings

    def resolve(self):
        unresolved_models = []
        for name, defn in self.def_map.items():
            if defn is None:
                unresolved_models.append(defn)
        if unresolved_models:
            raise ValueError('no definitions found for models: %r'
                             % unresolved_models)

        for route in self.routes:
            pass
        return

    def get_openapi_spec_dict(self):
        ret = collections.OrderedDict()

        self.resolve()

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
        ret['paths'] = self.path_map
        ret['definitions'] = self.def_map

        return ret

    def get_openapi_spec_yaml(self):
        return dump_yaml(self.get_openapi_spec_dict())

    def get_openapi_spec_json(self):
        return json.dumps(self.get_openapi_spec_dict(), indent=2)


# set up yaml pretty printing

_mapping_tag = yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG


def dict_representer(dumper, data):
    return dumper.represent_dict(data.iteritems())


def dict_constructor(loader, node):
    return collections.OrderedDict(loader.construct_pairs(node))


yaml.add_representer(collections.OrderedDict, dict_representer)
yaml.add_constructor(_mapping_tag, dict_constructor)

# disable reference/alias emission


class ExplicitDumper(yaml.Dumper):
    """
    A dumper that will never emit aliases.
    """
    def ignore_aliases(self, data):
        return True


def dump_yaml(*a, **kw):
    kw['Dumper'] = ExplicitDumper

    # always dump in characteristic yaml block style
    kw['default_flow_style'] = False
    return yaml.dump(*a, **kw)

# end yaml customization


if __name__ == '__main__':
    # attach_api_schema(get_admin_campaign)

    route = GET('/admin/campaign', get_admin_campaign)

    sb = APISpecBroker()

    sb.register_route(route)
    sb.resolve()

    print sb.get_openapi_spec_yaml()
    sb.get_openapi_spec_json()

    from bravado_core.spec import Spec
    spec = Spec(sb.get_openapi_spec_dict())

    import pdb;pdb.set_trace()
