"""pyxis: declarative chain-of-thought agent framework.

code as prompt + schema as workflow.
"""

from .client import (
    Client,
    FakeCall,
    FakeClient,
    InstructorClient,
    get_default_client,
    set_default_client,
)
from .step import Step, step

__version__ = "0.1.0"

__all__ = [
    "Client",
    "FakeCall",
    "FakeClient",
    "InstructorClient",
    "Step",
    "get_default_client",
    "set_default_client",
    "step",
]
