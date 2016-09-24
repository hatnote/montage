
import json
import datetime

from sqlalchemy import inspect
from sqlalchemy.types import TypeDecorator, Text
from sqlalchemy.ext.mutable import Mutable


from sqlalchemy.orm.state import InstanceState


class EntityJSONEncoder(json.JSONEncoder):
    """ JSON encoder for custom classes:

        Uses __json__() method if available to prepare the object.
        Especially useful for SQLAlchemy models
    """
    def __init__(self, *a, **kw):
        self.eager = kw.pop('eager', False)
        super(EntityJSONEncoder, self).__init__(*a, **kw)

    def default(self, o):
        if callable(getattr(o, 'to_json', None)):
            return o.to_json(eager=self.eager)

        return super(EntityJSONEncoder, self).default(o)


def get_entity_propnames(entity):
    """ Get entity property names

       :param entity: Entity
        :type entity: sqlalchemy.ext.declarative.api.DeclarativeMeta
        :returns: Set of entity property names
        :rtype: set
    """
    e = entity if isinstance(entity, InstanceState) else inspect(entity)
    ret = set(e.mapper.column_attrs.keys() + e.mapper.relationships.keys())

    type_props = [a for a in dir(entity.object)
                  if isinstance(getattr(entity.object.__class__, a, None), property)]
    ret |= set(type_props)
    return ret


def get_entity_loaded_propnames(entity):
    """ Get entity property names that are loaded (e.g. won't produce new queries)

        :param entity: Entity
        :type entity: sqlalchemy.ext.declarative.api.DeclarativeMeta
        :returns: Set of entity property names
        :rtype: set
    """
    ins = inspect(entity)
    keynames = get_entity_propnames(ins)

    # If the entity is not transient -- exclude unloaded keys
    # Transient entities won't load these anyway, so it's safe to
    # include all columns and get defaults
    if not ins.transient:
        keynames -= ins.unloaded

    # If the entity is expired -- reload expired attributes as well
    # Expired attributes are usually unloaded as well!
    if ins.expired:
        keynames |= ins.expired_attributes

    # Finish
    return keynames


class DictableBase(object):
    "Declarative Base mixin to allow objects serialization"

    def to_dict(self, eager=False, excluded=frozenset()):
        "This is called by clastic's json renderer"
        if eager:
            prop_names = get_entity_propnames(self)
        else:
            prop_names = get_entity_loaded_propnames(self)

        items = []
        for attr_name in prop_names - excluded:
            val = getattr(self, attr_name)

            if isinstance(val, datetime.datetime):
                val = val.isoformat()
            items.append((attr_name, val))
        return dict(items)

    def __repr__(self):
        prop_names = [col.name for col in self.__table__.c]

        parts = []
        for name in prop_names[:2]:  # TODO: configurable
            val = repr(getattr(self, name))
            if len(val) > 40:
                val = val[:37] + '...'
            parts.append('%s=%s' % (name, val))

        if not parts:
            return object.__repr__(self)

        cn = self.__class__.__name__
        return '<%s %s>' % (cn, ' '.join(parts))


class JSONEncodedDict(TypeDecorator):
    impl = Text

    def process_bind_param(self, value, dialect):
        if value is None:
            value = {}
        return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            value = '{}'
        return json.loads(value)


class MutableDict(Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutableDict."

        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        "Detect dictionary set events and emit change events."
        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."
        dict.__delitem__(self, key)
        self.changed()


MutableDict.associate_with(JSONEncodedDict)
