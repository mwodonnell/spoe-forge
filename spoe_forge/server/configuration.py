import logging
from math import floor

from spoe_forge.server.constants import DEFAULT_MAX_FRAME_SIZE
from spoe_forge.server.constants import SPOE_CAPABILITIES
from spoe_forge.server.constants import SPOE_VERSION

logger = logging.getLogger(__name__)


class ServerConfiguration:
    """
    Manages SPOP protocol negotiation for a single connection.

    Fresh instance created per connection to negotiate version, capabilities,
    and max frame size with HAProxy.
    """

    _server_compatible: bool

    _max_frame_size: int
    _capabilities: list[str]
    _version: str

    def __init__(self, max_frame_size: int = DEFAULT_MAX_FRAME_SIZE) -> None:
        """
        Initialize server configuration with defaults.

        :param int max_frame_size: Maximum frame size to negotiate with HAProxy
        """
        self._version = SPOE_VERSION
        self._capabilities = []

        self._max_frame_size = (
            max_frame_size  # Set to default until negotiation complete
        )
        self._server_compatible = True

    async def _check_version_compatibility(self, ha_versions: list[str]):
        """
        Check if server version is compatible with HAProxy versions.

        :param list[str] ha_versions: Versions supported by HAProxy
        """
        float_ver = float(self._version)
        for version in ha_versions:
            float_ha_ver = float(version)
            if floor(float_ha_ver) != floor(float_ha_ver):
                continue

            if float_ver <= float_ha_ver:
                self._server_compatible = True
                return

        self._server_compatible = False
        logger.error(
            f"No compatible versions found for server compatibility. "
            f"Agent supports {self._version}. "
            f"HAProxy supports {', '.join(ha_versions)}."
        )

    async def _find_max_frame_size(self, ha_max_frame_size: int):
        """
        Negotiate maximum frame size with HAProxy.

        Takes the minimum of server and HAProxy frame sizes.

        :param int ha_max_frame_size: Maximum frame size supported by HAProxy
        """
        self._max_frame_size = min(ha_max_frame_size, self._max_frame_size)

        if self.max_frame_size <= 0:
            logger.error(
                f"Frame size negotiation failed: negotiated size {self._max_frame_size} is not positive"
            )
            self._server_compatible = False
            return

    async def _find_common_capabilities(self, ha_capabilities: list[str]):
        """
        Find common capabilities between server and HAProxy.

        :param list[str] ha_capabilities: Capabilities supported by HAProxy
        """
        self._capabilities = list(set(ha_capabilities) & set(SPOE_CAPABILITIES))

        if "pipelining" not in self._capabilities:
            logger.warning(
                "Pipelining capability is not supported by HAProxy. "
                "Req/Resp cycles may be slower than they could be."
            )

        # We don't set compatability here as pipelining is the only option available, and we support it w/o
        # changes to the system - instead just log a warning that HAProxy won't take advantage of it and
        # move on

    async def negotiate_server_compatibility(
        self,
        supported_versions: list[str],
        ha_max_frame_size: int,
        ha_capabilities: list[str],
    ) -> None:
        """
        Negotiate protocol compatibility with HAProxy.

        Checks version, frame size, and capabilities to determine if connection
        can proceed.

        :param list[str] supported_versions: Versions supported by HAProxy
        :param int ha_max_frame_size: Maximum frame size supported by HAProxy
        :param list[str] ha_capabilities: Capabilities supported by HAProxy
        """
        await self._check_version_compatibility(supported_versions)
        await self._find_max_frame_size(ha_max_frame_size)
        await self._find_common_capabilities(ha_capabilities)

    @property
    def is_compatible(self) -> bool:
        """Check if negotiation succeeded and connection is compatible."""
        return self._server_compatible

    @property
    def version(self) -> str:
        """Get negotiated SPOP protocol version."""
        return self._version

    @property
    def max_frame_size(self) -> int:
        """Get negotiated maximum frame size."""
        return self._max_frame_size

    @property
    def capabilities(self) -> list[str]:
        """Get negotiated capabilities shared by server and HAProxy."""
        return self._capabilities
