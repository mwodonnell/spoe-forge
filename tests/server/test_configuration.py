from unittest.mock import patch

import pytest

from spoe_forge.server.configuration import ServerConfiguration
from spoe_forge.server.constants import DEFAULT_MAX_FRAME_SIZE
from spoe_forge.server.constants import SPOE_VERSION


def test_configuration_initialization_default():
    config = ServerConfiguration()

    assert config.version == SPOE_VERSION
    assert config.capabilities == []
    assert config.max_frame_size == DEFAULT_MAX_FRAME_SIZE
    assert config.is_compatible is True


def test_configuration_initialization_custom_frame_size():
    config = ServerConfiguration(max_frame_size=8192)

    assert config.max_frame_size == 8192
    assert config.version == SPOE_VERSION
    assert config.capabilities == []


@pytest.mark.asyncio
async def test_check_version_compatibility_success():
    config = ServerConfiguration()

    await config._check_version_compatibility(["2.0", "1.0"])

    assert config.is_compatible is True


@pytest.mark.asyncio
async def test_check_version_compatibility_exact_match():
    config = ServerConfiguration()

    await config._check_version_compatibility(["2.0"])

    assert config.is_compatible is True


@pytest.mark.asyncio
async def test_check_version_compatibility_higher_version():
    config = ServerConfiguration()

    await config._check_version_compatibility(["3.0", "2.0"])

    assert config.is_compatible is True


@pytest.mark.asyncio
async def test_check_version_compatibility_failure():
    config = ServerConfiguration()

    with patch("spoe_forge.server.configuration.logger") as mock_logger:
        await config._check_version_compatibility(["1.0"])

        assert config.is_compatible is False
        mock_logger.error.assert_called_once()
        assert "No compatible versions found" in mock_logger.error.call_args[0][0]


@pytest.mark.asyncio
async def test_check_version_compatibility_major_version_mismatch():
    config = ServerConfiguration()

    with patch("spoe_forge.server.configuration.logger") as mock_logger:
        await config._check_version_compatibility(["3.0"])

        assert config.is_compatible is False
        mock_logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_check_version_compatibility_same_major_higher_minor():
    config = ServerConfiguration()

    await config._check_version_compatibility(["2.5"])

    assert config.is_compatible is True


@pytest.mark.asyncio
async def test_check_version_compatibility_multiple_versions():
    config = ServerConfiguration()

    await config._check_version_compatibility(["1.0", "1.5", "2.0", "2.5"])

    assert config.is_compatible is True


@pytest.mark.asyncio
async def test_find_max_frame_size_uses_minimum():
    config = ServerConfiguration(max_frame_size=8192)

    await config._find_max_frame_size(16384)

    assert config.max_frame_size == 8192
    assert config.is_compatible is True


@pytest.mark.asyncio
async def test_find_max_frame_size_haproxy_smaller():
    config = ServerConfiguration(max_frame_size=16384)

    await config._find_max_frame_size(4096)

    assert config.max_frame_size == 4096
    assert config.is_compatible is True


@pytest.mark.asyncio
async def test_find_max_frame_size_equal():
    config = ServerConfiguration(max_frame_size=8192)

    await config._find_max_frame_size(8192)

    assert config.max_frame_size == 8192
    assert config.is_compatible is True


@pytest.mark.asyncio
async def test_find_max_frame_size_zero_fails():
    config = ServerConfiguration(max_frame_size=0)

    with patch("spoe_forge.server.configuration.logger") as mock_logger:
        await config._find_max_frame_size(8192)

        assert config.max_frame_size == 0
        assert config.is_compatible is False
        mock_logger.error.assert_called_once()
        assert "Frame size negotiation failed" in mock_logger.error.call_args[0][0]


@pytest.mark.asyncio
async def test_find_max_frame_size_negative_fails():
    config = ServerConfiguration(max_frame_size=8192)

    with patch("spoe_forge.server.configuration.logger") as mock_logger:
        await config._find_max_frame_size(-100)

        assert config.max_frame_size == -100
        assert config.is_compatible is False
        mock_logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_find_common_capabilities_with_pipelining():
    config = ServerConfiguration()

    await config._find_common_capabilities(["pipelining", "async"])

    assert "pipelining" in config.capabilities
    assert config.is_compatible is True


@pytest.mark.asyncio
async def test_find_common_capabilities_pipelining_only():
    config = ServerConfiguration()

    await config._find_common_capabilities(["pipelining"])

    assert config.capabilities == ["pipelining"]
    assert config.is_compatible is True


@pytest.mark.asyncio
async def test_find_common_capabilities_no_pipelining():
    config = ServerConfiguration()

    with patch("spoe_forge.server.configuration.logger") as mock_logger:
        await config._find_common_capabilities(["async", "fragmentation"])

        assert "pipelining" not in config.capabilities
        assert config.is_compatible is True
        mock_logger.warning.assert_called_once()
        assert (
            "Pipelining capability is not supported"
            in mock_logger.warning.call_args[0][0]
        )


@pytest.mark.asyncio
async def test_find_common_capabilities_empty():
    config = ServerConfiguration()

    with patch("spoe_forge.server.configuration.logger") as mock_logger:
        await config._find_common_capabilities([])

        assert config.capabilities == []
        assert config.is_compatible is True
        mock_logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_find_common_capabilities_intersection():
    config = ServerConfiguration()

    await config._find_common_capabilities(["pipelining", "async", "fragmentation"])

    assert config.capabilities == ["pipelining"]


@pytest.mark.asyncio
async def test_negotiate_server_compatibility_success():
    config = ServerConfiguration(max_frame_size=8192)

    await config.negotiate_server_compatibility(
        supported_versions=["2.0", "1.0"],
        ha_max_frame_size=16384,
        ha_capabilities=["pipelining", "async"],
    )

    assert config.is_compatible is True
    assert config.version == "2.0"
    assert config.max_frame_size == 8192
    assert "pipelining" in config.capabilities


@pytest.mark.asyncio
async def test_negotiate_server_compatibility_version_mismatch():
    config = ServerConfiguration()

    with patch("spoe_forge.server.configuration.logger") as mock_logger:
        await config.negotiate_server_compatibility(
            supported_versions=["1.0"],
            ha_max_frame_size=8192,
            ha_capabilities=["pipelining"],
        )

        mock_logger.error.assert_called_once()
        assert "No compatible versions found" in mock_logger.error.call_args[0][0]
        assert config.is_compatible is False


@pytest.mark.asyncio
async def test_negotiate_server_compatibility_calls_all_methods():
    config = ServerConfiguration()

    with (
        patch.object(config, "_check_version_compatibility") as mock_version,
        patch.object(config, "_find_max_frame_size") as mock_frame,
        patch.object(config, "_find_common_capabilities") as mock_caps,
    ):
        await config.negotiate_server_compatibility(
            supported_versions=["2.0"],
            ha_max_frame_size=8192,
            ha_capabilities=["pipelining"],
        )

        mock_version.assert_called_once_with(["2.0"])
        mock_frame.assert_called_once_with(8192)
        mock_caps.assert_called_once_with(["pipelining"])


def test_is_compatible_property():
    config = ServerConfiguration()

    assert config.is_compatible is True

    config._server_compatible = False
    assert config.is_compatible is False


def test_version_property():
    config = ServerConfiguration()

    assert config.version == SPOE_VERSION


def test_max_frame_size_property():
    config = ServerConfiguration(max_frame_size=8192)

    assert config.max_frame_size == 8192


def test_capabilities_property():
    config = ServerConfiguration()

    assert config.capabilities == []

    config._capabilities = ["pipelining"]
    assert config.capabilities == ["pipelining"]


@pytest.mark.asyncio
async def test_multiple_negotiations():
    config = ServerConfiguration(max_frame_size=8192)

    await config.negotiate_server_compatibility(
        supported_versions=["2.0"],
        ha_max_frame_size=4096,
        ha_capabilities=["pipelining"],
    )

    assert config.max_frame_size == 4096
    assert config.is_compatible is True

    await config.negotiate_server_compatibility(
        supported_versions=["2.0"],
        ha_max_frame_size=2048,
        ha_capabilities=[],
    )

    assert config.max_frame_size == 2048


@pytest.mark.asyncio
async def test_default_configuration_values():
    config = ServerConfiguration()

    assert config.version == "2.0"
    assert config.max_frame_size == DEFAULT_MAX_FRAME_SIZE
    assert config.capabilities == []
    assert config.is_compatible is True


@pytest.mark.asyncio
async def test_large_frame_size():
    config = ServerConfiguration(max_frame_size=1024 * 1024)  # 1MB

    await config.negotiate_server_compatibility(
        supported_versions=["2.0"],
        ha_max_frame_size=1024 * 512,
        ha_capabilities=["pipelining"],
    )

    assert config.max_frame_size == 1024 * 512
    assert config.is_compatible is True
