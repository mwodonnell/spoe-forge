import logging
import sys


_default_handler = logging.StreamHandler(sys.stderr)
_default_handler.setFormatter(
    logging.Formatter("%(levelname)s | %(asctime)s | %(name)s | %(message)s")
)


def _has_level_handler(logger: logging.Logger) -> bool:
    """
    Check if there is a handler in the logging chain that will handle the
    given logger's effective level.

    This traverses the logger hierarchy to check if any parent logger
    has a handler configured. Based on Flask's implementation.

    :param logger: Logger to check
    :return: True if a handler exists in the chain, False otherwise
    """
    level = logger.getEffectiveLevel()
    current = logger

    while current:
        if any(handler.level <= level for handler in current.handlers):
            return True

        if not current.propagate:
            break

        current = current.parent

    return False


def create_logger(debug: bool = False) -> logging.Logger:
    """
    Get the SPOE Forge logger and configure it if needed.

    This follows Flask's pattern:
    - Uses 'spoe_forge' as the logger name
    - Only adds default handler if no handler exists in the hierarchy
    - Respects existing logging configuration

    Internal function - called by spoe_forge.py at import time.

    :return: Configured logger instance
    """
    logger = logging.getLogger("spoe_forge")

    # Only add handler if none exists in the hierarchy
    if not _has_level_handler(logger):
        logger.addHandler(_default_handler)

    # Set default level if not already set
    if not logger.level:
        logger.setLevel(logging.DEBUG if debug else logging.INFO)

    return logger
