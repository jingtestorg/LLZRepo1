"""Integration test — end-to-end agent flow with mocked LLM and MCP tools."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _path(add_agent_to_path):
    pass


@pytest.fixture
def mock_tools_from_json():
    """Load tools from mcp-mock.json and build mock LangChain tool objects."""
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


@pytest.mark.asyncio
async def test_end_to_end_count_query(add_agent_to_path, mock_tools_from_json):
    """Full agent flow: count query → MCP tool call → formatted answer."""
    from agent import SampleAgent

    agent = SampleAgent()
    fake_response = "There are 47 cost centers in total across all controlling areas."
    fake_result = {"messages": [MagicMock(content=fake_response)]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)):
        response = await agent.invoke(
            "How many cost centers do we have?",
            "integration-ctx-001",
            tools=mock_tools_from_json,
        )

    assert response.status == "completed"
    assert response.message == fake_response


@pytest.mark.asyncio
async def test_end_to_end_top5_query(add_agent_to_path, mock_tools_from_json):
    """Full agent flow: top-5 query → MCP tool call → ranked list answer."""
    from agent import SampleAgent

    agent = SampleAgent()
    top5_response = (
        "Here are the top 5 cost centers:\n"
        "1. CC-1000 - Corporate IT (Controlling Area: A000)\n"
        "2. CC-2000 - Finance (Controlling Area: A000)\n"
        "3. CC-3000 - Human Resources (Controlling Area: A000)\n"
        "4. CC-4000 - Marketing (Controlling Area: A000)\n"
        "5. CC-5000 - Sales (Controlling Area: A000)"
    )
    fake_result = {"messages": [MagicMock(content=top5_response)]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)):
        response = await agent.invoke(
            "What are the top 5 cost centers?",
            "integration-ctx-002",
            tools=mock_tools_from_json,
        )

    assert response.status == "completed"
    assert "CC-1000" in response.message


@pytest.mark.asyncio
async def test_end_to_end_mcp_tool_metadata(add_agent_to_path, mock_tools_from_json):
    """Tools loaded from mcp-mock.json must have the expected names and descriptions."""
    tool_names = {t.name for t in mock_tools_from_json}
    assert "GET_ACostCenter2" in tool_names
    assert "GET_ACostCenterText2" in tool_names

    cost_center_tool = next(t for t in mock_tools_from_json if t.name == "GET_ACostCenter2")
    assert cost_center_tool.description  # non-empty description


@pytest.mark.asyncio
async def test_end_to_end_session_complete_milestone(add_agent_to_path, mock_tools_from_json, caplog):
    """M5 milestone should be logged on successful session completion."""
    import logging
    from agent import SampleAgent

    agent = SampleAgent()
    fake_result = {"messages": [MagicMock(content="There are 47 cost centers.")]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)):
        with caplog.at_level(logging.INFO, logger="agent"):
            await agent.invoke(
                "How many cost centers do we have?",
                "integration-ctx-003",
                tools=mock_tools_from_json,
            )

    log_text = " ".join(caplog.messages)
    assert "M5.achieved" in log_text


@pytest.mark.asyncio
async def test_end_to_end_error_handling(add_agent_to_path, mock_tools_from_json, caplog):
    """When MCP call fails, agent returns error message and logs M5.missed."""
    import logging
    from agent import SampleAgent

    agent = SampleAgent()

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(side_effect=RuntimeError("MCP unavailable"))):
        with caplog.at_level(logging.INFO, logger="agent"):
            response = await agent.invoke(
                "How many cost centers?",
                "integration-ctx-error",
                tools=mock_tools_from_json,
            )

    assert response.status == "completed"
    assert "error" in response.message.lower() or "encountered" in response.message.lower()

    log_text = " ".join(caplog.messages)
    assert "M5.missed" in log_text
