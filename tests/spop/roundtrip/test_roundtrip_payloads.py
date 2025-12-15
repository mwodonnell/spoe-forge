import ipaddress

import pytest

from spoe_forge.spop.constants import ActionScope
from spoe_forge.spop.decoders import payloads as decoder
from spoe_forge.spop.encoders import payloads as encoder
from spoe_forge.spop.spop_types import Flags
from spoe_forge.spop.spop_types import MetaData
from spoe_forge.spop.spop_types import SetVarAction
from spoe_forge.spop.spop_types import UnsetVarAction


@pytest.mark.asyncio
async def test_roundtrip_kv_pair(kv_pair_data):
    key, value, desc = kv_pair_data

    encoded = await encoder._compose_kv_pair(key, value)
    result_key, result_val, offset = await decoder._parse_kv_pair(encoded, 0)

    assert result_key == key
    assert result_val == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_kv_pair_complex_types():
    test_cases = [
        ("string_val", "hello world"),
        ("int_val", 123456),
        ("bool_true", True),
        ("bool_false", False),
        ("ipv4_val", ipaddress.IPv4Address("192.168.1.1")),
        ("ipv6_val", ipaddress.IPv6Address("2001:db8::1")),
        ("bytes_val", b"\x00\xff\xaa\x55"),
        ("null_val", None),
    ]

    for key, value in test_cases:
        encoded = await encoder._compose_kv_pair(key, value)
        result_key, result_val, offset = await decoder._parse_kv_pair(encoded, 0)

        assert result_key == key
        assert result_val == value
        assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_metadata(metadata_data):
    metadata_obj, desc = metadata_data

    encoded = await encoder.encode_metadata(metadata_obj)
    result, offset = await decoder.decode_metadata(encoded, 0)

    assert result.flags.FIN == metadata_obj.flags.FIN
    assert result.flags.ABORT == metadata_obj.flags.ABORT
    assert result.stream_id == metadata_obj.stream_id
    assert result.frame_id == metadata_obj.frame_id
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_metadata_edge_cases():
    test_cases = [
        MetaData(flags=Flags(FIN=False, ABORT=False), stream_id=0, frame_id=0),
        MetaData(flags=Flags(FIN=True, ABORT=True), stream_id=0, frame_id=0),
        MetaData(flags=Flags(FIN=True, ABORT=False), stream_id=999999, frame_id=999999),
        MetaData(
            flags=Flags(FIN=True, ABORT=False), stream_id=4328786159, frame_id=1000000
        ),
    ]

    for metadata in test_cases:
        encoded = await encoder.encode_metadata(metadata)
        result, offset = await decoder.decode_metadata(encoded, 0)

        assert result.flags.FIN == metadata.flags.FIN
        assert result.flags.ABORT == metadata.flags.ABORT
        assert result.stream_id == metadata.stream_id
        assert result.frame_id == metadata.frame_id


@pytest.mark.asyncio
async def test_roundtrip_kv_list(kv_list_data):
    kv_dict, desc = kv_list_data

    encoded = await encoder.encode_kv_list(kv_dict)
    result, offset = await decoder.decode_kv_list(encoded, 0, len(encoded))

    assert result == kv_dict
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_kv_list_empty():
    kv_dict = {}

    encoded = await encoder.encode_kv_list(kv_dict)
    result, offset = await decoder.decode_kv_list(encoded, 0, len(encoded))

    assert result == {}
    assert offset == 0


@pytest.mark.asyncio
async def test_roundtrip_kv_list_mixed_types():
    kv_dict = {
        "str": "value",
        "int": 42,
        "bool": True,
        "ip": ipaddress.IPv4Address("10.0.0.1"),
        "data": b"\x00\x01\x02",
    }

    encoded = await encoder.encode_kv_list(kv_dict)
    result, offset = await decoder.decode_kv_list(encoded, 0, len(encoded))

    assert result == kv_dict
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_kv_list_with_offset():
    kv_dict = {"a": 1, "b": 2}
    prefix = b"\xff\xff\xff\xff"

    encoded_kv = await encoder.encode_kv_list(kv_dict)
    full_buffer = prefix + encoded_kv

    result, offset = await decoder.decode_kv_list(
        full_buffer, len(prefix), len(full_buffer)
    )

    assert result == kv_dict
    assert offset == len(full_buffer)


@pytest.mark.asyncio
async def test_roundtrip_message_list(message_list_data):
    messages_dict, desc = message_list_data

    encoded = await encoder.encode_message_list(messages_dict)
    result, offset = await decoder.decode_list_of_messages(encoded, 0, len(encoded))

    assert result == messages_dict
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_message_list_empty():
    messages = {}

    encoded = await encoder.encode_message_list(messages)
    result, offset = await decoder.decode_list_of_messages(encoded, 0, len(encoded))

    assert result == messages
    assert offset == 0


@pytest.mark.asyncio
async def test_roundtrip_message_list_complex():
    messages = {
        "check-ip": {
            "src": ipaddress.IPv4Address("192.168.1.1"),
            "dst": ipaddress.IPv4Address("10.0.0.1"),
        },
        "check-user": {
            "username": "admin",
            "active": True,
            "score": 95,
        },
        "log-event": {
            "message": "test",
            "level": 3,
        },
    }

    encoded = await encoder.encode_message_list(messages)
    result, offset = await decoder.decode_list_of_messages(encoded, 0, len(encoded))

    assert result == messages
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_message_list_with_offset():
    messages = {"test": {"arg": 1}}
    prefix = b"\xaa\xbb\xcc"

    encoded_messages = await encoder.encode_message_list(messages)
    full_buffer = prefix + encoded_messages

    result, offset = await decoder.decode_list_of_messages(
        full_buffer, len(prefix), len(full_buffer)
    )

    assert result == messages
    assert offset == len(full_buffer)


@pytest.mark.asyncio
async def test_roundtrip_action(action_data):
    action_obj, desc = action_data

    encoded = await encoder._compose_action(action_obj)
    result, offset = await decoder.decode_list_of_actions(encoded, 0, len(encoded))

    assert len(result) == 1
    assert isinstance(result[0], type(action_obj))
    assert result[0].scope == action_obj.scope
    assert result[0].name == action_obj.name
    if isinstance(action_obj, SetVarAction):
        assert result[0].value == action_obj.value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_action_set_var_all_scopes():
    scopes = [
        ActionScope.PROCESS,
        ActionScope.SESSION,
        ActionScope.TRANSACTION,
        ActionScope.REQUEST,
        ActionScope.RESPONSE,
    ]

    for scope in scopes:
        action = SetVarAction(scope=scope, name="test", value=42)

        encoded = await encoder._compose_action(action)
        result, offset = await decoder.decode_list_of_actions(encoded, 0, len(encoded))

        assert len(result) == 1
        assert isinstance(result[0], SetVarAction)
        assert result[0].scope == scope
        assert result[0].name == "test"
        assert result[0].value == 42


@pytest.mark.asyncio
async def test_roundtrip_action_set_var_all_types():
    test_values = [
        ("int", 123),
        ("bool_true", True),
        ("bool_false", False),
        ("string", "hello"),
        ("bytes", b"\x00\xff"),
        ("ipv4", ipaddress.IPv4Address("192.168.1.1")),
        ("ipv6", ipaddress.IPv6Address("::1")),
        ("null", None),
    ]

    for name, value in test_values:
        action = SetVarAction(scope=ActionScope.SESSION, name=name, value=value)

        encoded = await encoder._compose_action(action)
        result, offset = await decoder.decode_list_of_actions(encoded, 0, len(encoded))

        assert len(result) == 1
        assert result[0].name == name
        assert result[0].value == value


@pytest.mark.asyncio
async def test_roundtrip_action_unset_var_all_scopes():
    scopes = [
        ActionScope.PROCESS,
        ActionScope.SESSION,
        ActionScope.TRANSACTION,
        ActionScope.REQUEST,
        ActionScope.RESPONSE,
    ]

    for scope in scopes:
        action = UnsetVarAction(scope=scope, name="test")

        encoded = await encoder._compose_action(action)
        result, offset = await decoder.decode_list_of_actions(encoded, 0, len(encoded))

        assert len(result) == 1
        assert isinstance(result[0], UnsetVarAction)
        assert result[0].scope == scope
        assert result[0].name == "test"


@pytest.mark.asyncio
async def test_roundtrip_action_list(action_list_data):
    """Test action list encoding/decoding round-trip."""
    actions, desc = action_list_data

    encoded = await encoder.encode_action_list(actions)
    result, offset = await decoder.decode_list_of_actions(encoded, 0, len(encoded))

    assert len(result) == len(actions)
    for i, action in enumerate(actions):
        assert isinstance(result[i], type(action))
        assert result[i].scope == action.scope
        assert result[i].name == action.name
        if isinstance(action, SetVarAction):
            assert result[i].value == action.value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_roundtrip_action_list_empty():
    actions = []

    encoded = await encoder.encode_action_list(actions)
    result, offset = await decoder.decode_list_of_actions(encoded, 0, 0)

    assert result == []
    assert offset == 0


@pytest.mark.asyncio
async def test_roundtrip_action_list_multiple():
    actions = [
        SetVarAction(scope=ActionScope.SESSION, name="a", value=1),
        SetVarAction(scope=ActionScope.REQUEST, name="b", value="test"),
        UnsetVarAction(scope=ActionScope.SESSION, name="c"),
        SetVarAction(scope=ActionScope.RESPONSE, name="d", value=True),
        UnsetVarAction(scope=ActionScope.TRANSACTION, name="e"),
    ]

    encoded = await encoder.encode_action_list(actions)
    result, offset = await decoder.decode_list_of_actions(encoded, 0, len(encoded))

    assert len(result) == len(actions)
    for i, action in enumerate(actions):
        assert isinstance(result[i], type(action))
        assert result[i].scope == action.scope
        assert result[i].name == action.name
        if isinstance(action, SetVarAction):
            assert result[i].value == action.value


@pytest.mark.asyncio
async def test_roundtrip_full_notify_payload():
    metadata = MetaData(
        flags=Flags(FIN=True, ABORT=False),
        stream_id=123,
        frame_id=456,
    )

    messages = {
        "check-request": {
            "method": "GET",
            "path": "/api/test",
            "src": ipaddress.IPv4Address("192.168.1.100"),
        }
    }

    encoded_metadata = await encoder.encode_metadata(metadata)
    encoded_messages = await encoder.encode_message_list(messages)
    full_payload = encoded_metadata + encoded_messages

    decoded_metadata, offset = await decoder.decode_metadata(full_payload, 0)
    decoded_messages, final_offset = await decoder.decode_list_of_messages(
        full_payload, offset, len(full_payload)
    )

    assert decoded_metadata.flags.FIN == metadata.flags.FIN
    assert decoded_metadata.flags.ABORT == metadata.flags.ABORT
    assert decoded_metadata.stream_id == metadata.stream_id
    assert decoded_metadata.frame_id == metadata.frame_id
    assert decoded_messages == messages
    assert final_offset == len(full_payload)


@pytest.mark.asyncio
async def test_roundtrip_full_ack_payload():
    metadata = MetaData(
        flags=Flags(FIN=True, ABORT=False),
        stream_id=123,
        frame_id=456,
    )

    actions = [
        SetVarAction(scope=ActionScope.SESSION, name="score", value=95),
        SetVarAction(scope=ActionScope.REQUEST, name="blocked", value=False),
        UnsetVarAction(scope=ActionScope.SESSION, name="temp"),
    ]

    encoded_metadata = await encoder.encode_metadata(metadata)
    encoded_actions = await encoder.encode_action_list(actions)
    full_payload = encoded_metadata + encoded_actions

    decoded_metadata, offset = await decoder.decode_metadata(full_payload, 0)
    decoded_actions, final_offset = await decoder.decode_list_of_actions(
        full_payload, offset, len(full_payload)
    )

    assert decoded_metadata.flags.FIN == metadata.flags.FIN
    assert decoded_metadata.stream_id == metadata.stream_id
    assert decoded_metadata.frame_id == metadata.frame_id
    assert len(decoded_actions) == len(actions)
    for i, action in enumerate(actions):
        assert isinstance(decoded_actions[i], type(action))
        assert decoded_actions[i].scope == action.scope
        assert decoded_actions[i].name == action.name
        if isinstance(action, SetVarAction):
            assert decoded_actions[i].value == action.value

    assert final_offset == len(full_payload)
