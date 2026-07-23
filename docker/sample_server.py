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
    ua = ctx.get_arg("ua")
    logger.info(f"received ua arg: {ua!r}")
    return [
        SetVarAction(scope=ActionScope.REQUEST, name="spoe_arg", value=f"ua was: {ua}")
    ]


agent.run(host="0.0.0.0", port=8500)
