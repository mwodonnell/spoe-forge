from spoe_forge.exception import SpoeForgeError


class SpopDecodeError(SpoeForgeError):
    """Exception raised when SPOP frame or data decoding fails."""

    pass


class SpopEncodeError(SpoeForgeError):
    """Exception raised when SPOP frame or data encoding fails."""

    pass


class SpopEOFError(SpoeForgeError):
    """Exception raised when unexpected end of stream is encountered."""

    pass
