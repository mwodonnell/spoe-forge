"""Fixtures for frame encoding/decoding tests."""

import pytest

from spoe_forge.spop.constants import FrameType
from spoe_forge.spop.spop_types import Flags
from spoe_forge.spop.spop_types import MetaData
from spoe_forge.spop.spop_types import SetVarAction
from spoe_forge.spop.spop_types import UnsetVarAction
from spoe_forge.spop.constants import ActionScope


# ============================================================================
# Data-only fixtures (for round-trip tests)
# ============================================================================


@pytest.fixture(
    params=[
        # (frame_type, metadata, payload_kwargs, description)
        (
            FrameType.HAPROXY_HELLO,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=1, frame_id=1),
            {
                "supported_versions": ["2.0", "1.0"],
                "max_frame_size": 16384,
                "capabilities": ["pipelining", "async"],
                "healthcheck": False,
            },
            "HaproxyHello: basic",
        ),
        (
            FrameType.HAPROXY_HELLO,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=0, frame_id=0),
            {
                "supported_versions": ["2.0"],
                "max_frame_size": 8192,
                "capabilities": ["pipelining"],
                "engine_id": "engine-1",
                "healthcheck": True,
            },
            "HaproxyHello: with engine_id and healthcheck",
        ),
    ],
    ids=lambda case: case[3],
)
def haproxy_hello_data(request):
    """Provides (frame_type, metadata, payload_kwargs, desc) for HaproxyHello."""
    return request.param


@pytest.fixture(
    params=[
        # (frame_type, metadata, payload_kwargs, description)
        (
            FrameType.AGENT_HELLO,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=1, frame_id=1),
            {
                "version": "2.0",
                "max_frame_size": 16384,
                "capabilities": ["pipelining", "async"],
            },
            "AgentHello: basic",
        ),
        (
            FrameType.AGENT_HELLO,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=0, frame_id=0),
            {
                "version": "2.0",
                "max_frame_size": 4096,
                "capabilities": [],
            },
            "AgentHello: no capabilities",
        ),
    ],
    ids=lambda case: case[3],
)
def agent_hello_data(request):
    """Provides (frame_type, metadata, payload_kwargs, desc) for AgentHello."""
    return request.param


@pytest.fixture(
    params=[
        # (frame_type, metadata, payload_kwargs, description)
        (
            FrameType.HAPROXY_DISCONNECT,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=1, frame_id=1),
            {"status_code": 0, "message": "Normal disconnect"},
            "Disconnect: normal from HAProxy",
        ),
        (
            FrameType.AGENT_DISCONNECT,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=0, frame_id=0),
            {"status_code": 1, "message": "Error occurred"},
            "Disconnect: error from Agent",
        ),
    ],
    ids=lambda case: case[3],
)
def disconnect_data(request):
    """Provides (frame_type, metadata, payload_kwargs, desc) for Disconnect."""
    return request.param


@pytest.fixture(
    params=[
        # (frame_type, metadata, payload_kwargs, description)
        (
            FrameType.NOTIFY,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=1, frame_id=1),
            {
                "messages": {
                    "check-ip": {"src": "192.168.1.1", "dst": "10.0.0.1"},
                }
            },
            "Notify: single message",
        ),
        (
            FrameType.NOTIFY,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=2, frame_id=3),
            {
                "messages": {
                    "check-ip": {"src": "192.168.1.1"},
                    "check-user": {"username": "admin", "active": True},
                }
            },
            "Notify: multiple messages",
        ),
        (
            FrameType.NOTIFY,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=0, frame_id=0),
            {"messages": {}},
            "Notify: empty messages",
        ),
    ],
    ids=lambda case: case[3],
)
def notify_data(request):
    """Provides (frame_type, metadata, payload_kwargs, desc) for Notify."""
    return request.param


@pytest.fixture(
    params=[
        # (frame_type, metadata, payload_kwargs, description)
        (
            FrameType.ACK,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=1, frame_id=1),
            {
                "actions": [
                    SetVarAction(scope=ActionScope.SESSION, name="score", value=95),
                ]
            },
            "Ack: single action",
        ),
        (
            FrameType.ACK,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=2, frame_id=3),
            {
                "actions": [
                    SetVarAction(
                        scope=ActionScope.SESSION, name="blocked", value=False
                    ),
                    UnsetVarAction(scope=ActionScope.REQUEST, name="temp"),
                ]
            },
            "Ack: multiple actions",
        ),
        (
            FrameType.ACK,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=0, frame_id=0),
            {"actions": []},
            "Ack: empty actions",
        ),
    ],
    ids=lambda case: case[3],
)
def ack_data(request):
    """Provides (frame_type, metadata, payload_kwargs, desc) for Ack."""
    return request.param


# ============================================================================
# Combined fixture for all frame types (for generic tests)
# ============================================================================


@pytest.fixture(
    params=[
        # Use the first case from each frame type for generic testing
        (
            FrameType.HAPROXY_HELLO,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=1, frame_id=1),
            {
                "supported_versions": ["2.0"],
                "max_frame_size": 16384,
                "capabilities": ["pipelining"],
            },
            "HaproxyHello",
        ),
        (
            FrameType.AGENT_HELLO,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=1, frame_id=1),
            {
                "version": "2.0",
                "max_frame_size": 16384,
                "capabilities": ["pipelining"],
            },
            "AgentHello",
        ),
        (
            FrameType.HAPROXY_DISCONNECT,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=1, frame_id=1),
            {"status_code": 0, "message": "Normal"},
            "Disconnect",
        ),
        (
            FrameType.NOTIFY,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=1, frame_id=1),
            {"messages": {"test": {"arg": 1}}},
            "Notify",
        ),
        (
            FrameType.ACK,
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=1, frame_id=1),
            {"actions": [SetVarAction(scope=ActionScope.SESSION, name="x", value=1)]},
            "Ack",
        ),
    ],
    ids=lambda case: case[3],
)
def any_frame_data(request):
    """Provides (frame_type, metadata, payload_kwargs, desc) for any frame type."""
    return request.param
