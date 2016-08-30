
def public(endpoint_func):
    """A simple decorator for skipping auth steps on certain endpoints,
    if it's a public page, for instance.
    """
    endpoint_func.is_public = True

    return endpoint_func
