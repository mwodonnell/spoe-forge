import asyncio
from unittest.mock import AsyncMock, MagicMock

from spoe_forge.server.configuration import ServerConfiguration
from spoe_forge.server.handler import ForgeHandler


def create_stream_reader(data: bytes) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    reader.feed_eof()
    return reader


def create_mock_streams():
    """Create mock StreamReader and StreamWriter for testing."""
    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = MagicMock(spec=asyncio.StreamWriter)
    writer.is_closing = MagicMock(return_value=False)
    writer.close = MagicMock()
    writer.wait_closed = AsyncMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    return reader, writer


def create_handler(notify_handler=None, max_concurrent_frames: int = 100):
    """Create ForgeHandler with mocked dependencies."""
    if notify_handler is None:
        notify_handler = AsyncMock(return_value=[])

    config = ServerConfiguration()
    reader, writer = create_mock_streams()
    handler = ForgeHandler(
        notify_handler,
        config,
        reader,
        writer,
        max_concurrent_frames=max_concurrent_frames,
    )
    return handler, reader, writer
