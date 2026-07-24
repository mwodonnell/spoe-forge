import asyncio
import logging

from spoe_forge import SpoeForge, AgentContext, SetVarAction, ActionScope

logging.basicConfig(
    format="%(levelname)s | %(asctime)s | %(name)s | %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
    level=logging.DEBUG,
)

agent = SpoeForge(name="sample-agent", debug=True)
logger = logging.getLogger("sample-spoe-server")


@agent.message("test-ping")
async def ping(ctx: AgentContext):
    ua = ctx.get_arg("ua")
    logger.info(f"handler start: ua={ua!r}")

    # A user-agent containing "slow" simulates a slow backend call, letting the
    # docker harness demonstrate pipelined (out-of-order) ACKs. Kept under
    # HAProxy's 1s processing timeout.
    if ua and "slow" in ua:
        await asyncio.sleep(0.5)

    logger.info(f"handler done: ua={ua!r}")
    return [
        SetVarAction(scope=ActionScope.REQUEST, name="spoe_arg", value=f"ua was: {ua}")
    ]


agent.run(host="0.0.0.0", port=8500)
