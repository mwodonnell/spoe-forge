import asyncio
from unittest.mock import AsyncMock
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from spoe_forge.agent.context import AgentContext
from spoe_forge.server.constants import DEFAULT_MAX_FRAME_SIZE
from spoe_forge.spoe_forge import SpoeForge
from spoe_forge.spop.constants import ActionScope
from spoe_forge.spop.spop_types import SetVarAction


def test_spoe_forge_initialization():
    forge = SpoeForge(name="test-agent")

    assert forge.name == "test-agent"
    assert forge._max_frame_size == DEFAULT_MAX_FRAME_SIZE
    assert forge._debug is False
    assert forge._registry is not None


def test_spoe_forge_initialization_custom_frame_size():
    forge = SpoeForge(name="test-agent", max_frame_size=8192)

    assert forge._max_frame_size == 8192


def test_spoe_forge_initialization_debug_mode():
    forge = SpoeForge(name="test-agent", debug=True)

    assert forge._debug is True


def test_logger_lazy_initialization():
    forge = SpoeForge(name="test-agent")

    assert "_logger" not in forge.__dict__

    logger = forge._logger

    assert "_logger" in forge.__dict__
    assert logger is not None


def test_logger_uses_debug_flag():
    forge_debug = SpoeForge(name="test-agent", debug=True)
    forge_normal = SpoeForge(name="test-agent", debug=False)

    assert forge_debug._logger is not None
    assert forge_normal._logger is not None


def test_message_decorator_registers_handler():
    forge = SpoeForge(name="test-agent")

    @forge.message("test-message")
    def handler(ctx: AgentContext):
        return []

    assert "test-message" in forge._registry._handlers
    assert forge._registry._handlers["test-message"] == handler


def test_message_decorator_returns_original_function():
    forge = SpoeForge(name="test-agent")

    def handler(ctx: AgentContext):
        return []

    decorated = forge.message("test-message")(handler)

    assert decorated is handler


def test_message_decorator_multiple_handlers():
    forge = SpoeForge(name="test-agent")

    @forge.message("message1")
    def handler1(ctx: AgentContext):
        return []

    @forge.message("message2")
    def handler2(ctx: AgentContext):
        return []

    assert len(forge._registry._handlers) == 2
    assert forge._registry._handlers["message1"] == handler1
    assert forge._registry._handlers["message2"] == handler2


def test_message_decorator_logs_registration():
    forge = SpoeForge(name="test-agent")

    with patch.object(forge, "_logger") as mock_logger:

        @forge.message("test-message")
        def handler(ctx: AgentContext):
            return []

        mock_logger.debug.assert_called_once()


@pytest.mark.asyncio
async def test_notify_handler_processes_single_message():
    forge = SpoeForge(name="test-agent")

    @forge.message("test-message")
    def handler(ctx: AgentContext):
        return [SetVarAction(scope=ActionScope.SESSION, name="test", value=42)]

    messages = [("test-message", {"arg": "value"})]
    actions = await forge._notify_handler(messages)

    assert len(actions) == 1
    assert isinstance(actions[0], SetVarAction)
    assert actions[0].name == "test"
    assert actions[0].value == 42


@pytest.mark.asyncio
async def test_notify_handler_processes_multiple_messages():
    forge = SpoeForge(name="test-agent")

    @forge.message("message1")
    def handler1(ctx: AgentContext):
        return [SetVarAction(scope=ActionScope.SESSION, name="var1", value=1)]

    @forge.message("message2")
    def handler2(ctx: AgentContext):
        return [SetVarAction(scope=ActionScope.SESSION, name="var2", value=2)]

    messages = [("message1", {}), ("message2", {})]
    actions = await forge._notify_handler(messages)

    assert len(actions) == 2
    assert actions[0].name == "var1"
    assert actions[1].name == "var2"


@pytest.mark.asyncio
async def test_notify_handler_handles_empty_action_list():
    forge = SpoeForge(name="test-agent")

    @forge.message("test-message")
    def handler(ctx: AgentContext):
        return []

    messages = [("test-message", {})]
    actions = await forge._notify_handler(messages)

    assert actions == []


@pytest.mark.asyncio
async def test_notify_handler_handles_none_return():
    forge = SpoeForge(name="test-agent")

    @forge.message("test-message")
    def handler(ctx: AgentContext):
        return None

    messages = [("test-message", {})]
    actions = await forge._notify_handler(messages)

    assert actions == []


@pytest.mark.asyncio
async def test_notify_handler_ignores_invalid_return_type():
    forge = SpoeForge(name="test-agent")

    @forge.message("test-message")
    def handler(ctx: AgentContext):
        return "invalid"  # Should be list

    messages = [("test-message", {})]

    actions = await forge._notify_handler(messages)

    assert actions == []


@pytest.mark.asyncio
async def test_notify_handler_logs_actions():
    forge = SpoeForge(name="test-agent")

    @forge.message("test-message")
    def handler(ctx: AgentContext):
        return [SetVarAction(scope=ActionScope.SESSION, name="test", value=1)]

    messages = [("test-message", {})]

    with patch.object(forge, "_logger") as mock_logger:
        await forge._notify_handler(messages)

        mock_logger.info.assert_called_once()
        assert "handled 'test-message'" in mock_logger.info.call_args[0][0]
        assert "1 action(s)" in mock_logger.info.call_args[0][0]


@pytest.mark.asyncio
async def test_notify_handler_acks_empty_when_handler_raises():
    forge = SpoeForge(name="test-agent")

    @forge.message("test-message")
    def handler(ctx: AgentContext):
        raise ValueError("Handler error")

    messages = [("test-message", {})]

    actions = await forge._notify_handler(messages)

    assert actions == []


@pytest.mark.asyncio
async def test_notify_handler_isolates_failing_handler():
    forge = SpoeForge(name="test-agent")

    @forge.message("bad-message")
    def bad_handler(ctx: AgentContext):
        raise ValueError("boom")

    @forge.message("good-message")
    def good_handler(ctx: AgentContext):
        return [SetVarAction(scope=ActionScope.SESSION, name="ok", value=1)]

    actions = await forge._notify_handler([("bad-message", {}), ("good-message", {})])

    assert len(actions) == 1
    assert actions[0].name == "ok"


@pytest.mark.asyncio
async def test_notify_handler_with_unregistered_message():
    forge = SpoeForge(name="test-agent")

    messages = [("unregistered-message", {})]
    actions = await forge._notify_handler(messages)

    assert actions == []


@pytest.mark.asyncio
async def test_notify_handler_aggregates_multiple_actions_from_single_handler():
    forge = SpoeForge(name="test-agent")

    @forge.message("test-message")
    def handler(ctx: AgentContext):
        return [
            SetVarAction(scope=ActionScope.SESSION, name="var1", value=1),
            SetVarAction(scope=ActionScope.SESSION, name="var2", value=2),
            SetVarAction(scope=ActionScope.SESSION, name="var3", value=3),
        ]

    messages = [("test-message", {})]
    actions = await forge._notify_handler(messages)

    assert len(actions) == 3


@pytest.mark.asyncio
async def test_handler_creates_fresh_config():
    forge = SpoeForge(name="test-agent", max_frame_size=8192)

    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = MagicMock(spec=asyncio.StreamWriter)

    with patch("spoe_forge.spoe_forge.ForgeHandler") as MockForgeHandler:
        mock_handler_instance = AsyncMock()
        MockForgeHandler.return_value = mock_handler_instance

        await forge._handler(reader, writer)

        MockForgeHandler.assert_called_once()

        call_args = MockForgeHandler.call_args[0]
        config = call_args[1]

        assert config.max_frame_size == 8192


@pytest.mark.asyncio
async def test_handler_passes_notify_handler_callback():
    forge = SpoeForge(name="test-agent")

    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = MagicMock(spec=asyncio.StreamWriter)

    with patch("spoe_forge.spoe_forge.ForgeHandler") as MockForgeHandler:
        mock_handler_instance = AsyncMock()
        MockForgeHandler.return_value = mock_handler_instance

        await forge._handler(reader, writer)

        call_args = MockForgeHandler.call_args[0]
        notify_callback = call_args[0]

        assert notify_callback == forge._notify_handler


@pytest.mark.asyncio
async def test_handler_calls_core_handler():
    forge = SpoeForge(name="test-agent")

    reader = AsyncMock(spec=asyncio.StreamReader)
    writer = MagicMock(spec=asyncio.StreamWriter)

    with patch("spoe_forge.spoe_forge.ForgeHandler") as MockForgeHandler:
        mock_handler_instance = AsyncMock()
        MockForgeHandler.return_value = mock_handler_instance

        await forge._handler(reader, writer)

        mock_handler_instance.core_handler.assert_called_once()


@pytest.mark.asyncio
async def test_serve_creates_asyncio_server():
    forge = SpoeForge(name="test-agent")

    mock_server = AsyncMock()
    mock_server.__aenter__ = AsyncMock(return_value=mock_server)
    mock_server.__aexit__ = AsyncMock()

    with patch("spoe_forge.spoe_forge.asyncio.start_server") as mock_start_server:
        mock_start_server.return_value = mock_server

        task = asyncio.create_task(forge.serve("0.0.0.0", 12345))

        await asyncio.sleep(0.01)

        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_start_server.assert_called_once_with(
            forge._handler, "0.0.0.0", 12345, ssl=None
        )


@pytest.mark.asyncio
async def test_serve_logs_listening_address():
    forge = SpoeForge(name="test-agent")

    mock_server = AsyncMock()
    mock_server.__aenter__ = AsyncMock(return_value=mock_server)
    mock_server.__aexit__ = AsyncMock()

    with (
        patch("spoe_forge.spoe_forge.asyncio.start_server") as mock_start_server,
        patch.object(forge, "_logger") as mock_logger,
    ):
        mock_start_server.return_value = mock_server

        task = asyncio.create_task(forge.serve("localhost", 9000))
        await asyncio.sleep(0.01)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_logger.info.assert_called_once()
        assert "localhost:9000" in mock_logger.info.call_args[0][0]


@pytest.mark.asyncio
async def test_serve_passes_ssl_context():
    forge = SpoeForge(name="test-agent")

    mock_server = AsyncMock()
    mock_server.__aenter__ = AsyncMock(return_value=mock_server)
    mock_server.__aexit__ = AsyncMock()
    ssl_context = MagicMock()

    with patch("spoe_forge.spoe_forge.asyncio.start_server") as mock_start_server:
        mock_start_server.return_value = mock_server

        task = asyncio.create_task(forge.serve("0.0.0.0", 12345, ssl=ssl_context))
        await asyncio.sleep(0.01)
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        mock_start_server.assert_called_once_with(
            forge._handler, "0.0.0.0", 12345, ssl=ssl_context
        )


def test_run_exits_cleanly_on_keyboard_interrupt():
    forge = SpoeForge(name="test-agent")

    with (
        patch("spoe_forge.spoe_forge.asyncio.run") as mock_asyncio_run,
        patch.object(forge, "_logger") as mock_logger,
    ):

        def mock_run(coro):
            coro.close()
            raise KeyboardInterrupt()

        mock_asyncio_run.side_effect = mock_run

        forge.run("0.0.0.0", 12345)

        mock_logger.info.assert_called_once()
        assert "shutting down" in mock_logger.info.call_args[0][0]


def test_run_calls_asyncio_run():
    forge = SpoeForge(name="test-agent")

    with patch("spoe_forge.spoe_forge.asyncio.run") as mock_asyncio_run:

        def mock_run(coro):
            coro.close()
            return None

        mock_asyncio_run.side_effect = mock_run

        forge.run("0.0.0.0", 12345)

        mock_asyncio_run.assert_called_once()


@pytest.mark.asyncio
async def test_full_message_flow():
    forge = SpoeForge(name="test-agent")

    # Track handler invocation
    handler_called = False
    received_args = None

    @forge.message("check-ip")
    def check_ip(ctx: AgentContext):
        nonlocal handler_called, received_args
        handler_called = True
        received_args = ctx.get_args()
        return [
            SetVarAction(scope=ActionScope.SESSION, name="ip_valid", value=True),
            SetVarAction(scope=ActionScope.SESSION, name="score", value=95),
        ]

    messages = [("check-ip", {"src": "192.168.1.1", "dst": "10.0.0.1"})]

    actions = await forge._notify_handler(messages)

    assert handler_called is True
    assert received_args == {"src": "192.168.1.1", "dst": "10.0.0.1"}
    assert len(actions) == 2
    assert actions[0].name == "ip_valid"
    assert actions[1].name == "score"


@pytest.mark.asyncio
async def test_multiple_handlers_integration():
    forge = SpoeForge(name="test-agent")

    @forge.message("check-auth")
    def check_auth(ctx: AgentContext):
        return [
            SetVarAction(scope=ActionScope.SESSION, name="authenticated", value=True)
        ]

    @forge.message("check-rate-limit")
    def check_rate(ctx: AgentContext):
        return [SetVarAction(scope=ActionScope.SESSION, name="rate_ok", value=True)]

    messages = [
        ("check-auth", {"token": "abc123"}),
        ("check-rate-limit", {"ip": "1.2.3.4"}),
    ]

    actions = await forge._notify_handler(messages)

    assert len(actions) == 2
    assert any(a.name == "authenticated" for a in actions)
    assert any(a.name == "rate_ok" for a in actions)


@pytest.mark.asyncio
async def test_handler_with_real_context_usage():
    forge = SpoeForge(name="test-agent")

    @forge.message("process-request")
    def process_request(ctx: AgentContext):
        method = ctx.get_arg("method", default="GET")
        path = ctx.get_arg("path")
        has_auth = ctx.has_arg("authorization")

        return [
            SetVarAction(scope=ActionScope.REQUEST, name="method", value=method),
            SetVarAction(scope=ActionScope.REQUEST, name="path", value=path or "/"),
            SetVarAction(scope=ActionScope.REQUEST, name="has_auth", value=has_auth),
        ]

    messages = [("process-request", {"method": "POST", "path": "/api/users"})]

    actions = await forge._notify_handler(messages)

    assert len(actions) == 3
    assert actions[0].value == "POST"
    assert actions[1].value == "/api/users"
    assert actions[2].value is False
