# Practical Examples - Real-World Use Cases

This guide shows practical implementations of SPOE Forge agents for common use cases.

## Table of Contents

1. [IP Reputation Checking](#ip-reputation-checking)
2. [Rate Limiting](#rate-limiting)
3. [Request Validation](#request-validation)
4. [Multiple Message Handlers](#multiple-message-handlers)

---

## IP Reputation Checking

Block or flag requests from known bad IP addresses.

```python
from spoe_forge.agent import Agent, AgentContext, SetVarAction, ActionScope
from spoe_forge.server import SpoeForge
import ipaddress

# Simulated IP reputation database
BLOCKED_IPS = {
    "192.168.1.100",
    "10.0.0.50",
}

SUSPICIOUS_IPS = {
    "192.168.1.200",
}

agent = Agent(name="ip-reputation")

@agent.message("check-ip")
def check_ip_reputation(ctx: AgentContext) -> list[SetVarAction]:
    """
    Check IP address reputation and set security flags.

    Expected arguments:
    - client_ip: Client IP address (IPv4/IPv6)
    """
    client_ip = ctx.get_arg("client_ip")

    # Convert to string for lookup
    ip_str = str(client_ip)

    actions = []

    # Check if IP is blocked
    if ip_str in BLOCKED_IPS:
        actions.extend([
            SetVarAction(
                scope=ActionScope.SESSION,
                name="ip_blocked",
                value=True
            ),
            SetVarAction(
                scope=ActionScope.SESSION,
                name="block_reason",
                value="Known malicious IP"
            )
        ])
    # Check if IP is suspicious
    elif ip_str in SUSPICIOUS_IPS:
        actions.extend([
            SetVarAction(
                scope=ActionScope.SESSION,
                name="ip_suspicious",
                value=True
            ),
            SetVarAction(
                scope=ActionScope.SESSION,
                name="require_captcha",
                value=True
            )
        ])
    # IP is clean
    else:
        actions.append(
            SetVarAction(
                scope=ActionScope.SESSION,
                name="ip_trusted",
                value=True
            )
        )

    return actions

if __name__ == "__main__":
    forge = SpoeForge(agent, max_frame_size=16384)
    forge.run(host="0.0.0.0", port=12345)
```

### Usage Notes

- Uses `SESSION` scope so reputation is cached for the entire client session
- HAProxy can use `sess.ip_blocked` to reject requests
- `sess.require_captcha` can trigger additional validation flows

---

## Rate Limiting

Track and limit request rates per client.

```python
from spoe_forge.agent import Agent, AgentContext, SetVarAction, ActionScope
from spoe_forge.server import SpoeForge
from collections import defaultdict
from datetime import datetime, timedelta

# Simple in-memory rate limiter
class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self.requests = defaultdict(list)

    def is_allowed(self, client_id: str) -> tuple[bool, int]:
        """
        Check if request is allowed.

        Returns:
            (allowed, requests_remaining)
        """
        now = datetime.now()
        cutoff = now - self.window

        # Clean old requests
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff
        ]

        # Check limit
        current_count = len(self.requests[client_id])

        if current_count >= self.max_requests:
            return False, 0

        # Record this request
        self.requests[client_id].append(now)
        return True, self.max_requests - current_count - 1

# 100 requests per minute per IP
limiter = RateLimiter(max_requests=100, window_seconds=60)

agent = Agent(name="rate-limiter")

@agent.message("check-rate-limit")
def check_rate_limit(ctx: AgentContext) -> list[SetVarAction]:
    """
    Check if client has exceeded rate limit.

    Expected arguments:
    - client_ip: Client IP address
    """
    client_ip = str(ctx.get_arg("client_ip"))

    allowed, remaining = limiter.is_allowed(client_ip)

    return [
        SetVarAction(
            scope=ActionScope.TRANSACTION,
            name="rate_limit_allowed",
            value=allowed
        ),
        SetVarAction(
            scope=ActionScope.TRANSACTION,
            name="rate_limit_remaining",
            value=remaining
        )
    ]

if __name__ == "__main__":
    forge = SpoeForge(agent, max_frame_size=16384)
    forge.run(host="0.0.0.0", port=12345)
```

### Usage Notes

- Uses `TRANSACTION` scope for per-request decisions
- HAProxy can use `txn.rate_limit_allowed` to accept/reject requests
- `txn.rate_limit_remaining` can be added to response headers

---

## Request Validation

Validate request data and enforce security policies.

```python
from spoe_forge.agent import Agent, AgentContext, SetVarAction, UnsetVarAction, ActionScope
from spoe_forge.server import SpoeForge
import re

agent = Agent(name="request-validator")

# Regex patterns for validation
VALID_PATH_PATTERN = re.compile(r'^/[a-zA-Z0-9/_-]*$')
SQL_INJECTION_PATTERN = re.compile(r'(union|select|insert|update|delete|drop|create)', re.IGNORECASE)

@agent.message("validate-request")
def validate_request(ctx: AgentContext) -> list[SetVarAction | UnsetVarAction]:
    """
    Validate incoming request for security issues.

    Expected arguments:
    - request_path: HTTP request path
    - query_string: HTTP query string (optional)
    - user_agent: HTTP User-Agent header
    """
    request_path = ctx.get_arg("request_path")
    query_string = ctx.get_arg("query_string", "")
    user_agent = ctx.get_arg("user_agent", "")

    actions = []
    validation_errors = []

    # Check path format
    if not VALID_PATH_PATTERN.match(request_path):
        validation_errors.append("Invalid path format")

    # Check for SQL injection attempts
    if SQL_INJECTION_PATTERN.search(query_string):
        validation_errors.append("SQL injection attempt detected")

    # Check for missing or suspicious User-Agent
    if not user_agent or user_agent == "":
        validation_errors.append("Missing User-Agent")
    elif len(user_agent) > 500:
        validation_errors.append("Suspicious User-Agent length")

    # Set validation results
    if validation_errors:
        actions.extend([
            SetVarAction(
                scope=ActionScope.TRANSACTION,
                name="request_valid",
                value=False
            ),
            SetVarAction(
                scope=ActionScope.TRANSACTION,
                name="validation_error",
                value="; ".join(validation_errors)
            )
        ])
    else:
        actions.extend([
            SetVarAction(
                scope=ActionScope.TRANSACTION,
                name="request_valid",
                value=True
            ),
            # Clear any previous error
            UnsetVarAction(
                scope=ActionScope.TRANSACTION,
                name="validation_error"
            )
        ])

    return actions

if __name__ == "__main__":
    forge = SpoeForge(agent, max_frame_size=16384)
    forge.run(host="0.0.0.0", port=12345)
```

### Usage Notes

- Demonstrates both `SetVarAction` and `UnsetVarAction`
- Multiple validation checks in a single handler
- HAProxy can use `txn.request_valid` to allow/deny requests
- `txn.validation_error` provides detailed error messages for logging

---

## Multiple Message Handlers

Combine multiple handlers in a single agent for complex workflows.

```python
from spoe_forge.agent import Agent, AgentContext, SetVarAction, ActionScope
from spoe_forge.server import SpoeForge

agent = Agent(name="multi-handler-agent")

@agent.message("check-auth")
def check_authentication(ctx: AgentContext) -> list[SetVarAction]:
    """
    Validate authentication token.

    Expected arguments:
    - auth_token: Bearer token from Authorization header
    """
    auth_token = ctx.get_arg("auth_token", None)

    if not auth_token:
        return [
            SetVarAction(
                scope=ActionScope.TRANSACTION,
                name="authenticated",
                value=False
            )
        ]

    # Validate token (simplified)
    user_id = validate_token(auth_token)

    if user_id:
        return [
            SetVarAction(
                scope=ActionScope.SESSION,
                name="authenticated",
                value=True
            ),
            SetVarAction(
                scope=ActionScope.SESSION,
                name="user_id",
                value=user_id
            )
        ]
    else:
        return [
            SetVarAction(
                scope=ActionScope.TRANSACTION,
                name="authenticated",
                value=False
            )
        ]

@agent.message("check-permissions")
def check_permissions(ctx: AgentContext) -> list[SetVarAction]:
    """
    Verify user has required permissions.

    Expected arguments:
    - user_id: Authenticated user ID
    - required_permission: Permission needed for this resource
    """
    user_id = ctx.get_arg("user_id")
    required_permission = ctx.get_arg("required_permission")

    has_permission = user_has_permission(user_id, required_permission)

    return [
        SetVarAction(
            scope=ActionScope.TRANSACTION,
            name="authorized",
            value=has_permission
        )
    ]

@agent.message("log-access")
def log_access(ctx: AgentContext) -> list[SetVarAction]:
    """
    Log access attempt for auditing.

    Expected arguments:
    - user_id: User ID
    - resource_path: Requested resource
    - client_ip: Client IP address
    """
    user_id = ctx.get_arg("user_id", "anonymous")
    resource_path = ctx.get_arg("resource_path")
    client_ip = ctx.get_arg("client_ip")

    # Log to your audit system
    log_audit_event(user_id, resource_path, str(client_ip))

    # No variables to set, just logging
    return []

# Helper functions (implement based on your needs)
def validate_token(token: str) -> str | None:
    """Validate JWT/session token and return user_id"""
    # Implementation here
    return "user123" if token == "valid-token" else None

def user_has_permission(user_id: str, permission: str) -> bool:
    """Check if user has required permission"""
    # Implementation here
    return True

def log_audit_event(user_id: str, resource: str, ip: str):
    """Log access to audit system"""
    print(f"AUDIT: user={user_id} resource={resource} ip={ip}")

if __name__ == "__main__":
    forge = SpoeForge(agent, max_frame_size=16384)
    forge.run(host="0.0.0.0", port=12345)
```

### Usage Notes

- Single agent handles multiple message types
- Messages can be chained: check-auth → check-permissions → log-access
- Mix of `SESSION` (auth state) and `TRANSACTION` (per-request) scopes
- Handlers can return empty list if only performing side effects (logging)

---

## Production Considerations

### Error Handling

```python
from spoe_forge.agent import Agent, AgentContext, SetVarAction, ActionScope
from spoe_forge.agent.exceptions import SpoeAgentError

@agent.message("risky-operation")
def risky_handler(ctx: AgentContext) -> list[SetVarAction]:
    try:
        # Your business logic
        result = perform_external_api_call()
        return [SetVarAction(...)]
    except Exception as e:
        # Log the error
        logger.error(f"Handler failed: {e}")

        # Raise SpoeAgentError to disconnect gracefully
        raise SpoeAgentError(f"Operation failed: {e}")
```

### Logging

```python
from spoe_forge.log import logger

@agent.message("debug-handler")
def debug_handler(ctx: AgentContext) -> list[SetVarAction]:
    # Log incoming arguments
    logger.info(f"Received message with args: {ctx.get_args()}")

    # Your logic here
    result = process_data()

    # Log result
    logger.debug(f"Processing result: {result}")

    return [...]
```

### Performance

- Use `SESSION` scope for expensive operations that can be cached per-client
- Keep handlers fast - HAProxy connections are synchronous
- Consider async external API calls for I/O-bound operations
- Monitor handler execution time in production

---

## Next Steps

- Deploy your agent with Docker (see main repository for Dockerfile)
- Configure HAProxy SPOE to connect to your agent
- Monitor logs and metrics in production
- Explore the OAuth agent in the repository for a complete production example
