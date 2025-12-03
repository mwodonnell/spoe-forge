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
logger = logging.getLogger(__name__)


@agent.message("test-ping")
def ping(ctx: AgentContext):
    return [SetVarAction(scope=ActionScope.REQUEST, name="spoe_arg", value=2289)]


@agent.message("test-pong")
def pong(ctx: AgentContext):
    all_args = ctx.get_args()
    logger.info(f"all_args: {all_args}")


agent.run(host="0.0.0.0", port=8500)
