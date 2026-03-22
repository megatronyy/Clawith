"""Unified LLM calling service with failover support for all execution paths.

This module provides a shared entry point for all LLM calls across:
- WebSocket chat
- IM channels (Feishu, Slack, Teams, Discord, WeCom, DingTalk)
- Background services (task executor, scheduler, heartbeat, etc.)

All paths now support:
1. Config-level fallback: if primary missing, use fallback directly
2. Runtime failover: if primary fails with retryable error, try fallback once
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm_failover import classify_error, FailoverErrorType
from app.services.llm_utils import LLMMessage

if TYPE_CHECKING:
    from app.models.agent import Agent
    from app.models.llm import LLMModel


async def call_agent_llm(
    db: AsyncSession,
    agent_id: uuid.UUID,
    user_text: str,
    history: list[dict] | None = None,
    user_id: uuid.UUID | None = None,
    on_chunk=None,
    on_thinking=None,
    supports_vision: bool = False,
) -> str:
    """Call the agent's LLM with automatic failover support.

    This is the unified entry point for ALL LLM calls across all channels.

    Args:
        db: Database session
        agent_id: Agent UUID
        user_text: User message text
        history: Optional conversation history (last N messages)
        user_id: Optional user UUID (for personalized context)
        on_chunk: Optional streaming callback
        on_thinking: Optional thinking/reasoning callback
        supports_vision: Whether the model supports vision

    Returns:
        LLM response string, or error message if both primary and fallback fail
    """
    from app.models.agent import Agent
    from app.models.llm import LLMModel
    from app.api.websocket import call_llm

    # Load agent
    agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent: Agent | None = agent_result.scalar_one_or_none()
    if not agent:
        return "⚠️ 数字员工未找到"

    from app.core.permissions import is_agent_expired
    if is_agent_expired(agent):
        return "This Agent has expired and is off duty. Please contact your admin to extend its service."

    # Load primary model
    primary_model: LLMModel | None = None
    if agent.primary_model_id:
        model_result = await db.execute(select(LLMModel).where(LLMModel.id == agent.primary_model_id))
        primary_model = model_result.scalar_one_or_none()

    # Load fallback model
    fallback_model: LLMModel | None = None
    if agent.fallback_model_id:
        fb_result = await db.execute(select(LLMModel).where(LLMModel.id == agent.fallback_model_id))
        fallback_model = fb_result.scalar_one_or_none()

    # Config-level fallback: primary missing -> use fallback
    if not primary_model and fallback_model:
        primary_model = fallback_model
        fallback_model = None
        logger.warning(f"[call_agent_llm] Primary model unavailable, using fallback: {primary_model.model}")

    if not primary_model:
        return f"⚠️ {agent.name} 未配置 LLM 模型，请在管理后台设置。"

    # Build conversation messages
    messages: list[dict] = []
    if history:
        messages.extend(history[-10:])
    messages.append({"role": "user", "content": user_text})

    # Use unified call_llm with failover
    try:
        reply = await call_llm(
            primary_model,
            messages,
            agent.name,
            agent.role_description or "",
            agent_id=agent_id,
            user_id=user_id or agent_id,
            supports_vision=supports_vision or getattr(primary_model, 'supports_vision', False),
            on_chunk=on_chunk,
            on_thinking=on_thinking,
            fallback_model=fallback_model,
        )
        return reply
    except Exception as e:
        # call_llm should handle failover internally, but catch any unexpected errors
        error_msg = str(e) or repr(e)
        logger.error(f"[call_agent_llm] Unexpected error: {error_msg}")
        return f"⚠️ 调用模型出错: {error_msg[:150]}"


async def call_agent_llm_with_tools(
    db: AsyncSession,
    agent_id: uuid.UUID,
    system_prompt: str,
    user_prompt: str,
    max_rounds: int = 50,
) -> str:
    """Call agent LLM with tool-calling loop (for background services).

    Used by scheduler, heartbeat, and other background tasks.

    Args:
        db: Database session
        agent_id: Agent UUID
        system_prompt: System prompt/context
        user_prompt: User/instruction message
        max_rounds: Maximum tool-calling rounds

    Returns:
        Final response string
    """
    from app.models.agent import Agent
    from app.models.llm import LLMModel
    from app.services.agent_tools import execute_tool, get_agent_tools_for_llm
    from app.services.llm_utils import create_llm_client, get_max_tokens, LLMError

    # Load agent and models
    agent_result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent: Agent | None = agent_result.scalar_one_or_none()
    if not agent:
        return "⚠️ Agent not found"

    # Load models
    primary_model: LLMModel | None = None
    if agent.primary_model_id:
        model_result = await db.execute(select(LLMModel).where(LLMModel.id == agent.primary_model_id))
        primary_model = model_result.scalar_one_or_none()

    fallback_model: LLMModel | None = None
    if agent.fallback_model_id:
        fb_result = await db.execute(select(LLMModel).where(LLMModel.id == agent.fallback_model_id))
        fallback_model = fb_result.scalar_one_or_none()

    # Config-level fallback
    if not primary_model and fallback_model:
        primary_model = fallback_model
        fallback_model = None

    if not primary_model:
        return f"⚠️ {agent.name} has no LLM model configured"

    # Build messages
    messages = [
        LLMMessage(role="system", content=system_prompt),
        LLMMessage(role="user", content=user_prompt),
    ]

    # Load tools
    tools_for_llm = await get_agent_tools_for_llm(agent_id)

    async def _try_model(model: LLMModel) -> tuple[str, bool]:
        """Try to complete with a model. Returns (response, success)."""
        try:
            client = create_llm_client(
                provider=model.provider,
                api_key=model.api_key_encrypted,
                model=model.model,
                base_url=model.base_url,
                timeout=120.0,
            )

            max_tokens = get_max_tokens(
                model.provider, model.model,
                getattr(model, 'max_output_tokens', None)
            )

            # Tool-calling loop
            api_messages = list(messages)  # Copy
            for round_i in range(max_rounds):
                try:
                    response = await client.complete(
                        messages=api_messages,
                        tools=tools_for_llm if tools_for_llm else None,
                        temperature=0.7,
                        max_tokens=max_tokens,
                    )
                except Exception as e:
                    await client.close()
                    raise

                if not response.tool_calls:
                    await client.close()
                    return response.content or "[Empty response]", True

                # Execute tool calls
                api_messages.append(LLMMessage(
                    role="assistant",
                    content=response.content or None,
                    tool_calls=[{
                        "id": tc["id"],
                        "type": "function",
                        "function": tc["function"],
                    } for tc in response.tool_calls],
                ))

                for tc in response.tool_calls:
                    fn = tc["function"]
                    tool_name = fn["name"]
                    raw_args = fn.get("arguments", "{}")
                    try:
                        import json
                        args = json.loads(raw_args) if raw_args else {}
                    except json.JSONDecodeError:
                        args = {}

                    result = await execute_tool(
                        tool_name, args,
                        agent_id=agent_id,
                        user_id=agent.creator_id,
                    )
                    api_messages.append(LLMMessage(
                        role="tool",
                        tool_call_id=tc["id"],
                        content=str(result),
                    ))

            await client.close()
            return "[Error] Too many tool call rounds", False

        except Exception as e:
            return f"[Error] {e}", False

    # Try primary model
    reply, success = await _try_model(primary_model)
    if success:
        return reply

    # Primary failed - check if retryable
    error_type = classify_error(Exception(reply))
    if error_type == FailoverErrorType.NON_RETRYABLE or not fallback_model:
        return reply

    # Try fallback model
    logger.info(f"[call_agent_llm_with_tools] Retrying with fallback: {fallback_model.model}")
    reply2, success2 = await _try_model(fallback_model)
    if success2:
        return reply2

    return f"⚠️ Both models failed | Primary: {reply[:80]} | Fallback: {reply2[:80]}"


__all__ = [
    "call_agent_llm",
    "call_agent_llm_with_tools",
]
