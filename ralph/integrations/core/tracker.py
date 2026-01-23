"""
Resource Tracking System for Ralph Integrations

Thread-safe singleton tracker for monitoring:
- API calls (endpoint, method, response_time_ms, status_code)
- LLM tokens (input_tokens, output_tokens, total_tokens, model)
- Costs (llm_cost_usd, api_cost_usd, total_cost_usd)
- Timing (start_time, end_time, duration_ms)
- Context (session_id, agent_name, phase, task_type)

Usage:
    from integrations.core.tracker import tracker

    # Start session
    tracker.start_session("research_123", "/path/to/state")
    tracker.set_context(phase="execution", agent="data_agent")

    # Record metrics (auto-recorded by http_wrapper)
    tracker.record_api_call(metric)

    # End session (saves to state/metrics.json)
    tracker.end_session()
"""

import time
import threading
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict


@dataclass
class APICallMetric:
    """Single API call measurement."""
    endpoint: str
    method: str
    module: str
    start_time: str
    end_time: str
    duration_ms: float
    status_code: int
    response_size_bytes: int = 0
    error: Optional[str] = None


@dataclass
class LLMCallMetric:
    """Single LLM call measurement."""
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    start_time: str
    end_time: str
    duration_ms: float
    agent_name: Optional[str] = None
    phase: Optional[str] = None
    task_type: Optional[str] = None


@dataclass
class SessionMetrics:
    """Aggregated session metrics."""
    session_id: str
    start_time: str
    end_time: Optional[str] = None
    total_duration_ms: float = 0

    # API metrics
    api_calls: List[Dict] = field(default_factory=list)
    api_calls_count: int = 0
    api_total_duration_ms: float = 0
    api_errors_count: int = 0

    # LLM metrics
    llm_calls: List[Dict] = field(default_factory=list)
    llm_calls_count: int = 0
    llm_total_input_tokens: int = 0
    llm_total_output_tokens: int = 0
    llm_total_tokens: int = 0
    llm_total_cost_usd: float = 0

    # Cost summary
    api_cost_usd: float = 0
    total_cost_usd: float = 0

    # Context
    current_phase: Optional[str] = None
    current_agent: Optional[str] = None
    task_type: Optional[str] = None


class ResourceTracker:
    """Thread-safe singleton resource tracker."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._metrics_lock = threading.Lock()
        self._session: Optional[SessionMetrics] = None
        self._state_dir: Optional[str] = None
        self._enabled = True
        self._start_timestamp: float = 0

    @property
    def enabled(self) -> bool:
        """Check if tracking is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool):
        """Enable or disable tracking."""
        self._enabled = value

    @property
    def is_active(self) -> bool:
        """Check if a session is currently active."""
        return self._session is not None

    def start_session(self, session_id: str, state_dir: str) -> None:
        """Initialize tracking for a research session.

        Args:
            session_id: Unique session identifier (e.g., research_20260122_wio_bank)
            state_dir: Path to state directory for saving metrics.json
        """
        with self._metrics_lock:
            self._session = SessionMetrics(
                session_id=session_id,
                start_time=datetime.utcnow().isoformat() + "Z"
            )
            self._state_dir = state_dir
            self._start_timestamp = time.time()

            # Ensure state directory exists
            if state_dir and not os.path.exists(state_dir):
                os.makedirs(state_dir, exist_ok=True)

    def end_session(self) -> Dict[str, Any]:
        """Finalize and save session metrics.

        Returns:
            Summary of session metrics
        """
        if not self._session:
            return {}

        with self._metrics_lock:
            self._session.end_time = datetime.utcnow().isoformat() + "Z"
            self._session.total_duration_ms = (time.time() - self._start_timestamp) * 1000
            self._session.total_cost_usd = (
                self._session.llm_total_cost_usd +
                self._session.api_cost_usd
            )

            # Save metrics
            self._save_metrics()

            # Get summary before clearing
            summary = self.get_summary()

            # Clear session
            session = self._session
            self._session = None
            self._state_dir = None

            return summary

    def set_context(self, phase: str = None, agent: str = None,
                    task_type: str = None) -> None:
        """Update current execution context.

        Args:
            phase: Current pipeline phase (e.g., execution, aggregation)
            agent: Current agent name (e.g., data_agent, research_agent)
            task_type: Current task type (e.g., d1, r2)
        """
        if not self._session:
            return
        with self._metrics_lock:
            if phase is not None:
                self._session.current_phase = phase
            if agent is not None:
                self._session.current_agent = agent
            if task_type is not None:
                self._session.task_type = task_type

    def record_api_call(self, metric: APICallMetric) -> None:
        """Record an API call metric.

        Args:
            metric: APICallMetric instance with call details
        """
        if not self._session or not self._enabled:
            return
        with self._metrics_lock:
            self._session.api_calls.append(asdict(metric))
            self._session.api_calls_count += 1
            self._session.api_total_duration_ms += metric.duration_ms
            if metric.error:
                self._session.api_errors_count += 1

    def record_llm_call(self, metric: LLMCallMetric) -> None:
        """Record an LLM call metric.

        Args:
            metric: LLMCallMetric instance with call details
        """
        if not self._session or not self._enabled:
            return
        with self._metrics_lock:
            # Add current context to metric
            metric_dict = asdict(metric)
            if not metric_dict.get("phase"):
                metric_dict["phase"] = self._session.current_phase
            if not metric_dict.get("agent_name"):
                metric_dict["agent_name"] = self._session.current_agent
            if not metric_dict.get("task_type"):
                metric_dict["task_type"] = self._session.task_type

            self._session.llm_calls.append(metric_dict)
            self._session.llm_calls_count += 1
            self._session.llm_total_input_tokens += metric.input_tokens
            self._session.llm_total_output_tokens += metric.output_tokens
            self._session.llm_total_tokens += metric.total_tokens
            self._session.llm_total_cost_usd += metric.cost_usd

    def add_api_cost(self, module: str, cost: float) -> None:
        """Add API cost for a module.

        Args:
            module: Module name (e.g., serper, dune)
            cost: Cost in USD
        """
        if not self._session or not self._enabled:
            return
        with self._metrics_lock:
            self._session.api_cost_usd += cost

    def _save_metrics(self) -> None:
        """Save metrics to state/metrics.json."""
        if not self._state_dir or not self._session:
            return

        metrics_path = os.path.join(self._state_dir, "metrics.json")

        # Build metrics dict
        metrics = asdict(self._session)

        # Add summary
        metrics["summary"] = self._build_summary()

        # Write atomically using temp file
        temp_path = metrics_path + ".tmp"
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(metrics, f, indent=2, default=str, ensure_ascii=False)
            # Atomic rename
            if os.path.exists(metrics_path):
                os.remove(metrics_path)
            os.rename(temp_path, metrics_path)
        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise

    def _build_summary(self) -> Dict[str, Any]:
        """Build summary breakdown by module, phase, and agent."""
        if not self._session:
            return {}

        by_module: Dict[str, Dict] = {}
        by_phase: Dict[str, Dict] = {}
        by_agent: Dict[str, Dict] = {}

        # Aggregate API calls by module
        for call in self._session.api_calls:
            module = call.get("module", "unknown")
            if module not in by_module:
                by_module[module] = {"calls": 0, "duration_ms": 0, "errors": 0}
            by_module[module]["calls"] += 1
            by_module[module]["duration_ms"] += call.get("duration_ms", 0)
            if call.get("error"):
                by_module[module]["errors"] += 1

        # Aggregate LLM calls by phase and agent
        for call in self._session.llm_calls:
            phase = call.get("phase", "unknown")
            agent = call.get("agent_name", "unknown")

            if phase not in by_phase:
                by_phase[phase] = {"llm_calls": 0, "tokens": 0, "cost_usd": 0}
            by_phase[phase]["llm_calls"] += 1
            by_phase[phase]["tokens"] += call.get("total_tokens", 0)
            by_phase[phase]["cost_usd"] += call.get("cost_usd", 0)

            if agent not in by_agent:
                by_agent[agent] = {"calls": 0, "tokens": 0, "cost_usd": 0}
            by_agent[agent]["calls"] += 1
            by_agent[agent]["tokens"] += call.get("total_tokens", 0)
            by_agent[agent]["cost_usd"] += call.get("cost_usd", 0)

        return {
            "by_module": by_module,
            "by_phase": by_phase,
            "by_agent": by_agent,
        }

    def get_summary(self) -> Dict[str, Any]:
        """Get current metrics summary.

        Returns:
            Summary dictionary with key metrics
        """
        if not self._session:
            return {}
        with self._metrics_lock:
            return {
                "session_id": self._session.session_id,
                "api_calls": self._session.api_calls_count,
                "api_errors": self._session.api_errors_count,
                "api_duration_ms": round(self._session.api_total_duration_ms, 2),
                "llm_calls": self._session.llm_calls_count,
                "llm_tokens": self._session.llm_total_tokens,
                "llm_cost_usd": round(self._session.llm_total_cost_usd, 6),
                "api_cost_usd": round(self._session.api_cost_usd, 6),
                "total_cost_usd": round(
                    self._session.llm_total_cost_usd + self._session.api_cost_usd,
                    6
                ),
            }

    def get_current_context(self) -> Dict[str, Optional[str]]:
        """Get current execution context.

        Returns:
            Dictionary with phase, agent, and task_type
        """
        if not self._session:
            return {"phase": None, "agent": None, "task_type": None}
        with self._metrics_lock:
            return {
                "phase": self._session.current_phase,
                "agent": self._session.current_agent,
                "task_type": self._session.task_type,
            }


# Global tracker instance
tracker = ResourceTracker()
