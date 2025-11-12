import logging


def init_logging() -> None:
    """
    Initialize logging configuration for SPOE Forge.

    Configures basic logging with INFO level and a standardized format.
    Output is sent to stderr via StreamHandler.
    """
    logging.basicConfig(
        format="%(levelname)s | %(asctime)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
        ],
        level=logging.INFO,
    )
