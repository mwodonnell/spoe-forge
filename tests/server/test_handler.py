import struct
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from spoe_forge.exception import SpoeForgeError
from spoe_forge.server.configuration import ServerConfiguration
from spoe_forge.server.constants import DisconnectCode
from spoe_forge.server.handler import ForgeHandler
from spoe_forge.spop.constants import ActionScope
from spoe_forge.spop.constants import FrameType
from spoe_forge.spop.exception import SpopEncodeError
from spoe_forge.spop.exception import SpopEOFError
from spoe_forge.spop.exception import SpopFrameTooBigError
from spoe_forge.spop.frame import Disconnect
from spoe_forge.spop.frame import Frame
from spoe_forge.spop.spop_types import SetVarAction
from tests.utils import create_mock_streams, create_handler, create_stream_reader


def test_handler_initialization():
    notify_handler = AsyncMock()
    config = ServerConfiguration()
    reader, writer = create_mock_streams()

    handler = ForgeHandler(notify_handler, config, reader, writer)

    assert handler.notify_handler == notify_handler
    assert handler.config == config
    assert handler.reader == reader
    assert handler.writer == writer


@pytest.mark.asyncio
async def test_close_connection_closes_writer():
    handler, reader, writer = create_handler()

    await handler.close_connection()

    writer.close.assert_called_once()
    writer.wait_closed.assert_called_once()


@pytest.mark.asyncio
async def test_close_connection_skips_if_already_closing():
    handler, reader, writer = create_handler()
    writer.is_closing.return_value = True

    await handler.close_connection()

    writer.close.assert_not_called()
    writer.wait_closed.assert_called_once()


@pytest.mark.asyncio
async def test_send_frame_success():
    handler, reader, writer = create_handler()

    test_frame = Frame.construct(
        FrameType.ACK,
        stream_id=1,
        frame_id=1,
        actions=[],
    )

    result = await handler.send_frame(test_frame)

    assert result is True
    writer.write.assert_called_once()
    writer.drain.assert_called_once()


@pytest.mark.asyncio
async def test_send_frame_fails_when_stream_closed():
    handler, reader, writer = create_handler()
    writer.is_closing.return_value = True

    test_frame = Frame.construct(
        FrameType.ACK,
        stream_id=1,
        frame_id=1,
        actions=[],
    )

    with patch("spoe_forge.server.handler.logger") as mock_logger:
        result = await handler.send_frame(test_frame)

        assert result is False
        writer.write.assert_not_called()
        mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_send_frame_raises_when_frame_too_big():
    handler, reader, writer = create_handler()

    large_messages = [(f"msg{i}", {"arg": i}) for i in range(1000)]
    test_frame = Frame.construct(
        FrameType.NOTIFY,
        stream_id=1,
        frame_id=1,
        messages=large_messages,
    )

    handler.config._max_frame_size = 100

    with pytest.raises(SpopFrameTooBigError):
        await handler.send_frame(test_frame)

    writer.write.assert_not_called()


@pytest.mark.asyncio
async def test_send_frame_returns_false_on_encode_error():
    handler, reader, writer = create_handler()

    test_frame = Frame.construct(
        FrameType.ACK,
        stream_id=1,
        frame_id=1,
        actions=[],
    )

    with (
        patch.object(test_frame, "encode", side_effect=SpopEncodeError("boom")),
        patch("spoe_forge.server.handler.logger") as mock_logger,
    ):
        result = await handler.send_frame(test_frame)

        assert result is False
        writer.write.assert_not_called()
        mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_core_handler_disconnects_on_oversized_inbound_frame():
    handler, reader, writer = create_handler()
    handler.reader = create_stream_reader(struct.pack("!I", 100_000))

    with patch("spoe_forge.server.handler.logger"):
        await handler.core_handler()

    written = writer.write.call_args[0][0]
    disconnect = await Frame.decode(create_stream_reader(written), 4096)

    assert isinstance(disconnect, Disconnect)
    assert disconnect.status_code == DisconnectCode.FRAME_TOO_BIG
    writer.close.assert_called_once()


@pytest.mark.asyncio
async def test_send_disconnect_constructs_and_sends_frame():
    handler, reader, writer = create_handler()

    result = await handler.send_disconnect(DisconnectCode.NORMAL, "Test message")

    assert result is True
    writer.write.assert_called_once()
    writer.drain.assert_called_once()


@pytest.mark.asyncio
async def test_send_disconnect_uses_correct_status_code():
    handler, reader, writer = create_handler()

    await handler.send_disconnect(DisconnectCode.PROTOCOL_ERROR, "Protocol error")

    writer.write.assert_called_once()


@pytest.mark.asyncio
async def test_send_disconnect_on_error_logs_error():
    handler, reader, writer = create_handler()

    with patch("spoe_forge.server.handler.logger") as mock_logger:
        await handler.send_disconnect_on_error(
            DisconnectCode.PROTOCOL_ERROR, "Test error"
        )

        mock_logger.error.assert_called_once()
        assert "SPOA server encountered an error" in mock_logger.error.call_args[0][0]


@pytest.mark.asyncio
async def test_send_disconnect_on_error_sends_disconnect():
    handler, reader, writer = create_handler()

    with patch("spoe_forge.server.handler.logger"):
        result = await handler.send_disconnect_on_error(
            DisconnectCode.IO_ERROR, "IO failed"
        )

        assert result is True
        writer.write.assert_called_once()


@pytest.mark.asyncio
async def test_handle_handshake_success():
    handler, reader, writer = create_handler()

    haproxy_hello = Frame.construct(
        FrameType.HAPROXY_HELLO,
        stream_id=0,
        frame_id=0,
        supported_versions=["2.0"],
        max_frame_size=16384,
        capabilities=["pipelining"],
        healthcheck=False,
    )

    with patch.object(Frame, "decode", return_value=haproxy_hello):
        result = await handler.handle_handshake()

        assert result is True
        assert handler.config.is_compatible is True
        writer.write.assert_called_once()  # AGENT_HELLO sent


@pytest.mark.asyncio
async def test_handle_handshake_rejects_wrong_frame_type():
    handler, reader, writer = create_handler()

    notify = Frame.construct(
        FrameType.NOTIFY,
        stream_id=1,
        frame_id=1,
        messages=[],
    )

    with (
        patch.object(Frame, "decode", return_value=notify),
        patch("spoe_forge.server.handler.logger"),
    ):
        result = await handler.handle_handshake()

        assert result is False
        # Should send disconnect
        assert writer.write.call_count >= 1


@pytest.mark.asyncio
async def test_handle_handshake_fails_on_incompatibility():
    handler, reader, writer = create_handler()

    haproxy_hello = Frame.construct(
        FrameType.HAPROXY_HELLO,
        stream_id=0,
        frame_id=0,
        supported_versions=["2.0"],
        max_frame_size=16384,
        capabilities=["pipelining"],
        healthcheck=False,
    )

    with (
        patch.object(Frame, "decode", return_value=haproxy_hello),
        patch("spoe_forge.server.handler.logger") as mock_logger,
    ):
        original_negotiate = handler.config.negotiate_server_compatibility

        def mock_negotiate(*args, **kwargs):
            original_negotiate(*args, **kwargs)
            handler.config._server_compatible = False

        with patch.object(
            handler.config, "negotiate_server_compatibility", side_effect=mock_negotiate
        ):
            result = await handler.handle_handshake()

            assert result is False
            assert any(
                "SPOA server encountered an error" in str(call)
                for call in mock_logger.error.call_args_list
            )


@pytest.mark.asyncio
async def test_handle_handshake_closes_on_healthcheck():
    handler, reader, writer = create_handler()

    haproxy_hello = Frame.construct(
        FrameType.HAPROXY_HELLO,
        stream_id=0,
        frame_id=0,
        supported_versions=["2.0"],
        max_frame_size=16384,
        capabilities=["pipelining"],
        healthcheck=True,  # Health check!
    )

    with (
        patch.object(Frame, "decode", return_value=haproxy_hello),
        patch("spoe_forge.server.handler.logger") as mock_logger,
    ):
        result = await handler.handle_handshake()

        assert result is False
        writer.write.assert_called_once()
        mock_logger.debug.assert_called()
        assert any(
            "Healthcheck" in str(call) for call in mock_logger.debug.call_args_list
        )


@pytest.mark.asyncio
async def test_handle_notify_cycle_success():
    notify_handler = AsyncMock(
        return_value=[SetVarAction(scope=ActionScope.SESSION, name="test", value=42)]
    )
    handler, reader, writer = create_handler(notify_handler)

    notify = Frame.construct(
        FrameType.NOTIFY,
        stream_id=1,
        frame_id=1,
        messages=[("test", {"arg": "value"})],
    )

    with patch.object(Frame, "decode", return_value=notify):
        result = await handler.handle_notify_cycle()

        assert result is True
        notify_handler.assert_called_once_with([("test", {"arg": "value"})])
        writer.write.assert_called_once()  # ACK sent


@pytest.mark.asyncio
async def test_handle_notify_cycle_handles_eof():
    handler, reader, writer = create_handler()

    with patch.object(Frame, "decode", side_effect=SpopEOFError()):
        with patch("spoe_forge.server.handler.logger") as mock_logger:
            result = await handler.handle_notify_cycle()

            assert result is False
            mock_logger.debug.assert_called()


@pytest.mark.asyncio
async def test_handle_notify_cycle_handles_disconnect():
    handler, reader, writer = create_handler()

    disconnect = Frame.construct(
        FrameType.HAPROXY_DISCONNECT,
        stream_id=0,
        frame_id=0,
        status_code=DisconnectCode.NORMAL,
        message="Normal disconnect",
    )

    with (
        patch.object(Frame, "decode", return_value=disconnect),
        patch("spoe_forge.server.handler.logger") as mock_logger,
    ):
        result = await handler.handle_notify_cycle()

        assert result is False
        writer.write.assert_called_once()
        mock_logger.debug.assert_called()


@pytest.mark.asyncio
async def test_handle_notify_cycle_rejects_wrong_frame_type():
    handler, reader, writer = create_handler()

    agent_hello = Frame.construct(
        FrameType.AGENT_HELLO,
        stream_id=0,
        frame_id=0,
        version="2.0",
        max_frame_size=16384,
        capabilities=["pipelining"],
    )

    with (
        patch.object(Frame, "decode", return_value=agent_hello),
        patch("spoe_forge.server.handler.logger"),
    ):
        result = await handler.handle_notify_cycle()

        assert result is False


@pytest.mark.asyncio
async def test_handle_notify_cycle_passes_messages_to_handler():
    captured_messages = None

    async def capture_handler(messages):
        nonlocal captured_messages
        captured_messages = messages
        return []

    handler, reader, writer = create_handler(capture_handler)

    test_messages = [("check-ip", {"src": "192.168.1.1", "dst": "10.0.0.1"})]
    notify = Frame.construct(
        FrameType.NOTIFY,
        stream_id=1,
        frame_id=1,
        messages=test_messages,
    )

    with patch.object(Frame, "decode", return_value=notify):
        await handler.handle_notify_cycle()

        assert captured_messages == test_messages


@pytest.mark.asyncio
async def test_core_handler_full_flow():
    notify_handler = AsyncMock(return_value=[])
    handler, reader, writer = create_handler(notify_handler)

    haproxy_hello = Frame.construct(
        FrameType.HAPROXY_HELLO,
        stream_id=0,
        frame_id=0,
        supported_versions=["2.0"],
        max_frame_size=16384,
        capabilities=["pipelining"],
        healthcheck=False,
    )

    notify1 = Frame.construct(
        FrameType.NOTIFY, stream_id=1, frame_id=1, messages=[("msg1", {})]
    )
    notify2 = Frame.construct(
        FrameType.NOTIFY, stream_id=1, frame_id=2, messages=[("msg2", {})]
    )
    disconnect = Frame.construct(
        FrameType.HAPROXY_DISCONNECT,
        stream_id=0,
        frame_id=0,
        status_code=DisconnectCode.NORMAL,
        message="Done",
    )

    with (
        patch.object(
            Frame, "decode", side_effect=[haproxy_hello, notify1, notify2, disconnect]
        ),
        patch("spoe_forge.server.handler.logger"),
    ):
        await handler.core_handler()

        assert notify_handler.call_count == 2
        writer.close.assert_called_once()


@pytest.mark.asyncio
async def test_core_handler_handles_spoeforge_error():
    notify_handler = AsyncMock(side_effect=SpoeForgeError("Test error"))
    handler, reader, writer = create_handler(notify_handler)

    haproxy_hello = Frame.construct(
        FrameType.HAPROXY_HELLO,
        stream_id=0,
        frame_id=0,
        supported_versions=["2.0"],
        max_frame_size=16384,
        capabilities=["pipelining"],
        healthcheck=False,
    )

    notify = Frame.construct(FrameType.NOTIFY, stream_id=1, frame_id=1, messages=[])

    with (
        patch.object(Frame, "decode", side_effect=[haproxy_hello, notify]),
        patch("spoe_forge.server.handler.logger"),
    ):
        await handler.core_handler()

        assert writer.write.call_count >= 2
        writer.close.assert_called_once()


@pytest.mark.asyncio
async def test_core_handler_handles_connection_reset():
    handler, reader, writer = create_handler()

    haproxy_hello = Frame.construct(
        FrameType.HAPROXY_HELLO,
        stream_id=0,
        frame_id=0,
        supported_versions=["2.0"],
        max_frame_size=16384,
        capabilities=["pipelining"],
        healthcheck=False,
    )

    with (
        patch.object(
            Frame, "decode", side_effect=[haproxy_hello, ConnectionResetError()]
        ),
        patch("spoe_forge.server.handler.logger") as mock_logger,
    ):
        await handler.core_handler()

        writer.close.assert_not_called()
        mock_logger.debug.assert_called()
        assert any(
            "Connection reset" in str(call) for call in mock_logger.debug.call_args_list
        )
