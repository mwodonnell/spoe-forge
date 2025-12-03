import pytest

from spoe_forge.spop.encoders import data_types as data_type
from spoe_forge.spop.exception import SpopEncodeError


@pytest.mark.asyncio
async def test_compose_varint(varint_case):
    decoded, encoded, num_bytes, desc = varint_case

    result = await data_type._compose_varint(decoded)
    assert result == encoded
    assert num_bytes == len(encoded)


@pytest.mark.parametrize("value", [-1, 4328786160])
@pytest.mark.asyncio
async def test_parse_varint_raises_error(value):
    # Expected to raise an encode error as these are out of bounds
    with pytest.raises(SpopEncodeError):
        await data_type._compose_varint(value)
