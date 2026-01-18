"""
Ralph Deep Research - Brief Builder Agent

Interactive dialog agent that transforms vague user queries into structured
research specifications (Brief/Technical Specification).

Based on specs/PROMPTS.md Section 2.

Why this agent:
- Asks clarifying questions ONE at a time
- Builds research specification iteratively
- Handles user modifications and revisions
- Produces approved Brief for research execution

Timeout: 10 seconds (target: 5 seconds per interaction)

Usage:
    agent = BriefBuilderAgent(llm_client, session_manager)
    result = await agent.run(session_id, {
        "session_id": "sess_123",
        "initial_context": {...},
        "conversation_history": [...],
        "current_brief": None,
        "user_message": "I want to invest long term"
    })
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.api.schemas import (
    Brief,
    BriefBuilderAction,
    BriefConstraints,
    BriefStatus,
    InitialContext,
    OutputFormat,
    Priority,
    RiskProfile,
    ScopeItem,
    ScopeType,
    UserContext,
    UserIntent,
)
from src.storage.session import DataType
from src.tools.errors import InvalidInputError


# =============================================================================
# OUTPUT MODELS FOR STRUCTURED LLM RESPONSE
# =============================================================================


class LLMScopeItem(BaseModel):
    """Scope item from LLM response."""
    id: int
    topic: str
    type: str = Field(description="data|research|both")
    details: str | None = None
    priority: str = Field(default="medium", description="high|medium|low")


class LLMUserContext(BaseModel):
    """User context from LLM response."""
    intent: str = Field(description="investment|market_research|competitive|learning|due_diligence|other")
    horizon: str | None = None
    risk_profile: str | None = Field(default=None, description="conservative|moderate|aggressive")
    additional: dict[str, Any] | None = None


class LLMBriefConstraints(BaseModel):
    """Brief constraints from LLM response."""
    focus_areas: list[str] = Field(default_factory=list)
    exclude: list[str] = Field(default_factory=list)
    time_period: str | None = None
    geographic_focus: str | None = None
    max_sources: int | None = None


class LLMBrief(BaseModel):
    """Brief from LLM response."""
    brief_id: str
    version: int = 1
    status: str = "draft"
    goal: str
    user_context: LLMUserContext | None = None
    scope: list[LLMScopeItem] = Field(default_factory=list)
    output_formats: list[str] = Field(default_factory=lambda: ["pdf", "excel"])
    constraints: LLMBriefConstraints | None = None


class LLMBriefBuilderOutput(BaseModel):
    """Output from Brief Builder LLM call."""
    action: str = Field(description="ask_question|present_brief|brief_approved")
    message: str
    current_brief: LLMBrief | None = None


# =============================================================================
# AGENT IMPLEMENTATION
# =============================================================================


class BriefBuilderAgent(BaseAgent):
    """
    Brief Builder Agent - Interactive research specification builder.

    Guides user through clarifying questions to build a structured
    research brief (Technical Specification / ТЗ).

    Process:
    1. Analyze initial context and conversation history
    2. Determine what information is missing
    3. Ask ONE clarifying question at a time
    4. When ready, present structured Brief for approval
    5. Handle modifications until user approves

    Actions:
    - ask_question: Request clarification from user
    - present_brief: Show draft Brief for approval
    - brief_approved: Confirm approved Brief ready for research
    """

    @property
    def agent_name(self) -> str:
        """Agent name for model selection and logging."""
        return "brief_builder"

    def get_timeout_key(self) -> str:
        """Timeout configuration key."""
        return "brief_builder"

    def validate_input(self, context: dict[str, Any]) -> None:
        """
        Validate input context.

        Args:
            context: Input context

        Raises:
            InvalidInputError: If required fields missing
        """
        super().validate_input(context)

        if "initial_context" not in context and "user_message" not in context:
            raise InvalidInputError(
                message="Either initial_context or user_message is required",
                field="initial_context",
            )

    async def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute brief building iteration.

        Args:
            context: Input with session_id, initial_context,
                     conversation_history, current_brief, user_message

        Returns:
            Dict with action, message, and current_brief
        """
        session_id = context["session_id"]
        initial_context = context.get("initial_context", {})
        conversation_history = context.get("conversation_history", [])
        current_brief = context.get("current_brief")
        user_message = context.get("user_message", "")

        self._logger.info(
            "Processing brief builder iteration",
            conversation_length=len(conversation_history),
            has_brief=current_brief is not None,
        )

        # Build prompt for LLM
        llm_output = await self._process_with_llm(
            session_id=session_id,
            initial_context=initial_context,
            conversation_history=conversation_history,
            current_brief=current_brief,
            user_message=user_message,
        )

        # Convert to proper response format
        result = self._build_response(
            session_id=session_id,
            llm_output=llm_output,
        )

        # Save conversation state
        await self._save_conversation(
            session_id=session_id,
            user_message=user_message,
            response=result,
        )

        # If brief is approved, save it
        if result["action"] == BriefBuilderAction.BRIEF_APPROVED.value:
            await self._save_approved_brief(
                session_id=session_id,
                brief=result.get("current_brief"),
            )

        self._logger.info(
            "Brief builder iteration completed",
            action=result["action"],
        )

        return result

    async def _process_with_llm(
        self,
        session_id: str,
        initial_context: dict[str, Any],
        conversation_history: list[dict[str, str]],
        current_brief: dict[str, Any] | None,
        user_message: str,
    ) -> LLMBriefBuilderOutput:
        """
        Process conversation with LLM.

        Args:
            session_id: Session ID
            initial_context: Initial research context
            conversation_history: Previous messages
            current_brief: Current brief draft if any
            user_message: Latest user message

        Returns:
            Structured LLM output
        """
        # Build context message
        context_parts = []

        # Add initial context summary
        if initial_context:
            context_summary = initial_context.get("context_summary", "")
            entities = initial_context.get("entities", [])
            suggested_topics = initial_context.get("suggested_topics", [])

            context_parts.append("## Initial Research Context:")
            if context_summary:
                context_parts.append(f"Summary: {context_summary}")
            if entities:
                entity_names = [e.get("name", "") for e in entities[:5]]
                context_parts.append(f"Entities: {', '.join(entity_names)}")
            if suggested_topics:
                context_parts.append(f"Suggested topics: {', '.join(suggested_topics[:5])}")
            context_parts.append("")

        # Add current brief if exists
        if current_brief:
            context_parts.append("## Current Brief Draft:")
            context_parts.append(f"Goal: {current_brief.get('goal', 'Not set')}")
            scope = current_brief.get("scope", [])
            if scope:
                context_parts.append("Scope items:")
                for item in scope:
                    context_parts.append(f"  - {item.get('topic', '')}")
            context_parts.append(f"Version: {current_brief.get('version', 1)}")
            context_parts.append(f"Status: {current_brief.get('status', 'draft')}")
            context_parts.append("")

        context_str = "\n".join(context_parts)

        # Build conversation messages for LLM
        messages = []

        # Add history
        for msg in conversation_history[-10:]:  # Last 10 messages
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

        # Add current context and user message
        system_context = f"""
{context_str}

## Instructions:
Based on the conversation and context:
1. If you need more information, ask ONE clarifying question
2. If you have enough information, present a structured Brief for approval
3. If the user approves, mark the Brief as approved

Always respond with a JSON matching the output schema.
"""

        if user_message:
            messages.append({
                "role": "user",
                "content": f"{system_context}\n\nUser message: {user_message}",
            })
        elif not messages:
            # First interaction - start the conversation
            messages.append({
                "role": "user",
                "content": f"{system_context}\n\nThis is the start of the conversation. Greet the user and ask your first clarifying question based on their query.",
            })

        # Generate brief_id if needed
        brief_id = (
            current_brief.get("brief_id")
            if current_brief
            else f"brief_{uuid.uuid4().hex[:12]}"
        )

        try:
            result = await self._call_llm_structured(
                messages=messages,
                response_model=LLMBriefBuilderOutput,
                max_tokens=2048,
                temperature=0.5,
            )

            # Ensure brief_id is set correctly
            if result.current_brief:
                result.current_brief.brief_id = brief_id

            return result

        except Exception as e:
            self._logger.warning(
                "Structured LLM call failed, using fallback",
                error=str(e),
            )
            return self._create_fallback_output(brief_id, initial_context)

    def _create_fallback_output(
        self,
        brief_id: str,
        initial_context: dict[str, Any],
    ) -> LLMBriefBuilderOutput:
        """
        Create fallback output if LLM call fails.

        Args:
            brief_id: Brief ID to use
            initial_context: Initial research context

        Returns:
            Basic output asking for goal clarification
        """
        query = ""
        if initial_context:
            query_analysis = initial_context.get("query_analysis", {})
            query = query_analysis.get("original_query", "")

        message = (
            f"Понял, вас интересует: {query}. "
            "Подскажите, какова ваша цель? "
            "Хотите инвестировать, изучить рынок, или просто узнать больше?"
            if query
            else "Подскажите, какова ваша цель исследования?"
        )

        return LLMBriefBuilderOutput(
            action="ask_question",
            message=message,
            current_brief=None,
        )

    def _build_response(
        self,
        session_id: str,
        llm_output: LLMBriefBuilderOutput,
    ) -> dict[str, Any]:
        """
        Build response from LLM output.

        Args:
            session_id: Session ID
            llm_output: Structured LLM output

        Returns:
            Response dictionary
        """
        # Convert action
        try:
            action = BriefBuilderAction(llm_output.action)
        except ValueError:
            action = BriefBuilderAction.ASK_QUESTION

        # Convert brief if present
        brief_dict = None
        if llm_output.current_brief:
            brief_dict = self._convert_brief(llm_output.current_brief)

        return {
            "action": action.value,
            "message": llm_output.message,
            "current_brief": brief_dict,
        }

    def _convert_brief(self, llm_brief: LLMBrief) -> dict[str, Any]:
        """
        Convert LLM brief to proper Brief format.

        Args:
            llm_brief: Brief from LLM

        Returns:
            Brief as dictionary
        """
        # Convert status
        try:
            status = BriefStatus(llm_brief.status)
        except ValueError:
            status = BriefStatus.DRAFT

        # Convert user context
        user_context = None
        if llm_brief.user_context:
            try:
                intent = UserIntent(llm_brief.user_context.intent)
            except ValueError:
                intent = UserIntent.OTHER

            risk_profile = None
            if llm_brief.user_context.risk_profile:
                try:
                    risk_profile = RiskProfile(llm_brief.user_context.risk_profile)
                except ValueError:
                    pass

            user_context = UserContext(
                intent=intent,
                horizon=llm_brief.user_context.horizon,
                risk_profile=risk_profile,
                additional=llm_brief.user_context.additional,
            )

        # Convert scope items
        scope = []
        for llm_item in llm_brief.scope:
            try:
                scope_type = ScopeType(llm_item.type)
            except ValueError:
                scope_type = ScopeType.BOTH

            try:
                priority = Priority(llm_item.priority)
            except ValueError:
                priority = Priority.MEDIUM

            scope_item = ScopeItem(
                id=llm_item.id,
                topic=llm_item.topic[:200],
                type=scope_type,
                details=llm_item.details[:500] if llm_item.details else None,
                priority=priority,
            )
            scope.append(scope_item)

        # Convert output formats
        output_formats = []
        for fmt in llm_brief.output_formats:
            try:
                output_formats.append(OutputFormat(fmt))
            except ValueError:
                pass
        if not output_formats:
            output_formats = [OutputFormat.PDF]

        # Convert constraints
        constraints = None
        if llm_brief.constraints:
            constraints = BriefConstraints(
                focus_areas=llm_brief.constraints.focus_areas,
                exclude=llm_brief.constraints.exclude,
                time_period=llm_brief.constraints.time_period,
                geographic_focus=llm_brief.constraints.geographic_focus,
                max_sources=llm_brief.constraints.max_sources,
            )

        # Build Brief
        brief = Brief(
            brief_id=llm_brief.brief_id,
            version=llm_brief.version,
            status=status,
            goal=llm_brief.goal[:500] if llm_brief.goal else "Research goal",
            user_context=user_context,
            scope=scope if scope else [
                ScopeItem(id=1, topic="General research", type=ScopeType.BOTH)
            ],
            output_formats=output_formats,
            constraints=constraints,
            approved_at=datetime.now(timezone.utc) if status == BriefStatus.APPROVED else None,
        )

        return brief.model_dump(mode="json")

    async def _save_conversation(
        self,
        session_id: str,
        user_message: str,
        response: dict[str, Any],
    ) -> None:
        """
        Save conversation turn to session.

        Args:
            session_id: Session ID
            user_message: User's message
            response: Agent's response
        """
        conversation_entry = {
            "user_message": user_message,
            "assistant_message": response["message"],
            "action": response["action"],
            "has_brief": response.get("current_brief") is not None,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        await self._save_result(
            session_id=session_id,
            data_type=DataType.CONVERSATION,
            result=conversation_entry,
        )

    async def _save_approved_brief(
        self,
        session_id: str,
        brief: dict[str, Any] | None,
    ) -> None:
        """
        Save approved brief to session.

        Args:
            session_id: Session ID
            brief: Approved brief dictionary
        """
        if brief:
            # Ensure approved status
            brief["status"] = BriefStatus.APPROVED.value
            brief["approved_at"] = datetime.now(timezone.utc).isoformat()

            await self._save_result(
                session_id=session_id,
                data_type=DataType.BRIEF,
                result=brief,
            )

            self._logger.info(
                "Brief approved and saved",
                brief_id=brief.get("brief_id"),
                version=brief.get("version"),
            )
