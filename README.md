# SPOE Forge

A pure Python framework for building SPOE (Stream Processing Offload Engine) agents that communicate
with HAProxy using the SPOA protocol.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Coverage Status](https://coveralls.io/repos/github/mwodonnell/spoe-forge/badge.svg?branch=unit-tests)](https://coveralls.io/github/mwodonnell/spoe-forge?branch=unit-tests)

## Overview

SPOE Forge provides a clean, decorator-based API for creating agents that process HAProxy messages and return
actions. Built with async/await throughout, it's designed for high-performance production environments. *Or at least as
performant as python will allow.*

### Status

Early alpha version, feature-complete according to most recent SPOE documentation and running in
production. Still going through initial testing/deployment to PyPi.

Future development planned as use cases/limitations arise. Intended to be a long-lived python project.

### Why SPOE Forge?

Originally created to power a Google OAuth2 authentication backend for HAProxy, it became clear the project
could be converted to an abstracted framework. I noticed during the development of this project that there
was a lack of well-maintained, easily understood implementations of the SPOA protocol in python.

### Key Features

- **Simple decorator-based API** - Register message handlers with `@agent.message()`
- **Full SPOP protocol support** - Complete implementation of the SPOA protocol
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

For a live example - there is a [Dockerfile](Dockerfile) and [docker-compose.yml](docker-compose.yml) provided to stand
up a test server. I owe you more docs on that.

### HAProxy Configuration

SPOE Forge works with HAProxy's SPOE configuration. For details on configuring HAProxy to communicate with your
agent, see the [official HAProxy SPOE documentation](https://www.haproxy.org/download/3.3/doc/SPOE.txt).

## Roadmap

Future enhancements under consideration with no timeline guaranteed:

- Middleware system for cross-cutting concerns
- More robust tools for local testing
- Much more extended documentation and examples

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Any and all contributions welcome.

## Support

For issues and questions, please file an issue on the GitHub repository once it's made public.

## Acknowledgments

Built to solve real-world production needs for HAProxy SPOA agents. Special thanks to the HAProxy team for
excellent documentation of the SPOE protocol.

Extra shoutout to [Christopher Faulet](https://github.com/capflam) for responding to some questions about a
few hiccups along the way.
