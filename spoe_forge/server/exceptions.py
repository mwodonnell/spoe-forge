class CloseConnection(Exception):
    """
    Internal control-flow signal: stop reading and cancel in-flight NOTIFY tasks.

    Deliberately not a SpoeForgeError - the protocol-error handlers in
    core_handler must never catch it, since it marks a graceful close, not a
    failure. Never raised across the server package boundary.
    """
