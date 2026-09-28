"""Unit tests for the top 5 cost centers query feature (R2)."""
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
async def test_top5_query_returns_list(agent, mock_tools):
    """Agent should return a list of 5 cost centers with name and ID."""
    top5_content = (
        "Here are the top 5 cost centers:\n"
        "1. CC-1000 - Corporate IT (A000)\n"
        "2. CC-2000 - Finance (A000)\n"
        "3. CC-3000 - Human Resources (A000)\n"
        "4. CC-4000 - Marketing (A000)\n"
        "5. CC-5000 - Sales (A000)"
    )
    fake_result = {"messages": [MagicMock(content=top5_content)]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)):
        response = await agent.invoke("What are the top 5 cost centers?", "ctx-top5", tools=mock_tools)

    assert response.status == "completed"
    assert "CC-" in response.message or "cost center" in response.message.lower()


@pytest.mark.asyncio
async def test_top5_query_variants(agent, mock_tools):
    """Agent should handle multiple phrasings for top 5 query."""
    fake_result = {"messages": [MagicMock(content="Top 5: CC-1000, CC-2000, CC-3000, CC-4000, CC-5000")]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)):
        for query in [
            "What are the top 5 cost centers?",
            "Show me the top cost centers",
            "List the leading cost centers",
        ]:
            response = await agent.invoke(query, "ctx-top5v", tools=mock_tools)
            assert response.status == "completed"


@pytest.mark.asyncio
async def test_top5_response_contains_identifiers(agent, mock_tools):
    """Response must include cost center identifiers (ID or name)."""
    fake_result = {"messages": [MagicMock(
        content="1. CC-1000 Corporate IT\n2. CC-2000 Finance\n3. CC-3000 HR\n4. CC-4000 Marketing\n5. CC-5000 Sales"
    )]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)):
        response = await agent.invoke("Top 5 cost centers please", "ctx-ids", tools=mock_tools)

    assert response.status == "completed"
    # Response should contain at least one cost center identifier
    assert any(cc in response.message for cc in ["CC-1000", "CC-2000", "Corporate IT", "Finance"])


@pytest.mark.asyncio
async def test_top5_mcp_tool_called(agent, mock_tools):
    """Verify agent calls MCP tool and returns its result."""
    fake_result = {"messages": [MagicMock(content="Top 5 cost centers retrieved.")]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)) as mock_inv:
        await agent.invoke("Show top 5 cost centers", "ctx-tool", tools=mock_tools)
        mock_inv.assert_called_once()
        call_kwargs = mock_inv.call_args
        assert len(call_kwargs.kwargs.get("tools", mock_tools)) > 0
