import asyncio
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
from spoe_forge.spop.exception import SpopFrameTooBigError
from spoe_forge.spop.encoders.data_types import encode_dt_bool
from spoe_forge.spop.encoders.data_types import encode_frame_len
from spoe_forge.spop.encoders.data_types import encode_string
from spoe_forge.spop.encoders.data_types import encode_tiny_int
from spoe_forge.spop.encoders.payloads import encode_metadata
from spoe_forge.spop.frame import Ack
from spoe_forge.spop.frame import AgentHello
from spoe_forge.spop.frame import Disconnect
from spoe_forge.spop.frame import Frame
from spoe_forge.spop.spop_types import Flags
from spoe_forge.spop.spop_types import MetaData
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
async def test_send_frame_raises_on_encode_error():
    handler, reader, writer = create_handler()

    test_frame = Frame.construct(
        FrameType.ACK,
        stream_id=1,
        frame_id=1,
        actions=[],
    )

    with patch.object(test_frame, "encode", side_effect=SpopEncodeError("boom")):
        with pytest.raises(SpopEncodeError):
            await handler.send_frame(test_frame)

    writer.write.assert_not_called()


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
async def test_send_disconnect_on_error_truncates_long_message():
    handler, reader, writer = create_handler()

    with patch("spoe_forge.server.handler.logger"):
        result = await handler.send_disconnect_on_error(
            DisconnectCode.PROTOCOL_ERROR, "x" * 5000
        )

    assert result is True
    frame = await Frame.decode(create_stream_reader(writer.write.call_args[0][0]), 4096)
    assert frame.message == "x" * 256


@pytest.mark.asyncio
async def test_adversarial_decode_error_still_sends_bounded_disconnect():
    handler, reader, writer = create_handler()

    # A maximally legal NOTIFY: huge message name plus a duplicated arg, so the
    # decode error text embeds ~4KB of peer-controlled content
    kv_pair = encode_string("k") + encode_dt_bool(True)
    payload = (
        encode_tiny_int(FrameType.NOTIFY)
        + encode_metadata(
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=1, frame_id=1)
        )
        + encode_string("M" * 4000)
        + encode_tiny_int(2)
        + kv_pair
        + kv_pair
    )
    assert len(payload) <= 4096

    handler.reader = _open_reader(
        _hello_bytes() + encode_frame_len(len(payload)) + payload
    )

    with patch("spoe_forge.server.handler.logger"):
        await asyncio.wait_for(handler.core_handler(), timeout=2)

    frames = await _written_frames(writer)
    assert isinstance(frames[-1], Disconnect)
    assert frames[-1].status_code == DisconnectCode.PROTOCOL_ERROR
    assert len(frames[-1].message) <= 256
    writer.close.assert_called_once()


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


def _hello_bytes(capabilities: list[str] | None = None) -> bytes:
    frame = Frame.construct(
        FrameType.HAPROXY_HELLO,
        stream_id=0,
        frame_id=0,
        supported_versions=["2.0"],
        max_frame_size=16384,
        capabilities=["pipelining"] if capabilities is None else capabilities,
        healthcheck=False,
    )
    return frame.encode(max_frame_size=16384)


def _notify_bytes(stream_id: int) -> bytes:
    frame = Frame.construct(
        FrameType.NOTIFY,
        stream_id=stream_id,
        frame_id=stream_id,
        messages=[("m", {"id": stream_id})],
    )
    return frame.encode(max_frame_size=16384)


def _disconnect_bytes() -> bytes:
    frame = Frame.construct(
        FrameType.HAPROXY_DISCONNECT,
        stream_id=0,
        frame_id=0,
        status_code=DisconnectCode.NORMAL,
        message="Done",
    )
    return frame.encode(max_frame_size=16384)


def _open_reader(data: bytes) -> asyncio.StreamReader:
    reader = asyncio.StreamReader()
    reader.feed_data(data)
    return reader


async def _written_frames(writer) -> list[Frame]:
    frames = []
    for call in writer.write.call_args_list:
        frames.append(await Frame.decode(create_stream_reader(call[0][0]), 16384))
    return frames


async def _wait_until(cond, timeout: float = 2.0) -> None:
    async with asyncio.timeout(timeout):
        while not cond():
            await asyncio.sleep(0.001)


@pytest.mark.asyncio
async def test_core_handler_full_flow():
    notify_handler = AsyncMock(return_value=[])
    handler, reader, writer = create_handler(notify_handler)
    handler.reader = _open_reader(_hello_bytes() + _notify_bytes(1) + _notify_bytes(2))

    task = asyncio.create_task(handler.core_handler())
    await _wait_until(lambda: writer.write.call_count >= 3)  # AGENT_HELLO + 2 ACKs
    handler.reader.feed_data(_disconnect_bytes())
    await asyncio.wait_for(task, timeout=2)

    assert notify_handler.call_count == 2
    writer.close.assert_called_once()


@pytest.mark.asyncio
async def test_pipelining_sends_acks_in_completion_order():
    first_gate = asyncio.Event()

    async def notify_handler(messages):
        if messages[0][1]["id"] == 1:
            await first_gate.wait()
        return []

    handler, reader, writer = create_handler(notify_handler)
    handler.reader = _open_reader(_hello_bytes() + _notify_bytes(1) + _notify_bytes(2))

    task = asyncio.create_task(handler.core_handler())
    await _wait_until(lambda: writer.write.call_count >= 2)  # ACK for stream 2 first
    first_gate.set()
    await _wait_until(lambda: writer.write.call_count >= 3)
    handler.reader.feed_eof()
    await asyncio.wait_for(task, timeout=2)

    frames = await _written_frames(writer)
    assert isinstance(frames[0], AgentHello)
    assert [f.metadata.stream_id for f in frames[1:]] == [2, 1]


@pytest.mark.asyncio
async def test_serial_without_pipelining_capability():
    started = []
    gate = asyncio.Event()

    async def notify_handler(messages):
        started.append(messages[0][1]["id"])
        await gate.wait()
        return []

    handler, reader, writer = create_handler(notify_handler)
    handler.reader = _open_reader(
        _hello_bytes([]) + _notify_bytes(1) + _notify_bytes(2)
    )

    with patch("spoe_forge.server.handler.logger"):
        task = asyncio.create_task(handler.core_handler())
        await _wait_until(lambda: len(started) == 1)
        await asyncio.sleep(0.01)

        assert started == [1]  # second NOTIFY must wait for the first ACK

        gate.set()
        await _wait_until(lambda: writer.write.call_count >= 3)
        handler.reader.feed_eof()
        await asyncio.wait_for(task, timeout=2)

    assert started == [1, 2]


@pytest.mark.asyncio
async def test_concurrency_bounded_by_max_concurrent_frames():
    started = []
    gate = asyncio.Event()

    async def notify_handler(messages):
        started.append(messages[0][1]["id"])
        await gate.wait()
        return []

    handler, reader, writer = create_handler(notify_handler, max_concurrent_frames=2)
    handler.reader = _open_reader(
        _hello_bytes() + _notify_bytes(1) + _notify_bytes(2) + _notify_bytes(3)
    )

    task = asyncio.create_task(handler.core_handler())
    await _wait_until(lambda: len(started) == 2)
    await asyncio.sleep(0.01)

    assert len(started) == 2  # third frame waits for a free slot

    gate.set()
    await _wait_until(lambda: writer.write.call_count >= 4)  # AGENT_HELLO + 3 ACKs
    handler.reader.feed_eof()
    await asyncio.wait_for(task, timeout=2)

    assert sorted(started) == [1, 2, 3]


@pytest.mark.asyncio
async def test_disconnect_cancels_in_flight_tasks():
    entered = asyncio.Event()
    cancelled = False

    async def notify_handler(messages):
        nonlocal cancelled
        entered.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled = True
            raise
        return []

    handler, reader, writer = create_handler(notify_handler)
    handler.reader = _open_reader(_hello_bytes() + _notify_bytes(1))

    task = asyncio.create_task(handler.core_handler())
    await asyncio.wait_for(entered.wait(), timeout=2)
    handler.reader.feed_data(_disconnect_bytes())
    await asyncio.wait_for(task, timeout=2)

    assert cancelled is True
    frames = await _written_frames(writer)
    assert isinstance(frames[-1], Disconnect)
    assert frames[-1].status_code == DisconnectCode.NORMAL
    assert not any(isinstance(f, Ack) for f in frames)


@pytest.mark.asyncio
async def test_oversized_ack_salvages_fitting_actions():
    async def notify_handler(messages):
        if messages[0][1]["id"] == 1:
            return [
                SetVarAction(scope=ActionScope.SESSION, name="big", value="x" * 5000),
                SetVarAction(scope=ActionScope.SESSION, name="kept", value=1),
            ]
        return [SetVarAction(scope=ActionScope.SESSION, name="ok", value=1)]

    handler, reader, writer = create_handler(notify_handler)
    handler.reader = _open_reader(_hello_bytes() + _notify_bytes(1))

    with patch("spoe_forge.server.handler.logger") as mock_logger:
        task = asyncio.create_task(handler.core_handler())
        await _wait_until(lambda: writer.write.call_count >= 2)

        # Connection survived - a subsequent NOTIFY is still served normally
        handler.reader.feed_data(_notify_bytes(2))
        await _wait_until(lambda: writer.write.call_count >= 3)
        handler.reader.feed_eof()
        await asyncio.wait_for(task, timeout=2)

        assert any(
            "salvageable actions" in str(call)
            for call in mock_logger.error.call_args_list
        )

    frames = await _written_frames(writer)
    acks = [f for f in frames if isinstance(f, Ack)]
    assert [(a.metadata.stream_id, a.actions) for a in acks] == [
        (1, [SetVarAction(scope=ActionScope.SESSION, name="kept", value=1)]),
        (2, [SetVarAction(scope=ActionScope.SESSION, name="ok", value=1)]),
    ]
    assert not any(isinstance(f, Disconnect) for f in frames)


@pytest.mark.asyncio
async def test_unencodable_ack_salvages_encodable_actions():
    async def notify_handler(messages):
        return [
            SetVarAction(scope=ActionScope.SESSION, name="v", value="hi \U0001f600"),
            SetVarAction(scope=ActionScope.SESSION, name="kept", value=1),
        ]

    handler, reader, writer = create_handler(notify_handler)
    handler.reader = _open_reader(_hello_bytes() + _notify_bytes(1))

    with patch("spoe_forge.server.handler.logger") as mock_logger:
        task = asyncio.create_task(handler.core_handler())
        await _wait_until(lambda: writer.write.call_count >= 2)
        handler.reader.feed_eof()
        await asyncio.wait_for(task, timeout=2)

        assert any(
            "Dropping unencodable action" in str(call)
            for call in mock_logger.error.call_args_list
        )

    frames = await _written_frames(writer)
    acks = [f for f in frames if isinstance(f, Ack)]
    assert [(a.metadata.stream_id, a.actions) for a in acks] == [
        (1, [SetVarAction(scope=ActionScope.SESSION, name="kept", value=1)])
    ]


@pytest.mark.asyncio
async def test_ack_with_no_salvageable_actions_is_empty():
    async def notify_handler(messages):
        return [
            SetVarAction(scope=ActionScope.SESSION, name="v", value="hi \U0001f600")
        ]

    handler, reader, writer = create_handler(notify_handler)
    handler.reader = _open_reader(_hello_bytes() + _notify_bytes(1))

    with patch("spoe_forge.server.handler.logger"):
        task = asyncio.create_task(handler.core_handler())
        await _wait_until(lambda: writer.write.call_count >= 2)
        handler.reader.feed_eof()
        await asyncio.wait_for(task, timeout=2)

    frames = await _written_frames(writer)
    acks = [f for f in frames if isinstance(f, Ack)]
    assert [(a.metadata.stream_id, a.actions) for a in acks] == [(1, [])]


@pytest.mark.asyncio
async def test_core_handler_handles_spoeforge_error():
    notify_handler = AsyncMock(side_effect=SpoeForgeError("Test error"))
    handler, reader, writer = create_handler(notify_handler)
    handler.reader = _open_reader(_hello_bytes() + _notify_bytes(1))

    with patch("spoe_forge.server.handler.logger"):
        await asyncio.wait_for(handler.core_handler(), timeout=2)

    frames = await _written_frames(writer)
    assert isinstance(frames[-1], Disconnect)
    assert frames[-1].status_code == DisconnectCode.PROTOCOL_ERROR
    writer.close.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("teardown_error", [ConnectionResetError, BrokenPipeError])
async def test_core_handler_handles_peer_teardown(teardown_error):
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
        patch.object(Frame, "decode", side_effect=[haproxy_hello, teardown_error()]),
        patch("spoe_forge.server.handler.logger") as mock_logger,
    ):
        await handler.core_handler()

        writer.close.assert_called_once()
        assert any(
            "Connection closed by HAProxy" in str(call)
            for call in mock_logger.debug.call_args_list
        )
