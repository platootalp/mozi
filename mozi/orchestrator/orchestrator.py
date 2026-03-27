"""Main orchestrator for Mozi AI Coding Agent.

This module provides the MainOrchestrator class that coordinates the full
pipeline including intent recognition, complexity assessment, task routing,
and agent execution.

The orchestrator follows this flow:
1. Create or resume session via SessionManager
2. Recognize intent via IntentRecognition
3. Assess complexity via ComplexityAssessor
4. Route task via TaskRouter
5. Execute via AgentRuntime based on routing strategy

Examples
--------
Run a task through the orchestrator:

    orchestrator = MainOrchestrator(model_adapter, tool_registry)
    result = await orchestrator.execute("Edit the main.py file")
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from mozi.core.error import MoziError
from mozi.orchestrator.agent.runtime import AgentRuntime, AgentRuntimeResult
from mozi.orchestrator.core.complexity import (
    ComplexityAssessor,
    TaskComplexity,
)
from mozi.orchestrator.core.intent import (
    IntentResult,
    recognize_intent,
)
from mozi.orchestrator.core.router import (
    RouteResult,
    RoutingStrategy,
    TaskRouter,
)
from mozi.orchestrator.session.context import SessionContext, SessionState
from mozi.orchestrator.session.manager import SessionManager


class OrchestratorError(MoziError):
    """Exception raised for orchestrator errors.

    This exception is raised when the orchestrator encounters an error
    during task execution, session management, or pipeline coordination.

    Attributes
    ----------
    task_description : str | None
        The task description that was being processed when the error occurred.

    Examples
    --------
    Raise when orchestrator fails:

        raise OrchestratorError("Failed to execute task", task_description="Edit file")
    """

    def __init__(
        self,
        message: str,
        task_description: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize OrchestratorError.

        Parameters
        ----------
        message : str
            Human-readable error message.
        task_description : str | None, optional
            The task description being processed when error occurred.
        cause : Exception | None, optional
            The original exception that caused this error.
        """
        super().__init__(message, cause=cause)
        self.task_description: str | None = task_description

    def __repr__(self) -> str:
        """Return detailed string representation for debugging."""
        cause_repr = repr(self.cause) if self.cause else None
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"task_description={self.task_description!r}, "
            f"cause={cause_repr})"
        )


@dataclass
class OrchestratorConfig:
    """Configuration for the main orchestrator.

    Attributes
    ----------
    max_fastpath_iterations : int
        Maximum iterations for FastPath (SIMPLE) tasks.
    max_enhanced_iterations : int
        Maximum iterations for Enhanced (MEDIUM) tasks.
    max_orchestrated_iterations : int
        Maximum iterations for Orchestrated (COMPLEX) tasks.
    enable_monitoring : bool
        Whether to enable execution monitoring.
    default_temperature : float
        Default temperature for model sampling.
    default_max_tokens : int | None
        Default maximum tokens for model output.
    """

    max_fastpath_iterations: int = 5
    max_enhanced_iterations: int = 15
    max_orchestrated_iterations: int = 30
    enable_monitoring: bool = True
    default_temperature: float = 0.7
    default_max_tokens: int | None = None


@dataclass
class OrchestratorResult:
    """Result from orchestrator task execution.

    Attributes
    ----------
    success : bool
        Whether the execution was successful.
    content : str
        The final content/response from execution.
    session_id : str
        The session ID used for this execution.
    intent : IntentResult
        The intent recognition result.
    complexity : TaskComplexity
        The complexity assessment result.
    routing : RouteResult
        The routing decision result.
    agent_result : AgentRuntimeResult | None
        The agent runtime result, if applicable.
    error : str | None
        Error message if execution failed.
    execution_time_ms : int
        Total execution time in milliseconds.
    """

    success: bool = False
    content: str = ""
    session_id: str = ""
    intent: IntentResult | None = None
    complexity: TaskComplexity | None = None
    routing: RouteResult | None = None
    agent_result: AgentRuntimeResult | None = None
    error: str | None = None
    execution_time_ms: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert orchestrator result to dictionary.

        Returns
        -------
        dict[str, Any]
            Dictionary representation of the result.
        """
        return {
            "success": self.success,
            "content": self.content,
            "session_id": self.session_id,
            "intent": self.intent.to_dict() if self.intent else None,
            "complexity": {
                "score": self.complexity.score if self.complexity else None,
                "level": (
                    self.complexity.level.value if self.complexity else None
                ),
                "factors": self.complexity.factors if self.complexity else None,
            },
            "routing": self.routing.to_dict() if self.routing else None,
            "agent_result": {
                "success": self.agent_result.success if self.agent_result else None,
                "iterations": (
                    self.agent_result.iterations if self.agent_result else None
                ),
            },
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
        }


class MainOrchestrator:
    """Main orchestrator coordinating the full Mozi pipeline.

    This class orchestrates the complete task execution flow:
    1. Session management via SessionManager
    2. Intent recognition via recognize_intent()
    3. Complexity assessment via ComplexityAssessor
    4. Task routing via TaskRouter
    5. Agent execution via AgentRuntime

    Attributes
    ----------
    session_manager : SessionManager
        Manages session lifecycle.
    complexity_assessor : ComplexityAssessor
        Assesses task complexity.
    task_router : TaskRouter
        Routes tasks to appropriate execution strategy.
    agent_runtime : AgentRuntime
        Executes tasks using the ReAct loop.
    config : OrchestratorConfig
        Orchestrator configuration.

    Examples
    --------
    Create and use the orchestrator:

        orchestrator = MainOrchestrator(model_adapter, tool_registry)
        result = await orchestrator.execute("Read the config file")
    """

    def __init__(
        self,
        model_adapter: Any,
        tool_registry: Any | None = None,
        session_manager: SessionManager | None = None,
        complexity_assessor: ComplexityAssessor | None = None,
        task_router: TaskRouter | None = None,
        agent_runtime: AgentRuntime | None = None,
        config: OrchestratorConfig | None = None,
    ) -> None:
        """Initialize the main orchestrator.

        Parameters
        ----------
        model_adapter : Any
            Model adapter for LLM interactions.
        tool_registry : Any | None, optional
            Tool registry for tool execution.
        session_manager : SessionManager | None, optional
            Session manager instance. Creates new if not provided.
        complexity_assessor : ComplexityAssessor | None, optional
            Complexity assessor instance. Creates new if not provided.
        task_router : TaskRouter | None, optional
            Task router instance. Creates new if not provided.
        agent_runtime : AgentRuntime | None, optional
            Agent runtime instance. Creates new if not provided.
        config : OrchestratorConfig | None, optional
            Orchestrator configuration. Uses defaults if not provided.
        """
        self._model_adapter = model_adapter
        self._tool_registry = tool_registry
        self._session_manager = session_manager or SessionManager()
        self._complexity_assessor = complexity_assessor or ComplexityAssessor()
        self._task_router = task_router or TaskRouter(
            complexity_assessor=self._complexity_assessor
        )
        self._config = config or OrchestratorConfig()

        # Create agent runtime if not provided
        if agent_runtime is not None:
            self._agent_runtime = agent_runtime
        else:
            # Import here to avoid circular dependency issues at module level
            from mozi.orchestrator.agent.runtime import AgentRuntime

            self._agent_runtime = AgentRuntime(
                model_adapter=self._model_adapter,
                tool_registry=self._tool_registry,
            )

    def _get_max_iterations_for_strategy(
        self, strategy: RoutingStrategy
    ) -> int:
        """Get max iterations based on routing strategy.

        Parameters
        ----------
        strategy : RoutingStrategy
            The routing strategy.

        Returns
        -------
        int
            Maximum iterations for the strategy.
        """
        if strategy == RoutingStrategy.FASTPATH:
            return self._config.max_fastpath_iterations
        if strategy == RoutingStrategy.ENHANCED:
            return self._config.max_enhanced_iterations
        return self._config.max_orchestrated_iterations

    async def _create_session(
        self,
        task_description: str,
        complexity: TaskComplexity,
        metadata: dict[str, Any] | None = None,
    ) -> SessionContext:
        """Create a new session for task execution.

        Parameters
        ----------
        task_description : str
            The task description.
        complexity : TaskComplexity
            The complexity assessment result.
        metadata : dict[str, Any] | None, optional
            Additional session metadata.

        Returns
        -------
        SessionContext
            The newly created session.
        """
        from mozi.orchestrator.session.context import (
            ComplexityLevel as SessionComplexityLevel,
        )

        if metadata is None:
            metadata = {}

        metadata["task_description"] = task_description
        metadata["complexity_factors"] = complexity.factors

        # Convert complexity level to session context's enum type
        session_complexity_level = SessionComplexityLevel(complexity.level.value)

        return await self._session_manager.create_session(
            complexity_score=complexity.score,
            complexity_level=session_complexity_level,
            metadata=metadata,
        )

    async def _execute_fastpath(
        self,
        session: SessionContext,
        task: str,
        intent: IntentResult,
    ) -> AgentRuntimeResult:
        """Execute a task using FastPath strategy.

        FastPath is for SIMPLE tasks with direct single-agent execution.

        Parameters
        ----------
        session : SessionContext
            The session context.
        task : str
            The task description.
        intent : IntentResult
            The intent recognition result.

        Returns
        -------
        AgentRuntimeResult
            The execution result.
        """
        from mozi.orchestrator.agent.base import AgentConfig

        config = AgentConfig(
            name="fastpath_agent",
            max_iterations=self._config.max_fastpath_iterations,
            temperature=self._config.default_temperature,
            max_tokens=self._config.default_max_tokens,
        )

        return await self._agent_runtime.run(session, task, config)

    async def _execute_enhanced(
        self,
        session: SessionContext,
        task: str,
        intent: IntentResult,
    ) -> AgentRuntimeResult:
        """Execute a task using Enhanced strategy.

        Enhanced is for MEDIUM tasks with single-agent execution
        and enhanced monitoring.

        Parameters
        ----------
        session : SessionContext
            The session context.
        task : str
            The task description.
        intent : IntentResult
            The intent recognition result.

        Returns
        -------
        AgentRuntimeResult
            The execution result.
        """
        from mozi.orchestrator.agent.base import AgentConfig

        config = AgentConfig(
            name="enhanced_agent",
            max_iterations=self._config.max_enhanced_iterations,
            temperature=self._config.default_temperature,
            max_tokens=self._config.default_max_tokens,
        )

        return await self._agent_runtime.run(session, task, config)

    async def _execute_orchestrated(
        self,
        session: SessionContext,
        task: str,
        intent: IntentResult,
    ) -> AgentRuntimeResult:
        """Execute a task using Orchestrated strategy.

        Orchestrated is for COMPLEX tasks with multi-agent coordination.
        Currently delegates to single agent with extended iterations.

        Parameters
        ----------
        session : SessionContext
            The session context.
        task : str
            The task description.
        intent : IntentResult
            The intent recognition result.

        Returns
        -------
        AgentRuntimeResult
            The execution result.
        """
        from mozi.orchestrator.agent.base import AgentConfig

        config = AgentConfig(
            name="orchestrated_agent",
            max_iterations=self._config.max_orchestrated_iterations,
            temperature=self._config.default_temperature,
            max_tokens=self._config.default_max_tokens,
        )

        return await self._agent_runtime.run(session, task, config)

    async def execute(
        self,
        task_description: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OrchestratorResult:
        """Execute a task through the orchestrator pipeline.

        This method coordinates the full execution pipeline:
        1. Session creation/resumption
        2. Intent recognition
        3. Complexity assessment
        4. Task routing
        5. Agent execution

        Parameters
        ----------
        task_description : str
            Natural language description of the task to execute.
        session_id : str | None, optional
            Existing session ID to resume. Creates new session if not provided.
        metadata : dict[str, Any] | None, optional
            Additional metadata for the execution.

        Returns
        -------
        OrchestratorResult
            The result of the orchestrator execution.

        Raises
        ------
        OrchestratorError
            If execution fails at any stage.

        Examples
        --------
        Execute a simple task:

            result = await orchestrator.execute("Read the main.py file")
            print(result.content)

        Execute with existing session:

            result = await orchestrator.execute(
                "Continue editing",
                session_id="sess_abc123"
            )
        """
        start_time = datetime.now()

        try:
            # Step 1: Intent recognition first
            intent = recognize_intent(task_description)

            # Step 2: Route the task (includes complexity assessment)
            routing = self._task_router.route(task_description)

            # Step 3: Handle session
            if session_id:
                session = await self._session_manager.get_session(session_id)
            else:
                # Create new session using the routed complexity
                session = await self._create_session(
                    task_description=task_description,
                    complexity=routing.complexity,
                    metadata=metadata,
                )

            # Step 4: Execute based on strategy
            agent_result: AgentRuntimeResult | None = None

            if routing.strategy == RoutingStrategy.FASTPATH:
                agent_result = await self._execute_fastpath(
                    session, task_description, intent
                )
            elif routing.strategy == RoutingStrategy.ENHANCED:
                agent_result = await self._execute_enhanced(
                    session, task_description, intent
                )
            else:  # ORCHESTRATED
                agent_result = await self._execute_orchestrated(
                    session, task_description, intent
                )

            # Calculate execution time
            end_time = datetime.now()
            execution_time_ms = int(
                (end_time - start_time).total_seconds() * 1000
            )

            # Update session state
            if agent_result and agent_result.success:
                session.state = SessionState.COMPLETED
            else:
                session.state = SessionState.ERROR
            await self._session_manager.update_session(session)

            # Build and return result
            return OrchestratorResult(
                success=agent_result.success if agent_result else False,
                content=agent_result.content if agent_result else "",
                session_id=session.session_id,
                intent=intent,
                complexity=routing.complexity,
                routing=routing,
                agent_result=agent_result,
                error=agent_result.error if agent_result else None,
                execution_time_ms=execution_time_ms,
            )

        except Exception as e:
            end_time = datetime.now()
            execution_time_ms = int(
                (end_time - start_time).total_seconds() * 1000
            )

            raise OrchestratorError(
                f"Orchestrator execution failed: {e}",
                task_description=task_description,
                cause=e,
            ) from e

    async def execute_with_retry(
        self,
        task_description: str,
        max_retries: int = 3,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> OrchestratorResult:
        """Execute a task with automatic retry on failure.

        Parameters
        ----------
        task_description : str
            Natural language description of the task.
        max_retries : int, optional
            Maximum number of retry attempts. Defaults to 3.
        session_id : str | None, optional
            Existing session ID to resume.
        metadata : dict[str, Any] | None, optional
            Additional metadata for execution.

        Returns
        -------
        OrchestratorResult
            The result of the orchestrator execution.

        Raises
        ------
        OrchestratorError
            If all retry attempts fail.
        """
        last_result: OrchestratorResult | None = None

        for attempt in range(max_retries + 1):
            result = await self.execute(
                task_description=task_description,
                session_id=session_id,
                metadata=metadata,
            )

            if result.success:
                return result

            last_result = result
            if attempt < max_retries:
                # Could add exponential backoff here
                continue

        # All attempts failed
        error_msg = (
            f"All {max_retries + 1} attempts failed: "
            f"{last_result.error if last_result else 'Unknown error'}"
        )
        raise OrchestratorError(
            error_msg,
            task_description=task_description,
            cause=None,
        )

    def get_session_manager(self) -> SessionManager:
        """Get the session manager.

        Returns
        -------
        SessionManager
            The session manager instance.
        """
        return self._session_manager

    def get_complexity_assessor(self) -> ComplexityAssessor:
        """Get the complexity assessor.

        Returns
        -------
        ComplexityAssessor
            The complexity assessor instance.
        """
        return self._complexity_assessor

    def get_task_router(self) -> TaskRouter:
        """Get the task router.

        Returns
        -------
        TaskRouter
            The task router instance.
        """
        return self._task_router
