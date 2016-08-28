
import datetime
from json import JSONEncoder

from sqlalchemy import inspect
from sqlalchemy.orm.state import InstanceState


class EntityJSONEncoder(JSONEncoder):
    """ JSON encoder for custom classes:

        Uses __json__() method if available to prepare the object.
        Especially useful for SQLAlchemy models
    """
    def __init__(self, *a, **kw):
        self.eager = kw.pop(eager, False)
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
    ins = entity if isinstance(entity, InstanceState) else inspect(entity)
    return set(ins.mapper.column_attrs.keys() + ins.mapper.relationships.keys())


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
