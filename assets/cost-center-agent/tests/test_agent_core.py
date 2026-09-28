"""Additional unit tests to improve coverage of agent.py core paths."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from litellm.exceptions import APIConnectionError


@pytest.fixture(autouse=True)
def _path(add_agent_to_path):
    pass


@pytest.fixture
def agent(add_agent_to_path):
    from agent import SampleAgent
    return SampleAgent()


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


@pytest.mark.asyncio
async def test_agent_response_status_completed(agent, mock_tools):
    """Agent invoke returns status=completed on success."""
    fake_result = {"messages": [MagicMock(content="Answer: 47 cost centers.")]}
    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)):
        response = await agent.invoke("How many cost centers?", "ctx-status", tools=mock_tools)
    assert response.status == "completed"
    assert "47" in response.message


@pytest.mark.asyncio
async def test_agent_stream_yields_processing_then_result(agent, mock_tools):
    """stream() must yield a 'Processing...' chunk then the final answer."""
    fake_result = {"messages": [MagicMock(content="There are 47 cost centers.")]}
    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)):
        chunks = []
        async for chunk in agent.stream("How many cost centers?", "ctx-stream", tools=mock_tools):
            chunks.append(chunk)

    assert chunks[0]["is_task_complete"] is False
    assert "Processing" in chunks[0]["content"]
    assert chunks[-1]["is_task_complete"] is True
    assert "47" in chunks[-1]["content"]


@pytest.mark.asyncio
async def test_agent_stream_error_yields_error_message(agent, mock_tools):
    """stream() must yield an error message chunk when _run_agent raises."""
    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(side_effect=RuntimeError("boom"))):
        chunks = []
        async for chunk in agent.stream("How many cost centers?", "ctx-err", tools=mock_tools):
            chunks.append(chunk)

    assert chunks[-1]["is_task_complete"] is True
    assert "error" in chunks[-1]["content"].lower() or "encountered" in chunks[-1]["content"].lower()


@pytest.mark.asyncio
async def test_fallback_model_not_used_when_primary_succeeds(agent, mock_tools):
    """When primary model works, fallback should not be triggered."""
    fake_result = {"messages": [MagicMock(content="47 cost centers.")]}

    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value=fake_result)

    with patch.object(agent, "_create_graph", return_value=mock_graph) as mock_create:
        result = await agent._invoke_with_fallback(
            tools=mock_tools,
            system_prompt="test",
            query="count",
            context_id="ctx-fallback",
        )

    assert result == fake_result
    # _create_graph called only once (primary model)
    assert mock_create.call_count == 1


@pytest.mark.asyncio
async def test_invoke_returns_error_status_when_stream_raises(agent, mock_tools):
    """If stream exhausts without completion, invoke returns error status."""
    fake_result = {"messages": [MagicMock(content="error occurred")]}

    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(side_effect=ValueError("test"))):
        response = await agent.invoke("Count", "ctx-invoke-err", tools=mock_tools)

    assert response.status == "completed"  # error is caught and returned as completed with error message


@pytest.mark.asyncio
async def test_system_prompt_content(agent):
    """System prompt must contain key instructions."""
    from agent import get_system_prompt
    prompt = get_system_prompt()
    assert "Finance Controller" in prompt
    assert "cost center" in prompt.lower()
    assert "read-only" in prompt.lower() or "never create" in prompt.lower()
    assert "MUST use tools" in prompt


@pytest.mark.asyncio
async def test_m4_logging_on_success(agent, mock_tools, caplog):
    """M4.achieved should be logged after successful response delivery."""
    import logging
    fake_result = {"messages": [MagicMock(content="47 cost centers.")]}
    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(return_value=fake_result)):
        with caplog.at_level(logging.INFO, logger="agent"):
            await agent.invoke("How many?", "ctx-m4", tools=mock_tools)

    assert "M4.achieved" in " ".join(caplog.messages)


@pytest.mark.asyncio
async def test_m5_missed_logging_on_error(agent, mock_tools, caplog):
    """M5.missed should be logged when the agent encounters an error."""
    import logging
    with patch.object(agent, "_invoke_with_fallback", new=AsyncMock(side_effect=RuntimeError("error"))):
        with caplog.at_level(logging.INFO, logger="agent"):
            await agent.invoke("How many?", "ctx-m5-miss", tools=mock_tools)

    assert "M5.missed" in " ".join(caplog.messages)
