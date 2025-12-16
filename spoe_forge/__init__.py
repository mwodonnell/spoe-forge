"""SPOE Forge - A Python framework for building HAProxy SPOA agents."""

from spoe_forge.spoe_forge import SpoeForge
from spoe_forge.spop.spop_types import SetVarAction, UnsetVarAction, Action
from spoe_forge.spop.constants import ActionScope
from spoe_forge.agent.context import AgentContext

__version__ = "0.1.0a2"

__all__ = [
    "__version__",
    "SpoeForge",
    "AgentContext",
    "Action",
    "ActionScope",
    "SetVarAction",
    "UnsetVarAction",
]
