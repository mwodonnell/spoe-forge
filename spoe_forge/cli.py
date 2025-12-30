import argparse
import asyncio
import sys

from spoe_forge.exception import SpoeForgeError
from spoe_forge.log import create_logger
from spoe_forge.spop.constants import FrameType
from spoe_forge.spop.frame import Frame

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8500
DEFAULT_FRAME_SIZE = 1024 * 4

logger = create_logger(debug=False)


async def healthcheck(host: str, port: int, quiet: bool) -> bool:
    """
    Perform a full SPOP protocol handshake check.

    Mimics HAProxy's healthcheck behavior by sending HAPROXY_HELLO
    with healthcheck flag and expecting AGENT_HELLO response.

    :param str host: Target host
    :param int port: Target port
    :param bool quiet: Suppress output
    :return: True if protocol handshake successful, False otherwise
    """
    try:
        # Open connection with timeout
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=5.0
        )

        # Construct HAPROXY_HELLO frame with healthcheck flag
        haproxy_hello = await Frame.construct(
            frame_type=FrameType.HAPROXY_HELLO,
            stream_id=0,
            frame_id=0,
            supported_versions=["2.0"],
            max_frame_size=DEFAULT_FRAME_SIZE,
            capabilities=["pipelining"],
            healthcheck=True,
        )

        writer.write(await haproxy_hello.encode(DEFAULT_FRAME_SIZE))
        await writer.drain()

        agent_hello = await asyncio.wait_for(Frame.decode(reader), timeout=5.0)

        writer.close()
        await writer.wait_closed()

        if agent_hello.frame_type != FrameType.AGENT_HELLO:
            if not quiet:
                logger.error(
                    f"Health check failed: unexpected response {agent_hello.frame_type.name}"
                )
            return False

        return True

    except (OSError, asyncio.TimeoutError, SpoeForgeError) as e:
        if not quiet:
            logger.error(f"Health check failed: {e}")
        return False


def healthcheck_command(args: argparse.Namespace) -> int:
    result = asyncio.run(healthcheck(args.host, args.port, args.quiet))

    if not result:
        return 1

    if not args.quiet:
        logger.info("Health check passed")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="spoe-forge",
        description="SPOE Forge CLI utilities",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Healthcheck command
    healthcheck_parser = subparsers.add_parser(
        "healthcheck",
        help="Check health of SPOE agent",
        description="Perform health check on SPOE agent using TCP or SPOP protocol validation",
    )
    healthcheck_parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Target host (default: {DEFAULT_HOST})",
    )
    healthcheck_parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Target port (default: {DEFAULT_PORT})",
    )
    healthcheck_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output (only exit codes)",
    )
    healthcheck_parser.set_defaults(func=healthcheck_command)

    args = parser.parse_args()
    if hasattr(args, "func"):
        return args.func(args)

    parser.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
