# SPOE Forge

A pure Python framework for building SPOE (Stream Processing Offload Engine) agents
that communicate with HAProxy using the SPOA protocol.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Coverage Status](https://coveralls.io/repos/github/mwodonnell/spoe-forge/badge.svg?branch=unit-tests)](https://coveralls.io/github/mwodonnell/spoe-forge?branch=unit-tests)

## Overview

SPOE Forge provides a clean, decorator-based API for creating agents that process HAProxy messages
and return actions. Built with async/await throughout, it's designed for high-performance production
environments. *Or at least as performant as python will allow.*

### Why SPOE Forge?

Originally created to power a Google OAuth2 authentication backend for HAProxy, it became clear the
project could be converted to an abstracted framework. I noticed during the development of this
project that there was a lack of well-maintained, easily understood implementations of the SPOA
protocol in python.

### Key Features

-   **Simple decorator-based API** - Register message handlers with `@agent.message()`
-   **Full SPOP protocol support** - Complete implementation of the SPOA protocol
-   **Health check support** - Built-in HAProxy health check handling

## Installation

Install from PyPI:

```bash
pip install spoe-forge
```

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

SPOE Forge works with HAProxy's SPOE configuration. For details on configuring HAProxy to
communicate with your agent, see the
[official HAProxy SPOE documentation](https://www.haproxy.org/download/3.3/doc/SPOE.txt).

## Local Development

### Running with Docker

A complete local development environment is provided using Docker Compose, including a sample
SPOE agent, HAProxy, and a test backend service.

**Quick start:**

```bash
cd docker
docker compose up --build
```

This starts three services:

-   **SPOA Agent** (`spoa`) - Sample SPOE Forge agent running on port 8500
-   **Whoami** (`whoami`) - Simple backend service for testing
-   **HAProxy** (`haproxy`) - Configured to communicate with the WhoAmI example BE Service, the SPOA agent, and is listening on port 8080

**Test the setup:**

```bash
# Open logs
docker compose logs

# Visit the dev url in your browser
http://localhost:8080
```

Check both the docker logs and the `X-Test-Arg` header displayed on the WhoAmI page.

Make any updates to the HAProxy configs or the sample_server.py files in `./docker/` to
support your testing.

### Health Checks

SPOE Forge includes a built-in CLI healthcheck utility for monitoring agent health in
containerized environments.

**Basic usage:**

```bash
# Basic usage
spoe-forge healthcheck --host 127.0.0.1 --port 8500

# Use default host and port
spoe-forge healthcheck


# Quiet mode, only exit codes
spoe-forge healthcheck --quiet

# Help info
spoe-forge --help
spoe-forge healthcheck --help
```

**Docker Integration:**

The provided [docker-compose.yml](./docker/docker-compose.yml) includes a pre-configured
healthcheck for the sample SPOE agent as a reference:

```yaml
healthcheck:
  test: ["CMD", "uv", "run", "spoe-forge", "healthcheck", "--host", "127.0.0.1", "--port", "8500", "--quiet"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 10s
```

View healthcheck status:

```bash
docker compose ps     # Shows health status
docker inspect spoa   # Detailed healthcheck info
```

**Exit codes:**

-   `0`: Health check passed
-   `1`: Health check failed
-   `2`: Invalid usage

## Roadmap

Future enhancements under consideration with no timeline guaranteed:

-   Middleware support
-   Much more extended documentation and examples

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Any and all contributions welcome.

## Support

For issues and questions, please [file an issue on GitHub](https://github.com/mwodonnell/spoe-forge/issues).

## Acknowledgments

Built to solve real-world production needs for HAProxy SPOA agents. Special thanks to the
HAProxy team for excellent documentation of the SPOE protocol.

Extra shoutout to [Christopher Faulet](https://github.com/capflam) for responding to some
questions about a few hiccups along the way.
