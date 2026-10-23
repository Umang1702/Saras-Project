"""Tests for the tool registry — registration, lookup, duplicate rejection."""
import pytest

from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult
from tools.registry import ToolRegistry
from utils.exceptions import ToolNotFoundError


class DummyInput(ToolInput):
    value: int = 0


class DummyTool(Tool):
    name = "dummy_tool"
    description = "A tool for testing."
    permission_level = PermissionLevel.SAFE
    input_model = DummyInput

    def run(self, params: DummyInput) -> ToolResult:
        return ToolResult(success=True, message="ok", data={"value": params.value})


def test_register_and_get():
    registry = ToolRegistry()
    registry.register(DummyTool())
    assert registry.has("dummy_tool")
    assert registry.get("dummy_tool").name == "dummy_tool"


def test_duplicate_registration_raises():
    registry = ToolRegistry()
    registry.register(DummyTool())
    with pytest.raises(ValueError):
        registry.register(DummyTool())


def test_unknown_tool_raises():
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        registry.get("does_not_exist")


def test_llm_schemas_shape():
    registry = ToolRegistry()
    registry.register(DummyTool())
    schemas = registry.llm_schemas()
    assert schemas[0]["name"] == "dummy_tool"
    assert "parameters" in schemas[0]
