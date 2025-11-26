# SPOE Forge

A production-ready Python framework for building SPOE (Stream Processing Offload Engine) agents that communicate
with HAProxy using the SPOA protocol.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)

## Overview

SPOE Forge provides a clean, decorator-based API for creating agents that process HAProxy messages and return
actions. Built with async/await throughout, it's designed for high-performance production environments. *Or at least as
performant as python will allow.*

### Status

Early version, feature-complete according to most recent SPOE documentation and running in production. Will be
published as a PyPI package in the future.

Future development planned as use cases/limitations arise.

Severely lacking unit tests right now - these will be added prior to first major PyPi release. Testing has been
done on personal HAProxy deployment.

### Why SPOE Forge?

This framework was created to power a production Google OAuth2 authentication system for HAProxy,
where it currently handles real-world authentication flows on AWS ECS. The lack of well-maintained
Python implementations of the SPOA protocol led to the development of this framework, which is now
being prepared for open-source release to help the community build SPOA agents more easily.

While python is not the goto for network level projects - it's enough in certain applications.
For a more venerable package - I would defer to the existing [GO Implementation](https://github.com/negasus/haproxy-spoe-go).


### Key Features

- **Simple decorator-based API** - Register message handlers with `@agent.message()`
- **Full SPOP protocol support** - Complete implementation of the SPOA protocol
- **Production-tested** - Currently running in production environments
- **Async/await throughout** - Non-blocking I/O for high performance
- **Type-safe** - Full type hints and IDE support
- **Flexible action system** - Set/unset variables across different HAProxy scopes
- **Health check support** - Built-in HAProxy health check handling

## Quick Start

### Basic Example

```python
from spoe_forge import (
    SpoeForge,
    AgentContext,
    SetVarAction,
    ActionScope
)

# Create an agent
agent = SpoeForge(name="my-agent", debug=False)

# Register a message handler
@agent.message("check-request")
def handle_request(ctx: AgentContext) -> list[SetVarAction]:
    """Process incoming request and set HAProxy variables"""

    # Get message arguments from HAProxy
    client_ip = ctx.get_arg("client_ip")
    request_path = ctx.get_arg("path")

    # Your business logic here
    is_allowed = check_access(client_ip, request_path)

    # Return actions to set HAProxy variables
    return [
        SetVarAction(
            scope=ActionScope.TRANSACTION,
            name="access_allowed",
            value=is_allowed
        )
    ]

# Start the server
if __name__ == "__main__":
    agent.run(host="0.0.0.0", port=12345)
```

### HAProxy Configuration

SPOE Forge works with HAProxy's SPOE configuration. For details on configuring HAProxy to communicate with your
agent, see the [official HAProxy SPOE documentation](https://www.haproxy.org/download/3.3/doc/SPOE.txt).

## Supported Data Types

SPOE Forge supports all SPOA data types:

- `int` - Signed integers
- `bool` - Boolean values
- `str` - ASCII strings
- `bytes` - Binary data
- `ipaddress.IPv4Address` - IPv4 addresses
- `ipaddress.IPv6Address` - IPv6 addresses
- `None` - Null values

## Action Scopes

Set variables at different HAProxy scopes:

- `ActionScope.PROCESS` - Process-wide variables
- `ActionScope.SESSION` - Client session lifetime
- `ActionScope.TRANSACTION` - Request/response transaction
- `ActionScope.REQUEST` - Current request only
- `ActionScope.RESPONSE` - Current response only

## Protocol Reference

SPOE Forge implements the SPOA protocol as specified in the [HAProxy SPOE documentation](https://raw.githubusercontent.com/haproxy/haproxy/refs/tags/v3.2.0/doc/SPOE.txt).

## Roadmap

Future enhancements under consideration:

- Publish to PyPI for easy installation
- Native async handler support
- Middleware system for cross-cutting concerns
- Message validation framework
- Comprehensive test suite
- CLI tools for local testing
- Extended documentation and examples

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

This project is in early stages and will be accepting contributions once published as a package. Stay tuned!

## Support

For issues and questions, please file an issue on the GitHub repository once it's made public.

## Acknowledgments

Built to solve real-world production needs for HAProxy SPOA agents. Special thanks to the HAProxy team for
excellent documentation of the SPOE protocol.

Extra shoutout to [Christopher Faulet](https://github.com/capflam) for responding to some questions about a
few hiccups along the way.
