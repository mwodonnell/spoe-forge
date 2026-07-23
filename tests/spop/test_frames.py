import struct

import pytest

from spoe_forge.spop.constants import ActionScope
from spoe_forge.spop.constants import FrameType
from spoe_forge.spop.exception import SpopDecodeError
from spoe_forge.spop.exception import SpopFrameTooBigError
from spoe_forge.spop.frame import Ack
from spoe_forge.spop.frame import AgentHello
from spoe_forge.spop.frame import Disconnect
from spoe_forge.spop.frame import Frame
from spoe_forge.spop.frame import HaproxyHello
from spoe_forge.spop.frame import Notify
from spoe_forge.spop.spop_types import SetVarAction
from tests.utils import create_stream_reader


def test_frame_registry_contains_all_types():
    assert FrameType.HAPROXY_HELLO in Frame._registry
    assert FrameType.AGENT_HELLO in Frame._registry
    assert FrameType.HAPROXY_DISCONNECT in Frame._registry
    assert FrameType.AGENT_DISCONNECT in Frame._registry
    assert FrameType.NOTIFY in Frame._registry
    assert FrameType.ACK in Frame._registry


def test_frame_registry_maps_to_correct_classes():
    assert Frame._registry[FrameType.HAPROXY_HELLO] == HaproxyHello
    assert Frame._registry[FrameType.AGENT_HELLO] == AgentHello
    assert Frame._registry[FrameType.HAPROXY_DISCONNECT] == Disconnect
    assert Frame._registry[FrameType.AGENT_DISCONNECT] == Disconnect
    assert Frame._registry[FrameType.NOTIFY] == Notify
    assert Frame._registry[FrameType.ACK] == Ack


@pytest.mark.asyncio
async def test_construct_haproxy_hello():
    frame = Frame.construct(
        frame_type=FrameType.HAPROXY_HELLO,
        stream_id=1,
        frame_id=1,
        supported_versions=["2.0", "1.0"],
        max_frame_size=16384,
        capabilities=["pipelining", "async"],
    )

    assert isinstance(frame, HaproxyHello)
    assert frame.frame_type == FrameType.HAPROXY_HELLO
    assert frame.metadata.stream_id == 1
    assert frame.metadata.frame_id == 1
    assert frame.supported_versions == ["2.0", "1.0"]
    assert frame.max_frame_size == 16384
    assert frame.capabilities == ["pipelining", "async"]
    assert frame.healthcheck is False


@pytest.mark.asyncio
async def test_construct_haproxy_hello_with_optional_fields():
    frame = Frame.construct(
        frame_type=FrameType.HAPROXY_HELLO,
        stream_id=0,
        frame_id=0,
        supported_versions=["2.0"],
        max_frame_size=8192,
        capabilities=["pipelining"],
        engine_id="engine-1",
        healthcheck=True,
    )

    assert isinstance(frame, HaproxyHello)
    assert frame.engine_id == "engine-1"
    assert frame.healthcheck is True


@pytest.mark.asyncio
async def test_construct_agent_hello():
    frame = Frame.construct(
        frame_type=FrameType.AGENT_HELLO,
        stream_id=1,
        frame_id=1,
        version="2.0",
        max_frame_size=16384,
        capabilities=["pipelining"],
    )

    assert isinstance(frame, AgentHello)
    assert frame.frame_type == FrameType.AGENT_HELLO
    assert frame.version == "2.0"
    assert frame.max_frame_size == 16384
    assert frame.capabilities == ["pipelining"]


@pytest.mark.asyncio
async def test_construct_disconnect_haproxy():
    frame = Frame.construct(
        frame_type=FrameType.HAPROXY_DISCONNECT,
        stream_id=1,
        frame_id=1,
        status_code=0,
        message="Normal disconnect",
    )

    assert isinstance(frame, Disconnect)
    assert frame.frame_type == FrameType.HAPROXY_DISCONNECT
    assert frame.status_code == 0
    assert frame.message == "Normal disconnect"


@pytest.mark.asyncio
async def test_construct_disconnect_agent():
    frame = Frame.construct(
        frame_type=FrameType.AGENT_DISCONNECT,
        stream_id=0,
        frame_id=0,
        status_code=1,
        message="Error occurred",
    )

    assert isinstance(frame, Disconnect)
    assert frame.frame_type == FrameType.AGENT_DISCONNECT
    assert frame.status_code == 1
    assert frame.message == "Error occurred"


@pytest.mark.asyncio
async def test_construct_notify():
    frame = Frame.construct(
        frame_type=FrameType.NOTIFY,
        stream_id=1,
        frame_id=1,
        messages={"check-ip": {"src": "192.168.1.1", "dst": "10.0.0.1"}},
    )

    assert isinstance(frame, Notify)
    assert frame.frame_type == FrameType.NOTIFY
    assert "check-ip" in frame.messages
    assert frame.messages["check-ip"]["src"] == "192.168.1.1"


@pytest.mark.asyncio
async def test_construct_notify_empty():
    frame = Frame.construct(
        frame_type=FrameType.NOTIFY,
        stream_id=0,
        frame_id=0,
        messages={},
    )

    assert isinstance(frame, Notify)
    assert frame.messages == {}


@pytest.mark.asyncio
async def test_construct_ack():
    frame = Frame.construct(
        frame_type=FrameType.ACK,
        stream_id=1,
        frame_id=1,
        actions=[SetVarAction(scope=ActionScope.SESSION, name="score", value=95)],
    )

    assert isinstance(frame, Ack)
    assert frame.frame_type == FrameType.ACK
    assert len(frame.actions) == 1
    assert frame.actions[0].name == "score"
    assert frame.actions[0].value == 95


@pytest.mark.asyncio
async def test_construct_ack_empty():
    frame = Frame.construct(
        frame_type=FrameType.ACK,
        stream_id=0,
        frame_id=0,
        actions=[],
    )

    assert isinstance(frame, Ack)
    assert frame.actions == []


@pytest.mark.asyncio
async def test_encode_raises_on_size_limit():
    large_messages = {f"msg{i}": {"arg": i} for i in range(1000)}

    frame = Frame.construct(
        frame_type=FrameType.NOTIFY,
        stream_id=1,
        frame_id=1,
        messages=large_messages,
    )

    with pytest.raises(SpopFrameTooBigError, match="frame size .* exceeds max"):
        frame.encode(max_frame_size=100)  # Very small max size


@pytest.mark.asyncio
async def test_decode_raises_on_oversized_frame():
    reader = create_stream_reader(struct.pack("!I", 100_000))

    with pytest.raises(SpopFrameTooBigError, match="exceeds maximum size"):
        await Frame.decode(reader, 4096)


@pytest.mark.asyncio
async def test_decode_accepts_frame_exactly_at_size_limit():
    frame = Frame.construct(
        frame_type=FrameType.ACK,
        stream_id=1,
        frame_id=1,
        actions=[],
    )

    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader, len(encoded))

    assert isinstance(decoded, Ack)


@pytest.mark.asyncio
async def test_encode_includes_correct_frame_length():
    frame = Frame.construct(
        frame_type=FrameType.ACK,
        stream_id=0,
        frame_id=0,
        actions=[],
    )

    result = frame.encode(max_frame_size=16384)
    frame_len = int.from_bytes(result[0:4], "big")
    assert frame_len == len(result) - 4


@pytest.mark.asyncio
async def test_encode_includes_frame_type():
    frame = Frame.construct(
        frame_type=FrameType.ACK,
        stream_id=1,
        frame_id=1,
        actions=[],
    )

    result = frame.encode(max_frame_size=16384)
    assert result[4] == FrameType.ACK


def test_to_spop_list_with_values():
    result = HaproxyHello.to_spop_list(["a", "b", "c"])
    assert result == "a,b,c"


def test_to_spop_list_empty():
    result = HaproxyHello.to_spop_list([])
    assert result == ""


def test_to_spop_list_single_value():
    result = HaproxyHello.to_spop_list(["single"])
    assert result == "single"


def test_from_spop_list_with_values():
    result = HaproxyHello.from_spop_list("a,b,c")
    assert result == ["a", "b", "c"]


def test_from_spop_list_empty():
    result = HaproxyHello.from_spop_list("")
    assert result == []


def test_from_spop_list_single_value():
    result = HaproxyHello.from_spop_list("single")
    assert result == ["single"]


@pytest.mark.asyncio
async def test_construct_raises_on_unknown_frame_type():
    invalid_frame_type = 99  # Not a valid FrameType value

    with pytest.raises(SpopDecodeError, match="Unknown frame type"):
        Frame.construct(
            frame_type=invalid_frame_type,
            stream_id=0,
            frame_id=0,
        )
