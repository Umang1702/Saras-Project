"""
Tests for the planner using a fake LLM provider (no real API calls, no
network access needed to run the test suite).
"""
from intelligence.llm import LLMService
from intelligence.providers.base import LLMProvider, LLMResponse, ToolCallRequest
from core.planner import TaskPlanner
from security.policies import PermissionLevel
from tools.base import Tool, ToolInput, ToolResult
from tools.registry import ToolRegistry


class DummyInput(ToolInput):
    value: int = 0


class DummyTool(Tool):
    name = "dummy_tool"
    description = "test"
    permission_level = PermissionLevel.SAFE
    input_model = DummyInput

    def run(self, params: DummyInput) -> ToolResult:
        return ToolResult(success=True, message="ok")


class FakeProvider(LLMProvider):
    def __init__(self, response: LLMResponse):
        self._response = response

    def complete(self, system_prompt, messages, tools=None):
        return self._response


def test_plan_with_direct_answer():
    provider = FakeProvider(LLMResponse(text="Paris is the capital of France."))
    planner = TaskPlanner(LLMService(provider), ToolRegistry())
    plan = planner.plan("What is the capital of France?", [])
    assert plan.direct_answer == "Paris is the capital of France."
    assert plan.steps == []


def test_plan_with_tool_call():
    provider = FakeProvider(LLMResponse(tool_calls=[ToolCallRequest(tool_name="dummy_tool", arguments={"value": 1})]))
    registry = ToolRegistry()
    registry.register(DummyTool())
    planner = TaskPlanner(LLMService(provider), registry)
    plan = planner.plan("do the dummy thing", [])
    assert plan.direct_answer is None
    assert len(plan.steps) == 1
    assert plan.steps[0].tool_name == "dummy_tool"


def test_plan_skips_unknown_tool():
    provider = FakeProvider(LLMResponse(tool_calls=[ToolCallRequest(tool_name="nonexistent", arguments={})]))
    planner = TaskPlanner(LLMService(provider), ToolRegistry())
    try:
        planner.plan("do something", [])
        assert False, "expected PlannerError"
    except Exception as exc:
        assert "no valid" in str(exc).lower() or "valid" in str(exc).lower()
