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
from .flow import Flow, flow
from .step import Step, step
from .tool import Tool
from .trace import Trace, TraceRecord, trace

__version__ = "0.1.0"

__all__ = [
    "Client",
    "FakeCall",
    "FakeClient",
    "Flow",
    "InstructorClient",
    "Step",
    "Tool",
    "Trace",
    "TraceRecord",
    "flow",
    "get_default_client",
    "set_default_client",
    "step",
    "trace",
]
