from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from spoe_forge.spop.constants import ActionScope
from spoe_forge.spop.encoders import payloads as payload
from spoe_forge.spop.exception import SpopEncodeError
from spoe_forge.spop.spop_types import Flags
from spoe_forge.spop.spop_types import MetaData
from spoe_forge.spop.spop_types import SetVarAction
from spoe_forge.spop.spop_types import UnsetVarAction


@pytest.mark.asyncio
async def test_compose_kv_pair(kv_pair_case):
    key, value, encoded, desc = kv_pair_case

    result = await payload._compose_kv_pair(key, value)

    assert result == encoded


@pytest.mark.asyncio
async def test_compose_kv_pair_calls_lower_level_functions():
    with (
        patch(
            "spoe_forge.spop.encoders.payloads.encode_string", new_callable=AsyncMock
        ) as mock_encode_string,
        patch(
            "spoe_forge.spop.encoders.payloads.auto_encode_dt_var",
            new_callable=AsyncMock,
        ) as mock_auto_encode,
    ):
        mock_encode_string.return_value = b"\x04test"
        mock_auto_encode.return_value = b"\x04\x2a"

        result = await payload._compose_kv_pair("test", 42)

        mock_encode_string.assert_called_once_with("test")
        mock_auto_encode.assert_called_once_with(42)
        assert result == b"\x04test\x04\x2a"


@pytest.mark.asyncio
async def test_encode_metadata(metadata_case):
    metadata_obj, encoded, desc = metadata_case

    result = await payload.encode_metadata(metadata_obj)

    assert result == encoded


@pytest.mark.asyncio
async def test_encode_metadata_calls_encode_int():
    test_metadata = MetaData(
        flags=Flags(FIN=True, ABORT=False),
        stream_id=1,
        frame_id=2,
    )

    with patch(
        "spoe_forge.spop.encoders.payloads.encode_int", new_callable=AsyncMock
    ) as mock_encode_int:
        mock_encode_int.side_effect = [b"\x01", b"\x02"]

        await payload.encode_metadata(test_metadata)

        assert mock_encode_int.call_count == 2
        mock_encode_int.assert_any_call(1)
        mock_encode_int.assert_any_call(2)


@pytest.mark.asyncio
async def test_encode_metadata_fin_flag():
    metadata = MetaData(
        flags=Flags(FIN=True, ABORT=False),
        stream_id=0,
        frame_id=0,
    )

    result = await payload.encode_metadata(metadata)

    assert result[3] == 0x01  # FrameFlag.FIN


@pytest.mark.asyncio
async def test_encode_metadata_abort_flag():
    metadata = MetaData(
        flags=Flags(FIN=False, ABORT=True),
        stream_id=0,
        frame_id=0,
    )

    result = await payload.encode_metadata(metadata)

    assert result[3] == 0x02  # FrameFlag.ABORT


@pytest.mark.asyncio
async def test_encode_metadata_both_flags():
    metadata = MetaData(
        flags=Flags(FIN=True, ABORT=True),
        stream_id=0,
        frame_id=0,
    )

    result = await payload.encode_metadata(metadata)

    assert result[3] == 0x03


@pytest.mark.asyncio
async def test_encode_kv_list(kv_list_case):
    kv_dict, encoded, desc = kv_list_case

    result = await payload.encode_kv_list(kv_dict)

    assert result == encoded


@pytest.mark.asyncio
async def test_encode_kv_list_empty():
    result = await payload.encode_kv_list({})

    assert result == b""


@pytest.mark.asyncio
async def test_encode_kv_list_calls_compose_kv_pair():
    test_dict = {"a": 1, "b": 2}

    with patch(
        "spoe_forge.spop.encoders.payloads._compose_kv_pair", new_callable=AsyncMock
    ) as mock_compose:
        mock_compose.side_effect = [b"\x01a\x04\x01", b"\x01b\x04\x02"]

        result = await payload.encode_kv_list(test_dict)

        assert mock_compose.call_count == 2
        assert result == b"\x01a\x04\x01\x01b\x04\x02"


@pytest.mark.asyncio
async def test_encode_message_list(message_list_case):
    messages_dict, encoded, desc = message_list_case

    result = await payload.encode_message_list(messages_dict)

    assert result == encoded


@pytest.mark.asyncio
async def test_encode_message_list_empty():
    result = await payload.encode_message_list({})

    assert result == b""


@pytest.mark.asyncio
async def test_encode_message_list_calls_lower_level_functions():
    test_messages = {"test": {"a": 1}}

    with (
        patch(
            "spoe_forge.spop.encoders.payloads.encode_string", new_callable=AsyncMock
        ) as mock_encode_string,
        patch(
            "spoe_forge.spop.encoders.payloads.encode_tiny_int", new_callable=AsyncMock
        ) as mock_encode_tiny,
        patch(
            "spoe_forge.spop.encoders.payloads._compose_kv_pair", new_callable=AsyncMock
        ) as mock_compose_kv,
    ):
        mock_encode_string.return_value = b"\x04test"
        mock_encode_tiny.return_value = b"\x01"
        mock_compose_kv.return_value = b"\x01a\x04\x01"

        result = await payload.encode_message_list(test_messages)

        mock_encode_string.assert_called_once_with("test")
        mock_encode_tiny.assert_called_once_with(1)
        mock_compose_kv.assert_called_once_with("a", 1)
        assert result == b"\x04test\x01\x01a\x04\x01"


@pytest.mark.asyncio
async def test_encode_message_list_raises_on_too_many_args():
    large_message = {f"arg{i}": i for i in range(256)}
    messages = {"test": large_message}

    with pytest.raises(SpopEncodeError, match="too many args"):
        await payload.encode_message_list(messages)


@pytest.mark.asyncio
async def test_compose_action_set_var(action_case):
    action_obj, encoded, desc = action_case

    result = await payload._compose_action(action_obj)

    assert result == encoded


@pytest.mark.asyncio
async def test_compose_action_raises_on_unknown_type():
    class UnknownAction:
        pass

    unknown = UnknownAction()

    with pytest.raises(SpopEncodeError, match="Unexpected Action"):
        await payload._compose_action(unknown)


@pytest.mark.asyncio
async def test_compose_set_action_calls_lower_level_functions():
    action = SetVarAction(
        scope=ActionScope.SESSION,
        name="test",
        value=42,
    )

    with (
        patch(
            "spoe_forge.spop.encoders.payloads.encode_string", new_callable=AsyncMock
        ) as mock_encode_string,
        patch(
            "spoe_forge.spop.encoders.payloads.auto_encode_dt_var",
            new_callable=AsyncMock,
        ) as mock_auto_encode,
    ):
        mock_encode_string.return_value = b"\x04test"
        mock_auto_encode.return_value = b"\x04\x2a"

        await payload._compose_action(action)

        mock_encode_string.assert_called_once_with("test")
        mock_auto_encode.assert_called_once_with(42)


@pytest.mark.asyncio
async def test_compose_unset_action_calls_encode_string():
    action = UnsetVarAction(
        scope=ActionScope.SESSION,
        name="test",
    )

    with patch(
        "spoe_forge.spop.encoders.payloads.encode_string", new_callable=AsyncMock
    ) as mock_encode_string:
        mock_encode_string.return_value = b"\x04test"

        await payload._compose_action(action)

        mock_encode_string.assert_called_once_with("test")


@pytest.mark.asyncio
async def test_encode_action_list(action_list_case):
    actions, encoded, desc = action_list_case

    result = await payload.encode_action_list(actions)

    assert result == encoded


@pytest.mark.asyncio
async def test_encode_action_list_empty():
    result = await payload.encode_action_list([])

    assert result == b""


@pytest.mark.asyncio
async def test_encode_action_list_calls_compose_action():
    actions = [
        SetVarAction(scope=ActionScope.SESSION, name="a", value=1),
        UnsetVarAction(scope=ActionScope.REQUEST, name="b"),
    ]

    with patch(
        "spoe_forge.spop.encoders.payloads._compose_action", new_callable=AsyncMock
    ) as mock_compose:
        mock_compose.side_effect = [
            b"\x01\x03\x02\x01a\x04\x01",
            b"\x02\x02\x03\x01b",
        ]

        result = await payload.encode_action_list(actions)

        assert mock_compose.call_count == 2
        assert result == b"\x01\x03\x02\x01a\x04\x01\x02\x02\x03\x01b"


@pytest.mark.asyncio
async def test_encode_action_list_multiple_set_vars():
    actions = [
        SetVarAction(scope=ActionScope.SESSION, name="x", value=1),
        SetVarAction(scope=ActionScope.REQUEST, name="y", value=2),
    ]

    result = await payload.encode_action_list(actions)

    assert result.startswith(b"\x01\x03")
    assert len(result) > 0
    assert b"\x01y\x04\x02" in result


@pytest.mark.asyncio
async def test_encode_action_list_multiple_unset_vars():
    actions = [
        UnsetVarAction(scope=ActionScope.SESSION, name="x"),
        UnsetVarAction(scope=ActionScope.REQUEST, name="y"),
    ]

    result = await payload.encode_action_list(actions)

    assert result.startswith(b"\x02\x02")
    assert len(result) > 0
    assert b"\x01y" in result
