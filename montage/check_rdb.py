
from sqlalchemy import exc
from sqlalchemy import event
from sqlalchemy import select
from sqlalchemy import inspect
from sqlalchemy.ext.declarative.clsregistry import _ModuleMarker
from sqlalchemy.orm import RelationshipProperty


def get_schema_errors(base_type, session):
    """Check whether the current database matches the models declared in
    model base.

    Currently we check that all tables exist with all columns. What is
    not checked:

    * Column types are not verified
    * Relationships are not verified at all (TODO)

    :param base_type: Declarative base type for SQLAlchemy models to check
    :param session: SQLAlchemy session bound to an engine
    :return: True if all declared models have corresponding tables and columns.
    """
    # based on http://stackoverflow.com/a/30653553/178013

    engine = session.get_bind()
    iengine = inspect(engine)

    errors = []

    tables = iengine.get_table_names()

    # Go through all SQLAlchemy models
    for name, model_type in base_type._decl_class_registry.items():

        if isinstance(model_type, _ModuleMarker):
            # Not a model
            continue

        table = model_type.__tablename__
        if table not in tables:
            errors.append("Model %s table %s missing from database %s"
                          % (model_type, table, engine))
            continue

        # Check all columns are found
        # Looks like:
        # [{'default': "nextval('sanity_check_test_id_seq'::regclass)",
        # 'autoincrement': True, 'nullable': False, 'type':
        # INTEGER(), 'name': 'id'}]

        columns = [c["name"] for c in iengine.get_columns(table)]
        mapper = inspect(model_type)

        for column_prop in mapper.attrs:
            if isinstance(column_prop, RelationshipProperty):
                # TODO: Add sanity checks for relations
                pass
            else:
                for column in column_prop.columns:
                    # Assume normal flat column
                    if column.key in columns:
                        continue
                    errors.append("Model %s missing column %s from database %s"
                                  % (model_type, column.key, engine))

    return errors


def ping_connection(connection, branch):
    # from: http://docs.sqlalchemy.org/en/latest/core/pooling.html#disconnect-handling-pessimistic

    if branch:
        # "branch" refers to a sub-connection of a connection,
        # we don't want to bother pinging on these.
        return

    # turn off "close with result".  This flag is only used with
    # "connectionless" execution, otherwise will be False in any case
    save_should_close_with_result = connection.should_close_with_result
    connection.should_close_with_result = False

    try:
        # run a SELECT 1.   use a core select() so that
        # the SELECT of a scalar value without a table is
        # appropriately formatted for the backend
        connection.scalar(select([1]))
    except exc.DBAPIError as err:
        # catch SQLAlchemy's DBAPIError, which is a wrapper
        # for the DBAPI's exception.  It includes a .connection_invalidated
        # attribute which specifies if this connection is a "disconnect"
        # condition, which is based on inspection of the original exception
        # by the dialect in use.
        if err.connection_invalidated:
            # run the same SELECT again - the connection will re-validate
            # itself and establish a new connection.  The disconnect detection
            # here also causes the whole connection pool to be invalidated
            # so that all stale connections are discarded.
            connection.scalar(select([1]))
        else:
            raise
    finally:
        # restore "close with result"
        connection.should_close_with_result = save_should_close_with_result
    return
