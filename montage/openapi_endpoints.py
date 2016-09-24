
import clastic
from clastic.errors import Forbidden, BadRequest
from boltons.strutils import slugify

from rdb import CoordinatorDAO
from server import get_admin_round

# TODO: support "required"

# TODO: clastic add a bind-time middleware callback (application
# creation fails unless middleware signs off on success)


def get_admin_campaign():  # rdb_session, user, campaign_id):
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


######

import re
import json
import yaml
import collections
from pprint import pprint

from clastic import POST
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


from clastic import BaseResponse, render_basic
from boltons.tbutils import ExceptionInfo


class SpecMessageMiddleware(clastic.Middleware):
    provides = ('response_dict', 'request_dict')

    def __init__(self, spec_broker, raise_errors=True, lint_responses=True):
        self.spec_broker = spec_broker
        self.raise_errors = raise_errors
        self.lint_responses = lint_responses

    def request(self, next, request, _route):
        response_dict = {'errors': [], 'status': 'success'}

        request_model_name = getattr(_route, 'request_model_name', None)
        try:
            request_data = request.get_data()
            request_dict = json.loads(request_data)
        except Exception:
            if request_model_name:
                raise BadRequest('failed to load JSON request data')
            request_dict = None

        if request_model_name:
            request_model = self.spec_broker.def_map[request_model_name]
            print request_model

        return next(response_dict=response_dict, request_dict=request_dict)

    def endpoint(self, next, response_dict, request, _route):
        # TODO: autoswitch resp status code
        try:
            ret = next()
        except Exception:
            if self.raise_errors:
                raise
            ret = None
            exc_info = ExceptionInfo.from_current()
            err = '%s: %s' % (exc_info.exc_type, exc_info.exc_msg)
            response_dict['errors'].append(err)
            response_dict['status'] = 'exception'
        else:
            if response_dict.get('errors'):
                response_dict['status'] = 'failure'

        if isinstance(ret, BaseResponse):
            # preserialized responses (and 404s, etc.)  TODO: log that
            # we're skipping over response_dict if the response status
            # code == 2xx
            # TODO: autoserialize body if no body is set
            return ret
        elif isinstance(ret, dict):
            response_dict.update(ret)
        else:
            response_dict.update({'data': ret})

        return render_basic(context=response_dict,
                            request=request,
                            _route=_route)


class APISpecBroker(object):
    def __init__(self,
                 title='',
                 description='',
                 contact_name='',
                 response_wrapper_name=None,
                 response_wrapper_key=None,
                 extra_defs=None):
        # TODO: request wrapper
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

        self.response_wrapper = None
        self.response_wrapper_key = response_wrapper_key
        self.response_wrapper_name = response_wrapper_name

        if response_wrapper_name:
            try:
                response_wrapper = self.def_map[response_wrapper_name]
            except KeyError:
                raise ValueError('response wrapper %r not found in extra_defs'
                                 % response_wrapper_name)
            # TODO: assert response_wrapper_key in response_wrapper
            self.response_wrapper = response_wrapper

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

            self.def_map[req_def_name] = {'properties': req_def}
        route.request_model_name = req_def_name

        resp_map = collections.OrderedDict()

        resp_def_name = spec_dict.get('response_model_name')
        if resp_def_name:
            self.def_map[resp_def_name] = None

        resp_def = spec_dict.get('response_model')

        if resp_def:
            default_resp_def_name = '%sResponseModel' % (cc_op_id,)
            resp_def_name = resp_def_name or default_resp_def_name
            # TODO: response_summary?
            resp_dict = {}  # 'description': 'JSON response message for %s' % op_id}

            self.def_map[resp_def_name] = {'properties': resp_def}
            if self.response_wrapper:
                wrapper_name = '%sResponseWrapper' % (cc_op_id,)
                resp_wrapper = dict(self.response_wrapper)
                wrapper_dict = {'type': 'object',
                                'schema':
                                {'$ref': '#/definitions/' + resp_def_name}}
                resp_wrapper[self.response_wrapper_key] = wrapper_dict
                self.def_map[wrapper_name] = {'properties': resp_wrapper}
                schema_name = wrapper_name
            else:
                schema_name = resp_def_name

            resp_dict['schema'] = {'$ref': '#/definitions/' + schema_name}
            resp_map['200'] = resp_dict
        route.response_model_name = resp_def_name

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
            m_dict[method.lower()] = path_dict
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

        """
        >>> jsonschema.validators.Draft4Validator.DEFAULT_TYPES.keys()
        [u'boolean', u'string', u'integer', u'array', u'object', u'null', u'number']

        bravad_core.SWAGGER_PRIMITIVES is that, minus object/array

        all "type" keys should map to one of those or something in #/definitions/
        """
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

        from bravado_core.spec import Spec
        self.spec = Spec(ret)

        # spec.resolver.resolve('#/definitions/UserInfo')

        #from bravado_core.validate import validate_schema_object

        #uinfo = self.spec.resolver.resolve('#/definitions/UserInfo')[1]
        #validate_schema_object(self.spec,
        #                      uinfo,
        #                       {})

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
    return dict(loader.construct_pairs(node))
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

    route = POST('/admin/campaign', get_admin_campaign)

    BASE_DEFS = """
    BaseResponseWrapper:
        properties:
            status:
                type: string
            user:
                type: object
                schema:
                    $ref: #/definitions/UserInfo
            data:
                type: object
            errors:
                type: array
                items:
                    type: string

    UserInfo:
        properties:
            type: object
            id:
                type: int64
            username:
                type: string
            created_by:
                type: string
            is_organizer:
                type: bool
            create_date:
                type: string
                format: date-time
            last_login_date:
                type: string
                format: date-time
    """

    sb = APISpecBroker(response_wrapper_name='BaseResponseWrapper',
                       response_wrapper_key='data',
                       extra_defs=BASE_DEFS)

    sb.register_route(route)
    # sb.resolve()

    print sb.get_openapi_spec_yaml()
    sb.get_openapi_spec_json()


    app = clastic.Application([route],
                              middlewares=[SpecMessageMiddleware(sb)])

    #app.serve()

    import pdb;pdb.set_trace()
