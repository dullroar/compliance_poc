"""Look up a domain's adapter (loan-payload mapping and report extras) by domain key."""
from __future__ import annotations

import importlib
from types import ModuleType


def adapter(domain: str) -> ModuleType:
    """Return compliance_mcp.<domain>.adapter, which must define TOOL, tool_arguments,
    unavailable and extras."""
    return importlib.import_module(f"compliance_mcp.{domain}.adapter")
