import logging

from spoe_forge.spop.spop_types import SpoaDataType

logger = logging.getLogger(__name__)


class AgentContext:
    """
    Context object passed to message handlers containing message data.

    Provides access to message name and arguments from HAProxy NOTIFY frames.
    """

    def __init__(self, message: str, args: dict[str, SpoaDataType]):
        """
        Create a new agent context.

        :param str message: Message name from NOTIFY frame
        :param dict[str, SpoaDataType] args: Message arguments
        """
        self._message = message
        self._args = args

    def get_arg(self, arg: str, default: SpoaDataType = None) -> SpoaDataType:
        """
        Retrieve a message argument by name.

        :param str arg: Argument name to retrieve
        :param default: Default value to return if argument is not present.
        :return: Argument value, or None if not found
        """
        try:
            return self._args[arg]
        except KeyError:
            return default

    def get_args(self) -> dict[str, SpoaDataType]:
        """
        Retrieve all message arguments.

        :return: Dictionary mapping argument names to values
        """
        return self._args

    def has_arg(self, arg: str) -> bool:
        """
        Check if an argument exists in the message.

        :param str arg: Argument name to check
        :return: True if argument exists, False otherwise
        """
        return arg in self._args
