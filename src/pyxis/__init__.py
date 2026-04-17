"""pyxis: declarative chain-of-thought agent framework.

code as prompt + schema as workflow.
"""

from .client import (
    AsyncClient,
    Client,
    CompletionResult,
    FakeCall,
    FakeClient,
    InstructorClient,
    Usage,
    get_default_client,
    set_default_client,
)
from .flow import AsyncFlow, Flow, flow
from .step import AsyncStep, Step, step
from .tool import Tool
from .trace import Trace, TraceRecord, trace

__version__ = "0.1.0"

__all__ = [
    "AsyncClient",
    "AsyncFlow",
    "AsyncStep",
    "Client",
    "CompletionResult",
    "FakeCall",
    "FakeClient",
    "Flow",
    "InstructorClient",
    "Step",
    "Tool",
    "Trace",
    "TraceRecord",
    "Usage",
    "flow",
    "get_default_client",
    "set_default_client",
    "step",
    "trace",
]
