import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Literal, Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from langchain_litellm import ChatLiteLLM
from langgraph.graph.state import CompiledStateGraph
from litellm.exceptions import APIConnectionError, APIError, Timeout
from opentelemetry import trace
from sap_cloud_sdk.agent_decorators import agent_config, agent_model, prompt_section
from sap_cloud_sdk.agent_memory.factory.langgraph_checkpoint import create_checkpointer
from mcp_providers.agw import get_user_sub

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

TOP_5_COUNT = 5


@agent_model(
    key="config.model",
    label="LLM Model",
    description="The language model powering this agent",
)
def get_model_name() -> str:
    return "sap/anthropic--claude-4.5-sonnet"


@agent_model(
    key="config.fallback_model",
    label="Fallback LLM Model",
    description="Fallback model used when the primary model is unavailable. Leave empty to disable fallback.",
)
def get_fallback_model_name() -> str:
    return ""


@agent_config(
    key="config.temperature",
    label="LLM Temperature",
    description="Controls randomness of responses (0.0 = deterministic, 1.0 = creative)",
)
def get_temperature() -> float:
    return 0.0


@agent_config(
    key="config.checkpointer.ttl_seconds",
    label="Thread TTL (seconds)",
    description="Evict inactive conversation threads after this period of inactivity. Set to 0 to disable eviction.",
)
def thread_ttl_seconds() -> int:
    return 3600  # 1 hour


@prompt_section(
    key="prompts.system",
    label="System Prompt",
    description="The full system prompt defining the agent's role and behavior",
    validation={"format": "markdown", "max_length": 5000},
)
def get_system_prompt() -> str:
    return (
        "You are a Finance Controller assistant. You answer questions about SAP S/4HANA cost center data.\n\n"
        "You support exactly two types of queries:\n"
        "1. Total count of cost centers - e.g. 'How many cost centers do we have?', 'What is the total number of cost centers?'\n"
        "2. Top 5 cost centers - e.g. 'What are the top 5 cost centers?', 'Show me the leading cost centers'\n\n"
        "IMPORTANT:\n"
        "- You MUST use tools to retrieve live data. Never fabricate, guess, or invent data.\n"
        "- When calling tools that support pagination, always set the page size parameter (top) to a maximum of 100 items.\n"
        "- If a tool returns an error, report the error message exactly as received. Do not suggest workarounds.\n"
        "- If the query is outside the supported scope above, respond with a clear message explaining you can only answer "
        "questions about (1) total cost center count and (2) top 5 cost centers.\n"
        "- Never create, update, or delete cost centers. This agent is strictly read-only."
    )


@dataclass
class AgentResponse:
    status: Literal["input_required", "completed", "error"]
    message: str


class SampleAgent:
    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

    def __init__(self):
        ttl = thread_ttl_seconds()
        self._primary_model = get_model_name()
        self._fallback_model = get_fallback_model_name().strip()
        self._temperature = get_temperature()

        _cache_kwargs = {
            "cache_control_injection_points": [
                {"location": "message", "role": "system", "control": {"type": "ephemeral"}}
            ]
        }
        self.llm = ChatLiteLLM(
            model=self._primary_model,
            temperature=self._temperature,
            model_kwargs=_cache_kwargs,
        )
        self._fallback_llm = (
            ChatLiteLLM(
                model=self._fallback_model,
                temperature=self._temperature,
                model_kwargs=_cache_kwargs,
            )
            if self._fallback_model
            else None
        )
        self._checkpointer = create_checkpointer(ttl_seconds=ttl or None)
        summarization_llm = ChatLiteLLM(model="sap/anthropic--claude-4.5-haiku", temperature=0.0)
        self._summarization_middleware = SummarizationMiddleware(
            model=summarization_llm,
            trigger=("tokens", 30_000),
            keep=("messages", 4),
        )

    def _create_graph(
        self,
        llm: ChatLiteLLM,
        tools: Sequence[BaseTool],
        system_prompt: str,
    ) -> CompiledStateGraph:
        return create_agent(
            llm,
            tools=list(tools),
            system_prompt=system_prompt,
            checkpointer=self._checkpointer,
            middleware=[self._summarization_middleware],
        )

    async def _invoke_with_fallback(
        self,
        tools: Sequence[BaseTool],
        system_prompt: str,
        query: str,
        context_id: str,
        extra_messages: list | None = None,
    ) -> dict[str, Any]:
        config = {"configurable": {"thread_id": f"{get_user_sub()}:{context_id}"}}
        messages = {"messages": (extra_messages or []) + [HumanMessage(content=query)]}

        try:
            graph = self._create_graph(self.llm, tools, system_prompt)
            return await graph.ainvoke(messages, config)
        except (APIConnectionError, APIError, Timeout) as primary_error:
            if not self._fallback_llm:
                raise
            logger.warning(
                "Primary model '%s' failed. Retrying with fallback model '%s'. Error: %s",
                self._primary_model,
                self._fallback_model,
                primary_error,
            )

        graph = self._create_graph(self._fallback_llm, tools, system_prompt)
        result = await graph.ainvoke(messages, config)
        logger.info(
            "Request completed with fallback model '%s' after primary model '%s' failed.",
            self._fallback_model,
            self._primary_model,
        )
        return result

    async def _run_agent(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool],
    ) -> str:
        """Core agent execution — instrumented with M1-M5 milestone spans.

        This is a plain async method (not a generator), so OpenTelemetry context
        managers are safe to use here without GeneratorExit errors.
        """
        # M1 — Query received
        if not query or not query.strip():
            logger.info("M1.missed: no input received or input was empty")
            return "I did not receive a question. Please ask me about cost centers."
        logger.info("M1.achieved: user query received and passed to intent classification")

        with tracer.start_as_current_span("M1_query_received"):
            pass  # milestone marker — actual work follows in M2

        # M2 — Intent classification (handled by LLM; we instrument the routing decision here)
        with tracer.start_as_current_span("M2_intent_classification"):
            system_prompt = get_system_prompt()
            tool_names = [tool.name for tool in tools] if tools else []
            logger.info("Running agent with %d tool(s): %s", len(tool_names), tool_names)

            extra: list = []
            if not tools:
                logger.info("M2.missed: intent could not be classified — returning out-of-scope message")
                extra.append(
                    SystemMessage(
                        content=(
                            "IMPORTANT: No tools are currently available. "
                            "Do not attempt to call any tools. Respond to the user "
                            "explaining that tools are temporarily unavailable."
                        )
                    )
                )
            else:
                logger.info("M2.achieved: intent classified, routing to MCP tool")

        # M3 — Data retrieval from CE_COSTCENTER_0001
        with tracer.start_as_current_span("M3_data_retrieval"):
            try:
                result = await self._invoke_with_fallback(
                    tools=tools or [],
                    system_prompt=system_prompt,
                    query=query,
                    context_id=context_id,
                    extra_messages=extra or None,
                )
                response = result["messages"][-1].content
                logger.info("M3.achieved: cost center data retrieved from CE_COSTCENTER_0001")
            except Exception as exc:
                logger.error("M3.missed: MCP server call failed or returned empty result — %s", exc)
                raise

        # M4 — Answer formatted and delivered
        with tracer.start_as_current_span("M4_answer_delivered"):
            logger.info("M4.achieved: response delivered to user")

        return response

    async def stream(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AsyncGenerator[dict, None]:
        """Stream agent responses."""
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content": "Processing...",
        }

        try:
            response = await self._run_agent(
                query=query,
                context_id=context_id,
                tools=tools or [],
            )
            # M5 — Session complete
            logger.info("M5.achieved: session completed — controller query resolved via agent")
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response,
            }

        except Exception:
            logger.exception("Agent stream() failed")
            logger.info("M5.missed: session ended without resolving the controller's query")
            yield {
                "is_task_complete": True,
                "require_user_input": False,
                "content": "I encountered an error while processing your request. Please try again.",
            }

    async def invoke(
        self,
        query: str,
        context_id: str,
        tools: Sequence[BaseTool] | None = None,
    ) -> AgentResponse:
        """Invoke agent and return final response."""
        last: dict = {}
        async for chunk in self.stream(query, context_id, tools=tools):
            last = chunk
        if last.get("is_task_complete"):
            return AgentResponse(status="completed", message=last["content"])
        if last.get("require_user_input"):
            return AgentResponse(status="input_required", message=last["content"])
        return AgentResponse(
            status="error", message=last.get("content", "Unknown error")
        )
