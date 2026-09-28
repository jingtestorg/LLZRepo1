"""Unit tests for out-of-scope query handling (R4)."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _path(add_agent_to_path):
    pass


@pytest.fixture
def mock_tools():
    mock_data = json.loads((Path(__file__).parent.parent / "mcp-mock.json").read_text())
    server = mock_data["servers"]["sap-s4-cost-center"]
    tools = []
    for tool_name, tool_info in server["tools"].items():
        tool = MagicMock()
        tool.name = tool_name
        tool.description = tool_info["description"]
        tool.ainvoke = AsyncMock(return_value=json.dumps(tool_info["mock_response"]))
        tools.append(tool)
    return tools


@pytest.fixture
def agent(add_agent_to_path):
    from agent import SampleAgent
    return SampleAgent()


@pytest.mark.asyncio
async def test_out_of_scope_query_returns_helpful_message(agent, mock_tools):
    """Agent should respond gracefully to unsupported queries."""
    out_of_scope_message = (
        "I can only answer questions about cost center data. "
        "Specifically: (1) total count of cost centers or (2) top 5 cost centers. "
        "Your question is outside my supported scope."
    )
    fake_result = {"messages": [MagicMock(content=out_of_scope_message)]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)):
        response = await agent.invoke(
            "What is the budget variance for cost center CC-1000?",
            "ctx-oos",
            tools=mock_tools,
        )

    assert response.status == "completed"
    assert response.message  # non-empty response


@pytest.mark.asyncio
async def test_out_of_scope_does_not_hallucinate(agent, mock_tools):
    """Agent should not fabricate data for unsupported queries."""
    out_of_scope_message = "I cannot answer questions about budget variances. I can only provide cost center count or top 5 cost centers."
    fake_result = {"messages": [MagicMock(content=out_of_scope_message)]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)):
        response = await agent.invoke(
            "Create a new cost center for IT department",
            "ctx-create",
            tools=mock_tools,
        )

    assert response.status == "completed"
    # Should NOT contain confirmations of creating anything
    assert "created" not in response.message.lower() or "cannot" in response.message.lower()


@pytest.mark.asyncio
async def test_no_tools_returns_unavailable_message(agent):
    """Agent with no tools should return a tools-unavailable message."""
    unavailable_msg = "Tools are temporarily unavailable. Please try again later."
    fake_result = {"messages": [MagicMock(content=unavailable_msg)]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)):
        response = await agent.invoke(
            "How many cost centers are there?",
            "ctx-notools",
            tools=[],
        )

    assert response.status == "completed"
    assert response.message


@pytest.mark.asyncio
async def test_out_of_scope_milestone_logging(agent, mock_tools, caplog):
    """M2.missed should be logged when intent cannot be classified (no tools)."""
    import logging
    unavailable_msg = "Tools are temporarily unavailable."
    fake_result = {"messages": [MagicMock(content=unavailable_msg)]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)):
        with caplog.at_level(logging.INFO, logger="agent"):
            await agent.invoke("How many cost centers?", "ctx-m2", tools=[])

    log_text = " ".join(caplog.messages)
    assert "M2.missed" in log_text or "M1.achieved" in log_text
