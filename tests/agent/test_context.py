import ipaddress

from spoe_forge.agent.context import AgentContext


def test_context_initialization():
    args = {"ip": "192.168.1.1", "port": 8080}
    ctx = AgentContext(message="check-request", args=args)

    assert ctx._message == "check-request"
    assert ctx._args == args


def test_context_initialization_empty_args():
    ctx = AgentContext(message="ping", args={})

    assert ctx._message == "ping"
    assert ctx._args == {}


def test_get_arg_returns_value():
    ctx = AgentContext(message="test", args={"name": "value", "count": 42})

    assert ctx.get_arg("name") == "value"
    assert ctx.get_arg("count") == 42


def test_get_arg_returns_none_when_missing():
    ctx = AgentContext(message="test", args={"name": "value"})

    assert ctx.get_arg("missing") is None


def test_get_arg_returns_default_when_missing():
    ctx = AgentContext(message="test", args={"name": "value"})

    assert ctx.get_arg("missing", default="default_value") == "default_value"
    assert ctx.get_arg("missing", default=0) == 0
    assert ctx.get_arg("missing", default="Hello SPOE") == "Hello SPOE"


def test_get_arg_returns_none_explicitly():
    ctx = AgentContext(message="test", args={"nullable": None})

    assert ctx.get_arg("nullable") is None


def test_get_arg_with_various_types():
    args = {
        "string": "test",
        "int": 42,
        "bool": True,
        "ip": ipaddress.IPv4Address("192.168.1.1"),
        "binary": b"\x00\x01\x02",
        "null": None,
    }
    ctx = AgentContext(message="test", args=args)

    assert ctx.get_arg("string") == "test"
    assert ctx.get_arg("int") == 42
    assert ctx.get_arg("bool") is True
    assert ctx.get_arg("ip") == ipaddress.IPv4Address("192.168.1.1")
    assert ctx.get_arg("binary") == b"\x00\x01\x02"
    assert ctx.get_arg("null") is None


def test_get_args_returns_all_arguments():
    """Test get_args returns all message arguments."""
    args = {"ip": "192.168.1.1", "port": 8080, "method": "GET"}
    ctx = AgentContext(message="test", args=args)

    result = ctx.get_args()

    assert result == args


def test_get_args_returns_empty_dict():
    ctx = AgentContext(message="test", args={})

    result = ctx.get_args()

    assert result == {}


def test_get_args_returns_mutable_reference():
    args = {"key": "value"}
    ctx = AgentContext(message="test", args=args)

    result = ctx.get_args()
    result["new_key"] = "new_value"

    assert ctx.get_arg("new_key") == "new_value"


def test_has_arg_returns_true_when_exists():
    ctx = AgentContext(message="test", args={"name": "value", "count": 42})

    assert ctx.has_arg("name") is True
    assert ctx.has_arg("count") is True


def test_has_arg_returns_false_when_missing():
    ctx = AgentContext(message="test", args={"name": "value"})

    assert ctx.has_arg("missing") is False
    assert ctx.has_arg("other") is False


def test_has_arg_returns_true_for_none_value():
    ctx = AgentContext(message="test", args={"nullable": None})

    assert ctx.has_arg("nullable") is True


def test_has_arg_with_empty_string_key():
    ctx = AgentContext(message="test", args={"": "empty_key_value"})

    assert ctx.has_arg("") is True


def test_context_with_many_arguments():
    args = {f"arg{i}": i for i in range(100)}
    ctx = AgentContext(message="test", args=args)

    assert len(ctx.get_args()) == 100
    assert ctx.get_arg("arg50") == 50
    assert ctx.has_arg("arg99") is True
    assert ctx.has_arg("arg100") is False


def test_context_argument_names_case_sensitive():
    ctx = AgentContext(message="test", args={"Name": "upper", "name": "lower"})

    assert ctx.get_arg("Name") == "upper"
    assert ctx.get_arg("name") == "lower"
    assert ctx.has_arg("NAME") is False


def test_context_with_special_characters_in_keys():
    args = {
        "key-with-dash": "value1",
        "key.with.dot": "value2",
        "key_with_underscore": "value3",
    }
    ctx = AgentContext(message="test", args=args)

    assert ctx.get_arg("key-with-dash") == "value1"
    assert ctx.get_arg("key.with.dot") == "value2"
    assert ctx.get_arg("key_with_underscore") == "value3"


def test_context_preserves_argument_order():
    args = {"first": 1, "second": 2, "third": 3}
    ctx = AgentContext(message="test", args=args)

    result_keys = list(ctx.get_args().keys())
    assert result_keys == ["first", "second", "third"]
