"""
Plan Executor for Zenith AI
Multi-step execution engine with safe execution layer, intermediate result
chaining, and graceful failure handling.
"""
from __future__ import annotations

import inspect
import time
from typing import Any, Optional

import structlog

from tools.calendar import CalendarTools
from tools.gmail import GmailTools
from tools.tasks import TasksTools
from tools.notes import NotesTools

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Safe-execution policy — actions that require user confirmation
# ---------------------------------------------------------------------------

# Actions considered "write" operations
WRITE_ACTIONS: set[str] = {
    "calendar.create_event",
    "calendar.quick_add",
    "calendar.update_event",
    "calendar.delete_event",
    "gmail.send_email",
    "tasks.add_task",
    "tasks.complete_task",
    "tasks.complete_task_by_title",
    "tasks.update_task",
    "tasks.set_reminder",
    "notes.save_note",
    "notes.delete_note",
    "notes.delete_note_by_query",
}

# Thresholds that bump risk to "high" and force confirmation
HIGH_RISK_RULES: list[dict] = [
    {
        "action": "gmail.send_email",
        "condition": lambda params: len(params.get("to", [])) > 3,
        "message": "This email will be sent to {count} recipients.",
    },
    {
        "action": "calendar.create_event",
        "condition": lambda params: len(params.get("attendees", [])) > 5,
        "message": "This meeting will notify {count} attendees.",
    },
]


def _assess_risk(steps: list[dict]) -> tuple[str, Optional[str]]:
    """
    Assess execution risk based on actions and parameters.

    Returns:
        (risk_level, confirmation_message | None)
        risk_level is one of: "low", "medium", "high"
    """
    has_write = any(s.get("action") in WRITE_ACTIONS for s in steps)
    if not has_write:
        return "low", None

    for rule in HIGH_RISK_RULES:
        for step in steps:
            if step.get("action") == rule["action"]:
                params = step.get("params", {})
                if rule["condition"](params):
                    recipients = params.get("to", params.get("attendees", []))
                    msg = rule["message"].format(count=len(recipients))
                    return "high", msg

    return "medium", None


class StepResult:
    """Encapsulates the outcome of a single execution step."""

    __slots__ = ("action", "success", "data", "error", "latency_ms")

    def __init__(
        self,
        action: str,
        success: bool,
        data: Any = None,
        error: Optional[str] = None,
        latency_ms: float = 0.0,
    ):
        self.action = action
        self.success = success
        self.data = data
        self.error = error
        self.latency_ms = latency_ms

    def to_dict(self) -> dict:
        d: dict[str, Any] = {
            "action": self.action,
            "success": self.success,
            "latency_ms": round(self.latency_ms, 1),
        }
        if self.success:
            d["data"] = self.data
        else:
            d["error"] = self.error
        return d


class PlanExecutor:
    """
    Multi-step plan execution engine.

    Responsibilities:
    - Iterate through planned steps sequentially
    - Call the correct tool method with resolved parameters
    - Store intermediate results for step chaining
    - Handle failures gracefully (partial results are preserved)
    - Enforce the safe-execution layer
    """

    def __init__(self):
        self.calendar = CalendarTools()
        self.gmail = GmailTools()
        self.tasks = TasksTools()
        self.notes = NotesTools()

        self._tool_map: dict[str, Any] = {
            "calendar": self.calendar,
            "gmail": self.gmail,
            "tasks": self.tasks,
            "notes": self.notes,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute_plan(
        self,
        plan: dict,
        credentials: dict,
        user_id: str,
        skip_confirmation: bool = False,
    ) -> dict:
        """
        Execute a structured plan produced by the Planner/Decomposer.

        Args:
            plan: Plan dict with "steps" list.
            credentials: Google OAuth credentials.
            user_id: Authenticated user id.
            skip_confirmation: If True, bypass safe-execution checks (used
                after user has already confirmed).

        Returns:
            Execution result dict with keys:
            - success (bool)
            - step_results (list[dict])
            - error (str | None)
            - requires_confirmation (bool)
            - confirmation_message (str | None)
            - risk_level (str)
            - total_latency_ms (float)
        """
        steps = plan.get("steps", [])
        if not steps:
            return {
                "success": True,
                "step_results": [],
                "error": None,
                "requires_confirmation": False,
                "confirmation_message": None,
                "risk_level": "low",
                "total_latency_ms": 0.0,
            }

        # --- Safe-execution check ---
        risk_level, confirmation_msg = _assess_risk(steps)

        has_write = any(s.get("action") in WRITE_ACTIONS for s in steps)
        if has_write and not skip_confirmation:
            return {
                "success": True,
                "step_results": [],
                "error": None,
                "requires_confirmation": True,
                "confirmation_message": confirmation_msg,
                "risk_level": risk_level,
                "pending_confirmation": True,
                "pending_steps": steps,
                "total_latency_ms": 0.0,
            }

        # --- Execute steps sequentially ---
        step_results: list[StepResult] = []
        overall_success = True
        overall_error: Optional[str] = None
        total_start = time.monotonic()

        for i, step in enumerate(steps):
            action = step.get("action", "")
            params = dict(step.get("params", {}))

            t0 = time.monotonic()
            try:
                data = await self._execute_step(
                    action=action,
                    params=params,
                    credentials=credentials,
                    user_id=user_id,
                    previous_results=step_results,
                )
                elapsed = (time.monotonic() - t0) * 1000
                step_results.append(
                    StepResult(action=action, success=True, data=data, latency_ms=elapsed)
                )
            except Exception as exc:
                elapsed = (time.monotonic() - t0) * 1000
                logger.error(
                    "step_execution_failed",
                    step_index=i,
                    action=action,
                    error=str(exc),
                )
                step_results.append(
                    StepResult(
                        action=action,
                        success=False,
                        error=str(exc),
                        latency_ms=elapsed,
                    )
                )
                overall_success = False
                overall_error = str(exc)
                break  # Stop on first failure

        total_latency = (time.monotonic() - total_start) * 1000

        return {
            "success": overall_success,
            "step_results": [r.to_dict() for r in step_results],
            "error": overall_error,
            "requires_confirmation": False,
            "confirmation_message": None,
            "risk_level": risk_level,
            "total_latency_ms": round(total_latency, 1),
        }

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _execute_step(
        self,
        action: str,
        params: dict,
        credentials: dict,
        user_id: str,
        previous_results: list[StepResult],
    ) -> Any:
        """Execute a single step, injecting credentials/user_id as needed."""
        if "." not in action:
            raise ValueError(f"Invalid action format (expected 'tool.method'): {action}")

        tool_name, method_name = action.split(".", 1)
        tool = self._tool_map.get(tool_name)
        if tool is None:
            raise ValueError(f"Unknown tool: {tool_name}")

        method = getattr(tool, method_name, None)
        if method is None:
            raise ValueError(f"Unknown method '{method_name}' on tool '{tool_name}'")

        # Inject credentials / user_id based on tool type
        if tool_name == "notes":
            call_params = dict(params)
            sig = inspect.signature(method)
            if "credentials" in sig.parameters and "credentials" not in call_params:
                call_params["credentials"] = credentials
            return await method(user_id=user_id, **call_params)
        else:
            return await method(credentials=credentials, **params)
