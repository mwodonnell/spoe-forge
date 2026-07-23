import pytest
from ipaddress import IPv4Address

from spoe_forge.spop.constants import ActionScope
from spoe_forge.spop.constants import FrameType
from spoe_forge.spop.frame import Ack
from spoe_forge.spop.frame import AgentHello
from spoe_forge.spop.frame import Disconnect
from spoe_forge.spop.frame import Frame
from spoe_forge.spop.frame import HaproxyHello
from spoe_forge.spop.frame import Notify
from spoe_forge.spop.spop_types import SetVarAction
from spoe_forge.spop.spop_types import UnsetVarAction
from tests.utils import create_stream_reader


@pytest.mark.asyncio
async def test_roundtrip_haproxy_hello(haproxy_hello_data):
    frame_type, metadata, payload_kwargs, desc = haproxy_hello_data

    frame = await Frame.construct(
        frame_type=frame_type,
        stream_id=metadata.stream_id,
        frame_id=metadata.frame_id,
        **payload_kwargs,
    )

    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert isinstance(decoded, HaproxyHello)
    assert decoded.frame_type == frame_type
    assert decoded.metadata.stream_id == metadata.stream_id
    assert decoded.metadata.frame_id == metadata.frame_id
    assert decoded.metadata.flags.FIN == metadata.flags.FIN
    assert decoded.metadata.flags.ABORT == metadata.flags.ABORT
    assert decoded.supported_versions == payload_kwargs["supported_versions"]
    assert decoded.max_frame_size == payload_kwargs["max_frame_size"]
    assert decoded.capabilities == payload_kwargs["capabilities"]
    assert decoded.healthcheck == payload_kwargs.get("healthcheck", False)
    if "engine_id" in payload_kwargs:
        assert decoded.engine_id == payload_kwargs["engine_id"]


@pytest.mark.asyncio
async def test_roundtrip_agent_hello(agent_hello_data):
    frame_type, metadata, payload_kwargs, desc = agent_hello_data

    frame = await Frame.construct(
        frame_type=frame_type,
        stream_id=metadata.stream_id,
        frame_id=metadata.frame_id,
        **payload_kwargs,
    )

    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert isinstance(decoded, AgentHello)
    assert decoded.frame_type == frame_type
    assert decoded.metadata.stream_id == metadata.stream_id
    assert decoded.metadata.frame_id == metadata.frame_id
    assert decoded.metadata.flags.FIN == metadata.flags.FIN
    assert decoded.metadata.flags.ABORT == metadata.flags.ABORT
    assert decoded.version == payload_kwargs["version"]
    assert decoded.max_frame_size == payload_kwargs["max_frame_size"]
    assert decoded.capabilities == payload_kwargs["capabilities"]


@pytest.mark.asyncio
async def test_roundtrip_disconnect(disconnect_data):
    frame_type, metadata, payload_kwargs, desc = disconnect_data

    frame = await Frame.construct(
        frame_type=frame_type,
        stream_id=metadata.stream_id,
        frame_id=metadata.frame_id,
        **payload_kwargs,
    )

    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert isinstance(decoded, Disconnect)
    assert decoded.frame_type == frame_type
    assert decoded.metadata.stream_id == metadata.stream_id
    assert decoded.metadata.frame_id == metadata.frame_id
    assert decoded.metadata.flags.FIN == metadata.flags.FIN
    assert decoded.metadata.flags.ABORT == metadata.flags.ABORT
    assert decoded.status_code == payload_kwargs["status_code"]
    assert decoded.message == payload_kwargs["message"]


@pytest.mark.asyncio
async def test_roundtrip_notify(notify_data):
    frame_type, metadata, payload_kwargs, desc = notify_data

    frame = await Frame.construct(
        frame_type=frame_type,
        stream_id=metadata.stream_id,
        frame_id=metadata.frame_id,
        **payload_kwargs,
    )

    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert isinstance(decoded, Notify)
    assert decoded.frame_type == frame_type
    assert decoded.metadata.stream_id == metadata.stream_id
    assert decoded.metadata.frame_id == metadata.frame_id
    assert decoded.metadata.flags.FIN == metadata.flags.FIN
    assert decoded.metadata.flags.ABORT == metadata.flags.ABORT
    assert decoded.messages == payload_kwargs["messages"]


@pytest.mark.asyncio
async def test_roundtrip_ack(ack_data):
    frame_type, metadata, payload_kwargs, desc = ack_data

    frame = await Frame.construct(
        frame_type=frame_type,
        stream_id=metadata.stream_id,
        frame_id=metadata.frame_id,
        **payload_kwargs,
    )

    encoded = frame.encode(max_frame_size=16384)

    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert isinstance(decoded, Ack)
    assert decoded.frame_type == frame_type
    assert decoded.metadata.stream_id == metadata.stream_id
    assert decoded.metadata.frame_id == metadata.frame_id
    assert decoded.metadata.flags.FIN == metadata.flags.FIN
    assert decoded.metadata.flags.ABORT == metadata.flags.ABORT
    assert len(decoded.actions) == len(payload_kwargs["actions"])

    for i, action in enumerate(decoded.actions):
        original = payload_kwargs["actions"][i]
        assert type(action) is type(original)
        assert action.scope == original.scope
        assert action.name == original.name
        if isinstance(action, SetVarAction):
            assert action.value == original.value


@pytest.mark.asyncio
async def test_roundtrip_any_frame(any_frame_data):
    frame_type, metadata, payload_kwargs, desc = any_frame_data

    frame = await Frame.construct(
        frame_type=frame_type,
        stream_id=metadata.stream_id,
        frame_id=metadata.frame_id,
        **payload_kwargs,
    )

    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert decoded.frame_type == frame_type
    assert decoded.metadata.stream_id == metadata.stream_id
    assert decoded.metadata.frame_id == metadata.frame_id
    assert decoded.metadata.flags.FIN == metadata.flags.FIN
    assert decoded.metadata.flags.ABORT == metadata.flags.ABORT


@pytest.mark.asyncio
async def test_roundtrip_haproxy_hello_multiple_versions():
    frame = await Frame.construct(
        frame_type=FrameType.HAPROXY_HELLO,
        stream_id=0,
        frame_id=0,
        supported_versions=["2.0", "1.0", "1.5"],
        max_frame_size=32768,
        capabilities=["pipelining", "async", "fragmentation"],
    )

    encoded = frame.encode(max_frame_size=32768)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert isinstance(decoded, HaproxyHello)
    assert decoded.supported_versions == ["2.0", "1.0", "1.5"]
    assert decoded.capabilities == ["pipelining", "async", "fragmentation"]


@pytest.mark.asyncio
async def test_roundtrip_notify_with_complex_types():
    frame = await Frame.construct(
        frame_type=FrameType.NOTIFY,
        stream_id=5,
        frame_id=10,
        messages={
            "check": {
                "ip": IPv4Address("192.168.1.1"),
                "port": 8080,
                "ssl": True,
                "data": b"\x00\x01\x02",
            }
        },
    )

    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert isinstance(decoded, Notify)
    assert decoded.messages["check"]["ip"] == IPv4Address("192.168.1.1")
    assert decoded.messages["check"]["port"] == 8080
    assert decoded.messages["check"]["ssl"] is True
    assert decoded.messages["check"]["data"] == b"\x00\x01\x02"


@pytest.mark.asyncio
async def test_roundtrip_ack_mixed_actions():
    frame = await Frame.construct(
        frame_type=FrameType.ACK,
        stream_id=3,
        frame_id=7,
        actions=[
            SetVarAction(scope=ActionScope.SESSION, name="user_id", value=12345),
            SetVarAction(scope=ActionScope.REQUEST, name="blocked", value=True),
            UnsetVarAction(scope=ActionScope.SESSION, name="temp_token"),
            SetVarAction(scope=ActionScope.RESPONSE, name="cache_ttl", value=3600),
            UnsetVarAction(scope=ActionScope.REQUEST, name="old_flag"),
        ],
    )

    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert isinstance(decoded, Ack)
    assert len(decoded.actions) == 5
    assert isinstance(decoded.actions[0], SetVarAction)
    assert decoded.actions[0].name == "user_id"
    assert decoded.actions[0].value == 12345
    assert isinstance(decoded.actions[1], SetVarAction)
    assert decoded.actions[1].name == "blocked"
    assert decoded.actions[1].value is True
    assert isinstance(decoded.actions[2], UnsetVarAction)
    assert decoded.actions[2].name == "temp_token"
    assert isinstance(decoded.actions[3], SetVarAction)
    assert decoded.actions[3].name == "cache_ttl"
    assert isinstance(decoded.actions[4], UnsetVarAction)
    assert decoded.actions[4].name == "old_flag"


@pytest.mark.asyncio
async def test_roundtrip_notify_empty_messages():
    frame = await Frame.construct(
        frame_type=FrameType.NOTIFY,
        stream_id=0,
        frame_id=0,
        messages={},
    )

    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert isinstance(decoded, Notify)
    assert decoded.messages == {}


@pytest.mark.asyncio
async def test_roundtrip_ack_empty_actions():
    frame = await Frame.construct(
        frame_type=FrameType.ACK,
        stream_id=0,
        frame_id=0,
        actions=[],
    )

    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert isinstance(decoded, Ack)
    assert decoded.actions == []


@pytest.mark.asyncio
async def test_roundtrip_notify_message_with_no_args():
    frame = await Frame.construct(
        frame_type=FrameType.NOTIFY,
        stream_id=1,
        frame_id=1,
        messages={"ping": {}},
    )

    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert isinstance(decoded, Notify)
    assert "ping" in decoded.messages
    assert decoded.messages["ping"] == {}


@pytest.mark.asyncio
async def test_roundtrip_haproxy_hello_no_capabilities():
    frame = await Frame.construct(
        frame_type=FrameType.HAPROXY_HELLO,
        stream_id=0,
        frame_id=0,
        supported_versions=["2.0"],
        max_frame_size=8192,
        capabilities=[],
    )

    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert isinstance(decoded, HaproxyHello)
    assert decoded.capabilities == []


@pytest.mark.asyncio
async def test_roundtrip_agent_hello_no_capabilities():
    frame = await Frame.construct(
        frame_type=FrameType.AGENT_HELLO,
        stream_id=1,
        frame_id=1,
        version="2.0",
        max_frame_size=8192,
        capabilities=[],
    )

    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert isinstance(decoded, AgentHello)
    assert decoded.capabilities == []


@pytest.mark.asyncio
async def test_roundtrip_disconnect_empty_message():
    frame = await Frame.construct(
        frame_type=FrameType.HAPROXY_DISCONNECT,
        stream_id=0,
        frame_id=0,
        status_code=0,
        message="",
    )

    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert isinstance(decoded, Disconnect)
    assert decoded.message == ""


@pytest.mark.asyncio
async def test_roundtrip_metadata_flags():
    frame = await Frame.construct(
        frame_type=FrameType.ACK,
        stream_id=1,
        frame_id=1,
        actions=[],
    )
    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    # Flags are always hardcoded - see spoe_forge.spop.frame.Frame.construct for reference
    assert decoded.metadata.flags.FIN is True
    assert decoded.metadata.flags.ABORT is False


@pytest.mark.asyncio
async def test_roundtrip_large_stream_and_frame_ids():
    frame = await Frame.construct(
        frame_type=FrameType.ACK,
        stream_id=999999,
        frame_id=888888,
        actions=[],
    )

    encoded = frame.encode(max_frame_size=16384)
    reader = create_stream_reader(encoded)
    decoded = await Frame.decode(reader)

    assert decoded.metadata.stream_id == 999999
    assert decoded.metadata.frame_id == 888888
