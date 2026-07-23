"""Fixtures for payload encoding/decoding tests."""

import ipaddress

import pytest

from spoe_forge.spop.constants import ActionScope
from spoe_forge.spop.spop_types import Flags
from spoe_forge.spop.spop_types import MetaData
from spoe_forge.spop.spop_types import SetVarAction
from spoe_forge.spop.spop_types import UnsetVarAction


# ============================================================================
# Data-only fixtures (for round-trip tests)
# ============================================================================


@pytest.fixture(
    params=[
        # (key, value, description)
        ("ip", "192.168.1.1", "KV pair: string"),
        ("count", 42, "KV pair: int"),
        ("active", True, "KV pair: bool true"),
        ("disabled", False, "KV pair: bool false"),
        ("addr", ipaddress.IPv4Address("10.0.0.1"), "KV pair: IPv4"),
    ],
    ids=lambda case: case[2],
)
def kv_pair_data(request):
    """Provides (key, value, desc) for KV pair test cases."""
    return request.param


@pytest.fixture(
    params=[
        # (key, value, encoded_bytes, description)
        ("ip", "192.168.1.1", b"\x02ip\x08\x0b192.168.1.1", "KV pair: string"),
        ("count", 42, b"\x05count\x04*", "KV pair: int"),
        ("active", True, b"\x06active\x11", "KV pair: bool true"),
        ("disabled", False, b"\x08disabled\x01", "KV pair: bool false"),
        (
            "addr",
            ipaddress.IPv4Address("10.0.0.1"),
            b"\x04addr\x06\n\x00\x00\x01",
            "KV pair: IPv4",
        ),
    ],
    ids=lambda case: case[3],
)
def kv_pair_case(request):
    """Provides (key, value, encoded, desc) for encoder/decoder tests."""
    return request.param


@pytest.fixture(
    params=[
        # (metadata_object, description)
        (
            MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=1, frame_id=1),
            "Metadata: FIN=True, stream=1, frame=1",
        ),
        (
            MetaData(flags=Flags(FIN=False, ABORT=True), stream_id=0, frame_id=0),
            "Metadata: ABORT=True, stream=0, frame=0",
        ),
        (
            MetaData(flags=Flags(FIN=True, ABORT=True), stream_id=42, frame_id=100),
            "Metadata: FIN=True, ABORT=True, stream=42, frame=100",
        ),
        (
            MetaData(flags=Flags(FIN=False, ABORT=False), stream_id=239, frame_id=240),
            "Metadata: no flags, stream=239, frame=240",
        ),
    ],
    ids=lambda case: case[1],
)
def metadata_data(request):
    """Provides (metadata, desc) for metadata test cases."""
    return request.param


@pytest.fixture(
    params=[
        # (metadata_object, encoded_bytes, description)
        (
            MetaData(
                flags=Flags(FIN=True, ABORT=False),
                stream_id=1,
                frame_id=1,
            ),
            b"\x00\x00\x00\x01\x01\x01",
            "Metadata: FIN=True, stream=1, frame=1",
        ),
        (
            MetaData(
                flags=Flags(FIN=False, ABORT=True),
                stream_id=0,
                frame_id=0,
            ),
            b"\x00\x00\x00\x02\x00\x00",
            "Metadata: ABORT=True, stream=0, frame=0",
        ),
        (
            MetaData(
                flags=Flags(FIN=True, ABORT=True),
                stream_id=42,
                frame_id=100,
            ),
            b"\x00\x00\x00\x03*d",
            "Metadata: FIN=True, ABORT=True, stream=42, frame=100",
        ),
        (
            MetaData(
                flags=Flags(FIN=False, ABORT=False),
                stream_id=239,
                frame_id=240,
            ),
            b"\x00\x00\x00\x00\xef\xf0\x00",
            "Metadata: no flags, stream=239, frame=240",
        ),
    ],
    ids=lambda case: case[2],
)
def metadata_case(request):
    """Provides (metadata, encoded, desc) for encoder/decoder tests."""
    return request.param


@pytest.fixture(
    params=[
        # (kv_dict, description)
        ({"name": "test", "value": 123}, "KV list: 2 pairs"),
        ({}, "KV list: empty"),
        ({"single": True}, "KV list: single pair"),
        ({"a": 1, "b": 2, "c": 3}, "KV list: 3 pairs"),
    ],
    ids=lambda case: case[1],
)
def kv_list_data(request):
    """Provides (kv_dict, desc) for KV list test cases."""
    return request.param


@pytest.fixture(
    params=[
        # (kv_dict, encoded_bytes, description)
        (
            {"name": "test", "value": 123},
            b"\x04name\x08\x04test\x05value\x04{",
            "KV list: 2 pairs",
        ),
        (
            {},
            b"",
            "KV list: empty",
        ),
        (
            {"single": True},
            b"\x06single\x11",
            "KV list: single pair",
        ),
        (
            {"a": 1, "b": 2, "c": 3},
            b"\x01a\x04\x01\x01b\x04\x02\x01c\x04\x03",
            "KV list: 3 pairs",
        ),
    ],
    ids=lambda case: case[2],
)
def kv_list_case(request):
    """Provides (kv_dict, encoded, desc) for encoder/decoder tests."""
    return request.param


@pytest.fixture(
    params=[
        # (messages, description)
        (
            [("check-ip", {"src": "192.168.1.1"})],
            "Message list: single message with 1 arg",
        ),
        ([], "Message list: empty"),
        (
            [("msg1", {"a": 1, "b": 2}), ("msg2", {"x": True})],
            "Message list: 2 messages",
        ),
        ([("test", {})], "Message list: message with no args"),
        (
            [("dup", {"a": 1}), ("dup", {"a": 2})],
            "Message list: duplicate message names",
        ),
    ],
    ids=lambda case: case[1],
)
def message_list_data(request):
    """Provides (messages, desc) for message list test cases."""
    return request.param


@pytest.fixture(
    params=[
        # (messages, encoded_bytes, description)
        (
            [("check-ip", {"src": "192.168.1.1"})],
            b"\x08check-ip\x01\x03src\x08\x0b192.168.1.1",
            "Message list: single message with 1 arg",
        ),
        (
            [],
            b"",
            "Message list: empty",
        ),
        (
            [("msg1", {"a": 1, "b": 2}), ("msg2", {"x": True})],
            b"\x04msg1\x02\x01a\x04\x01\x01b\x04\x02\x04msg2\x01\x01x\x11",
            "Message list: 2 messages",
        ),
        (
            [("test", {})],
            b"\x04test\x00",
            "Message list: message with no args",
        ),
        (
            [("dup", {"a": 1}), ("dup", {"a": 2})],
            b"\x03dup\x01\x01a\x04\x01\x03dup\x01\x01a\x04\x02",
            "Message list: duplicate message names",
        ),
    ],
    ids=lambda case: case[2],
)
def message_list_case(request):
    """Provides (messages, encoded, desc) for encoder/decoder tests."""
    return request.param


@pytest.fixture(
    params=[
        # (action_object, description)
        (
            SetVarAction(scope=ActionScope.SESSION, name="score", value=95),
            "SetVarAction: session scope, int value",
        ),
        (
            SetVarAction(scope=ActionScope.REQUEST, name="blocked", value=True),
            "SetVarAction: request scope, bool value",
        ),
        (
            UnsetVarAction(scope=ActionScope.SESSION, name="temp"),
            "UnsetVarAction: session scope",
        ),
        (
            UnsetVarAction(scope=ActionScope.PROCESS, name="cache"),
            "UnsetVarAction: process scope",
        ),
    ],
    ids=lambda case: case[1],
)
def action_data(request):
    """Provides (action, desc) for action test cases."""
    return request.param


@pytest.fixture(
    params=[
        # (action_object, encoded_bytes, description)
        (
            SetVarAction(
                scope=ActionScope.SESSION,
                name="score",
                value=95,
            ),
            b"\x01\x03\x01\x05score\x04_",
            "SetVarAction: session scope, int value",
        ),
        (
            SetVarAction(
                scope=ActionScope.REQUEST,
                name="blocked",
                value=True,
            ),
            b"\x01\x03\x03\x07blocked\x11",
            "SetVarAction: request scope, bool value",
        ),
        (
            UnsetVarAction(
                scope=ActionScope.SESSION,
                name="temp",
            ),
            b"\x02\x02\x01\x04temp",
            "UnsetVarAction: session scope",
        ),
        (
            UnsetVarAction(
                scope=ActionScope.PROCESS,
                name="cache",
            ),
            b"\x02\x02\x00\x05cache",
            "UnsetVarAction: process scope",
        ),
    ],
    ids=lambda case: case[2],
)
def action_case(request):
    """Provides (action, encoded, desc) for encoder/decoder tests."""
    return request.param


@pytest.fixture(
    params=[
        # (action_list, description)
        (
            [SetVarAction(scope=ActionScope.SESSION, name="x", value=1)],
            "Action list: single SetVar",
        ),
        ([], "Action list: empty"),
        (
            [
                SetVarAction(scope=ActionScope.SESSION, name="a", value=1),
                UnsetVarAction(scope=ActionScope.REQUEST, name="b"),
            ],
            "Action list: SetVar + UnsetVar",
        ),
    ],
    ids=lambda case: case[1],
)
def action_list_data(request):
    """Provides (actions, desc) for action list test cases."""
    return request.param


@pytest.fixture(
    params=[
        # (action_list, encoded_bytes, description)
        (
            [
                SetVarAction(
                    scope=ActionScope.SESSION,
                    name="x",
                    value=1,
                ),
            ],
            b"\x01\x03\x01\x01x\x04\x01",
            "Action list: single SetVar",
        ),
        (
            [],
            b"",
            "Action list: empty",
        ),
        (
            [
                SetVarAction(
                    scope=ActionScope.SESSION,
                    name="a",
                    value=1,
                ),
                UnsetVarAction(
                    scope=ActionScope.REQUEST,
                    name="b",
                ),
            ],
            b"\x01\x03\x01\x01a\x04\x01\x02\x02\x03\x01b",
            "Action list: SetVar + UnsetVar",
        ),
    ],
    ids=lambda case: case[2],
)
def action_list_case(request):
    """Provides (actions, encoded, desc) for encoder/decoder tests."""
    return request.param
