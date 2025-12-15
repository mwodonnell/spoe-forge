from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from spoe_forge.spop.constants import ActionScope
from spoe_forge.spop.decoders import payloads as payload
from spoe_forge.spop.exception import SpopDecodeError
from spoe_forge.spop.spop_types import SetVarAction
from spoe_forge.spop.spop_types import UnsetVarAction


@pytest.mark.asyncio
async def test_parse_kv_pair(kv_pair_case):
    key, value, encoded, desc = kv_pair_case

    result_key, result_val, offset = await payload._parse_kv_pair(encoded, 0)

    assert result_key == key
    assert result_val == value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_parse_kv_pair_calls_lower_level_functions():
    test_buf = b"\x04test\x04\x2a"  # "test" -> 42

    with (
        patch(
            "spoe_forge.spop.decoders.payloads.decode_string", new_callable=AsyncMock
        ) as mock_decode_string,
        patch(
            "spoe_forge.spop.decoders.payloads.auto_decode_var", new_callable=AsyncMock
        ) as mock_auto_decode,
    ):
        mock_decode_string.return_value = ("test", 5)
        mock_auto_decode.return_value = (42, 7)

        key, val, offset = await payload._parse_kv_pair(test_buf, 0)

        mock_decode_string.assert_called_once_with(test_buf, 0)
        mock_auto_decode.assert_called_once_with(test_buf, 5)
        assert key == "test"
        assert val == 42
        assert offset == 7


@pytest.mark.asyncio
async def test_decode_metadata(metadata_case):
    metadata_obj, encoded, desc = metadata_case

    result, offset = await payload.decode_metadata(encoded, 0)

    assert result.flags.FIN == metadata_obj.flags.FIN
    assert result.flags.ABORT == metadata_obj.flags.ABORT
    assert result.stream_id == metadata_obj.stream_id
    assert result.frame_id == metadata_obj.frame_id
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_decode_metadata_calls_decode_int64():
    test_buf = b"\x00\x00\x00\x01\x01\x02"

    with patch(
        "spoe_forge.spop.decoders.payloads.decode_int64", new_callable=AsyncMock
    ) as mock_decode_int64:
        mock_decode_int64.side_effect = [(1, 5), (2, 6)]

        result, offset = await payload.decode_metadata(test_buf, 0)

        assert mock_decode_int64.call_count == 2
        assert result.stream_id == 1
        assert result.frame_id == 2


@pytest.mark.asyncio
async def test_decode_metadata_raises_on_short_buffer():
    short_buf = b"\x00\x00"

    with pytest.raises(SpopDecodeError, match="unexpected end of stream"):
        await payload.decode_metadata(short_buf, 0)


@pytest.mark.asyncio
async def test_decode_metadata_raises_on_stream_id_error():
    test_buf = b"\x00\x00\x00\x01\xff\xff"

    with patch(
        "spoe_forge.spop.decoders.payloads.decode_int64", new_callable=AsyncMock
    ) as mock_decode:
        mock_decode.side_effect = SpopDecodeError("test error")

        with pytest.raises(SpopDecodeError, match="error decoding stream_id"):
            await payload.decode_metadata(test_buf, 0)


@pytest.mark.asyncio
async def test_decode_metadata_raises_on_frame_id_error():
    test_buf = b"\x00\x00\x00\x01\x01"

    with (
        patch(
            "spoe_forge.spop.decoders.payloads.decode_int64", new_callable=AsyncMock
        ) as mock_decode,
    ):
        mock_decode.side_effect = [(1, 5), SpopDecodeError("test error")]

        with pytest.raises(SpopDecodeError, match="error decoding frame_id"):
            await payload.decode_metadata(test_buf, 0)


@pytest.mark.asyncio
async def test_decode_kv_list(kv_list_case):
    kv_dict, encoded, desc = kv_list_case

    result, offset = await payload.decode_kv_list(encoded, 0, len(encoded))

    assert result == kv_dict
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_decode_kv_list_empty():
    result, offset = await payload.decode_kv_list(b"", 0, 0)

    assert result == {}
    assert offset == 0


@pytest.mark.asyncio
async def test_decode_kv_list_with_offset():
    buf = b"\xff\xff\x01a\x04\x01"  # Prefix + "a" -> 1
    result, offset = await payload.decode_kv_list(buf, 2, 6)

    assert result == {"a": 1}
    assert offset == 6


@pytest.mark.asyncio
async def test_decode_kv_list_calls_parse_kv_pair():
    test_buf = b"\x01a\x04\x01\x01b\x04\x02"  # "a"->1, "b"->2

    with patch(
        "spoe_forge.spop.decoders.payloads._parse_kv_pair", new_callable=AsyncMock
    ) as mock_parse:
        mock_parse.side_effect = [("a", 1, 4), ("b", 2, 8)]

        result, offset = await payload.decode_kv_list(test_buf, 0, 8)

        assert mock_parse.call_count == 2
        assert result == {"a": 1, "b": 2}


@pytest.mark.asyncio
async def test_decode_list_of_messages(message_list_case):
    messages_dict, encoded, desc = message_list_case

    result, offset = await payload.decode_list_of_messages(encoded, 0, len(encoded))

    assert result == messages_dict
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_decode_list_of_messages_empty():
    result, offset = await payload.decode_list_of_messages(b"", 0, 0)

    assert result == {}
    assert offset == 0


@pytest.mark.asyncio
async def test_decode_list_of_messages_with_offset():
    buf = b"\xff\xff\x04test\x00"  # Prefix + "test" with no args
    result, offset = await payload.decode_list_of_messages(buf, 2, 8)

    assert result == {"test": {}}
    assert offset == 8


@pytest.mark.asyncio
async def test_decode_list_of_messages_calls_lower_level_functions():
    test_buf = b"\x04test\x01\x01a\x04\x01"  # "test" with 1 arg: "a"->1

    with (
        patch(
            "spoe_forge.spop.decoders.payloads.decode_string", new_callable=AsyncMock
        ) as mock_decode_string,
        patch(
            "spoe_forge.spop.decoders.payloads.decode_tiny_int", new_callable=AsyncMock
        ) as mock_decode_tiny,
        patch(
            "spoe_forge.spop.decoders.payloads._parse_kv_pair", new_callable=AsyncMock
        ) as mock_parse_kv,
    ):
        mock_decode_string.return_value = ("test", 5)
        mock_decode_tiny.return_value = (1, 6)
        mock_parse_kv.return_value = ("a", 1, 10)

        result, offset = await payload.decode_list_of_messages(test_buf, 0, 10)

        mock_decode_string.assert_called_once_with(test_buf, 0)
        mock_decode_tiny.assert_called_once_with(test_buf, 5)
        mock_parse_kv.assert_called_once_with(test_buf, 6)
        assert result == {"test": {"a": 1}}


@pytest.mark.asyncio
async def test_decode_list_of_messages_raises_on_duplicate_arg():
    test_buf = b"\x04test\x02\x03dup\x04\x01\x03dup\x04\x02"

    with pytest.raises(SpopDecodeError, match="unexpected duplicate arg"):
        await payload.decode_list_of_messages(test_buf, 0, len(test_buf))


@pytest.mark.asyncio
async def test_decode_list_of_actions_set_var(action_case):
    action_obj, encoded, desc = action_case

    result, offset = await payload.decode_list_of_actions(encoded, 0, len(encoded))

    assert len(result) == 1
    assert isinstance(result[0], type(action_obj))
    assert result[0].scope == action_obj.scope
    assert result[0].name == action_obj.name
    if isinstance(action_obj, SetVarAction):
        assert result[0].value == action_obj.value
    assert offset == len(encoded)


@pytest.mark.asyncio
async def test_decode_list_of_actions_empty():
    result, offset = await payload.decode_list_of_actions(b"\x00", 0, 0)

    assert result == []
    assert offset == 0


@pytest.mark.asyncio
async def test_decode_list_of_actions_multiple():
    test_buf = b"\x01\x03\x01\x01a\x04\x01\x02\x02\x03\x01b"

    result, offset = await payload.decode_list_of_actions(test_buf, 0, len(test_buf))

    assert len(result) == 2
    assert isinstance(result[0], SetVarAction)
    assert result[0].scope == ActionScope.SESSION
    assert result[0].name == "a"
    assert result[0].value == 1

    assert isinstance(result[1], UnsetVarAction)
    assert result[1].scope == ActionScope.REQUEST
    assert result[1].name == "b"


@pytest.mark.asyncio
async def test_decode_list_of_actions_calls_parse_kv_pair_for_set_var():
    test_buf = b"\x01\x03\x02\x01a\x04\x01"  # SetVar(session, "a", 1)

    with patch(
        "spoe_forge.spop.decoders.payloads._parse_kv_pair", new_callable=AsyncMock
    ) as mock_parse:
        mock_parse.return_value = ("a", 1, 10)

        result, offset = await payload.decode_list_of_actions(
            test_buf, 0, len(test_buf)
        )

        mock_parse.assert_called_once()
        assert len(result) == 1
        assert isinstance(result[0], SetVarAction)


@pytest.mark.asyncio
async def test_decode_list_of_actions_calls_decode_string_for_unset_var():
    test_buf = b"\x02\x02\x02\x04temp"  # UnsetVar(session, "temp")

    with patch(
        "spoe_forge.spop.decoders.payloads.decode_string", new_callable=AsyncMock
    ) as mock_decode:
        mock_decode.return_value = ("temp", 9)

        result, offset = await payload.decode_list_of_actions(
            test_buf, 0, len(test_buf)
        )

        mock_decode.assert_called_once()
        assert len(result) == 1
        assert isinstance(result[0], UnsetVarAction)


@pytest.mark.asyncio
async def test_decode_list_of_actions_raises_on_invalid_action_type():
    test_buf = b"\xff\x03\x02"

    with pytest.raises(SpopDecodeError, match="invalid action type"):
        await payload.decode_list_of_actions(test_buf, 0, len(test_buf))


@pytest.mark.asyncio
async def test_decode_list_of_actions_raises_on_invalid_scope():
    test_buf = b"\x01\x03\xff"

    with pytest.raises(SpopDecodeError, match="invalid action scope"):
        await payload.decode_list_of_actions(test_buf, 0, len(test_buf))


@pytest.mark.asyncio
async def test_decode_list_of_actions_raises_on_unknown_action():
    test_buf = b"\x03\x03\x02"

    with pytest.raises(SpopDecodeError, match="invalid action type"):
        await payload.decode_list_of_actions(test_buf, 0, len(test_buf))
