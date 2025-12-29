import logging

from spoe_forge import SpoeForge, AgentContext, SetVarAction, ActionScope

logging.basicConfig(
    format="%(levelname)s | %(asctime)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
    level=logging.INFO,
)

agent = SpoeForge(name="sample-agent")
logger = logging.getLogger("sample-spoe-server")


@agent.message("test-ping")
def ping(ctx: AgentContext):
    return [
        SetVarAction(
            scope=ActionScope.REQUEST, name="spoe_arg", value="Hello from SPOE Forge"
        )
    ]


agent.run(host="0.0.0.0", port=8500)
