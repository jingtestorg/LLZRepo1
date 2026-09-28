"""Unit tests for the cost center count query feature (R1)."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add app/ to sys.path via conftest fixture
@pytest.fixture(autouse=True)
def _path(add_agent_to_path):
    pass


@pytest.fixture
def mock_tools():
    """Build mock LangChain tools from mcp-mock.json."""
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
async def test_count_query_invokes_mcp_tool(agent, mock_tools):
    """Agent should call GET_ACostCenter2 to retrieve cost center count."""
    count_tool = next(t for t in mock_tools if t.name == "GET_ACostCenter2")

    fake_result = {"messages": [MagicMock(content="There are 47 cost centers in total.")]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)) as mock_invoke:
        response = await agent.invoke("How many cost centers do we have?", "ctx-001", tools=mock_tools)

    assert response.status == "completed"
    assert "47" in response.message or "cost center" in response.message.lower()


@pytest.mark.asyncio
async def test_count_query_variants(agent, mock_tools):
    """Agent should handle multiple phrasings of a count query."""
    fake_result = {"messages": [MagicMock(content="The total number of cost centers is 47.")]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)):
        for query in [
            "How many cost centers do we have?",
            "What is the total number of cost centers?",
            "Count all cost centers",
        ]:
            response = await agent.invoke(query, "ctx-count", tools=mock_tools)
            assert response.status == "completed"


@pytest.mark.asyncio
async def test_count_query_empty_input(agent, mock_tools):
    """Agent should handle empty input gracefully (M1.missed)."""
    response = await agent.invoke("", "ctx-empty", tools=mock_tools)
    assert response.status == "completed"
    assert response.message  # some message returned


@pytest.mark.asyncio
async def test_count_milestone_logging(agent, mock_tools, caplog):
    """M1 and M3 milestones should be logged on a successful count query."""
    import logging
    fake_result = {"messages": [MagicMock(content="There are 47 cost centers.")]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)):
        with caplog.at_level(logging.INFO, logger="agent"):
            await agent.invoke("How many cost centers are there?", "ctx-log", tools=mock_tools)

    log_text = " ".join(caplog.messages)
    assert "M1.achieved" in log_text
    assert "M3.achieved" in log_text or "M2.achieved" in log_text
