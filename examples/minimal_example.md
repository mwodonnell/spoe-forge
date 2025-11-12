# Minimal Example - Hello World

This is the simplest possible SPOE Forge agent to help you get started.

## Overview

This example creates a basic agent that:
- Accepts a "hello" message from HAProxy
- Extracts a name argument
- Returns a greeting message as a HAProxy variable

## Code

```python
from spoe_forge.agent import Agent, AgentContext, SetVarAction, ActionScope
from spoe_forge.server import SpoeForge

# Create the agent
agent = Agent(name="hello-world")

# Register a message handler
@agent.message("hello")
def say_hello(ctx: AgentContext) -> list[SetVarAction]:
    """
    Handles 'hello' messages from HAProxy.

    Expected arguments:
    - name: The name to greet (string)
    """
    # Get the name argument, default to "World" if not provided
    name = ctx.get_arg("name", "World")

    # Create a greeting
    greeting = f"Hello, {name}!"

    # Return action to set a HAProxy variable
    return [
        SetVarAction(
            scope=ActionScope.TRANSACTION,
            name="greeting",
            value=greeting
        )
    ]

# Start the server
if __name__ == "__main__":
    # Create server with default settings
    forge = SpoeForge(agent, max_frame_size=16384)

    # Run on localhost:12345
    forge.run(host="0.0.0.0", port=12345)
```

## Running the Agent

```bash
# Save the code above as hello_agent.py
python hello_agent.py
```

The agent will start listening on port 12345.

## What's Happening

1. **Agent Creation**: `Agent(name="hello-world")` creates a new agent instance
2. **Handler Registration**: The `@agent.message("hello")` decorator registers a handler for messages named "hello"
3. **Context Access**: `ctx.get_arg("name", "World")` gets the "name" argument from HAProxy, defaulting to "World"
4. **Action Creation**: `SetVarAction(...)` creates an action that tells HAProxy to set a variable
5. **Server Start**: `SpoeForge(agent).run()` starts the TCP server

## HAProxy Configuration Hint

Your HAProxy SPOE configuration would need to:
- Connect to the agent on port 12345
- Send "hello" messages with a "name" argument
- Read the "greeting" transaction variable

Example SPOE message configuration:
```
[hello]
args=name=req.hdr(X-Name)
```

## Understanding the Response

When HAProxy sends a "hello" message:
- Input: `{"name": "Alice"}`
- Output: HAProxy variable `txn.greeting = "Hello, Alice!"`

The `TRANSACTION` scope means this variable exists only for the current request/response.

## Next Steps

- See [Practical Example](practical_example.md) for real-world use cases
- Try different argument types (integers, IPs, booleans)
- Experiment with different ActionScope values
- Add multiple message handlers to one agent
