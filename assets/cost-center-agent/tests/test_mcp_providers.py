"""Tests for mcp_providers/agw.py — mock tool loading and token helpers."""
import json
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _path(add_agent_to_path):
    pass


@pytest.mark.asyncio
async def test_get_mcp_tools_returns_mock_tools_in_test_mode():
    """In IBD_TESTING mode, get_mcp_tools() must return tools from mcp-mock.json."""
    from mcp_providers.agw import get_mcp_tools
    tools = await get_mcp_tools()
    assert len(tools) == 2
    tool_names = {t.name for t in tools}
    assert "GET_ACostCenter2" in tool_names
    assert "GET_ACostCenterText2" in tool_names


@pytest.mark.asyncio
async def test_mock_tools_have_descriptions():
    """Mock tools must have non-empty descriptions."""
    from mcp_providers.agw import get_mcp_tools
    tools = await get_mcp_tools()
    for tool in tools:
        assert tool.description, f"Tool {tool.name} has no description"


@pytest.mark.asyncio
async def test_mock_tool_invocation_returns_json():
    """Mock tools must return JSON string responses when invoked."""
    from mcp_providers.agw import get_mcp_tools
    tools = await get_mcp_tools()
    cost_center_tool = next(t for t in tools if t.name == "GET_ACostCenter2")
    result = await cost_center_tool.ainvoke({"top": 5})
    # Result should be JSON-parseable
    data = json.loads(result)
    assert "@odata.count" in data
    assert "value" in data


@pytest.mark.asyncio
async def test_mock_tools_missing_file_returns_empty(tmp_path):
    """If mcp-mock.json is missing, _build_mock_tools returns empty list."""
    from mcp_providers import agw
    original = agw._MOCK_FILE
    try:
        agw._MOCK_FILE = tmp_path / "mcp-mock.json"  # doesn't exist
        tools = agw._build_mock_tools()
        assert tools == []
    finally:
        agw._MOCK_FILE = original


def test_set_and_get_user_token():
    """set_user_token / get_user_token / reset_user_token round-trips correctly."""
    from mcp_providers.agw import set_user_token, get_user_token, reset_user_token
    token_ctx = set_user_token("test-jwt-token")
    assert get_user_token() == "test-jwt-token"
    reset_user_token(token_ctx)
    assert get_user_token() is None


def test_get_user_sub_in_test_mode_with_no_token():
    """get_user_sub() returns 'unknown' in IBD_TESTING mode when no token is set."""
    from mcp_providers.agw import get_user_sub, set_user_token, reset_user_token
    ctx = set_user_token(None)
    try:
        sub = get_user_sub()
        assert sub == "unknown"
    finally:
        reset_user_token(ctx)


@pytest.mark.asyncio
async def test_get_mcp_cost_center_mock_response_count():
    """The count field in mock response should match what was configured."""
    from mcp_providers.agw import get_mcp_tools
    tools = await get_mcp_tools()
    cost_center_tool = next(t for t in tools if t.name == "GET_ACostCenter2")
    result = await cost_center_tool.ainvoke({})
    data = json.loads(result)
    assert data["@odata.count"] == 47
    assert len(data["value"]) == 5  # 5 mock cost centers
