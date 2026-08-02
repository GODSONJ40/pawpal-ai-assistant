"""
pawpal_agent.py — Agentic AI Care Planner for PawPal+.

This is the AI feature that extends the original PawPal+ prototype into a full
applied-AI system. It wraps the deterministic ``Scheduler`` (pawpal_system.py)
in an **agentic workflow** powered by Claude:

    PLAN  -> ACT (build_care_schedule)  -> CHECK (inspect skipped/conflicts)
          -> REVISE (adjust & re-run)   -> SUBMIT (final plan)

The agent decides *how* to schedule; the deterministic Scheduler remains the
source of truth for *what actually fits*. On top of the loop the module adds the
three supporting reliability features the project requires:

    * Confidence scoring   -> compute_confidence()
    * Logging              -> logs/pawpal_agent.log  +  ai_interactions.md trace
    * Guardrails           -> validate_inputs(), MissingAPIKeyError, refusal &
                              iteration caps, and a deterministic fallback plan.

The code is written so the deterministic pieces (tools, confidence, guardrails)
run and test *without* any network call; only the live agent loop needs an
``ANTHROPIC_API_KEY``.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from pawpal_system import Owner, Pet, Task, Scheduler

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Default to the latest, most capable Claude model. Override with the
# PAWPAL_MODEL env var (e.g. "claude-sonnet-5" or "claude-haiku-4-5") if you
# want cheaper/faster runs for grading.
DEFAULT_MODEL = os.environ.get("PAWPAL_MODEL", "claude-opus-5")

MAX_ITERATIONS = 6  # guardrail: hard cap on agent loop turns
MAX_TOKENS = 4096

PROJECT_ROOT = Path(__file__).resolve().parent
LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "pawpal_agent.log"
INTERACTIONS_FILE = PROJECT_ROOT / "ai_interactions.md"

PRIORITY_WEIGHT = {"high": 3, "medium": 2, "low": 1}

# Titles containing any of these are treated as health-critical when high
# priority — skipping them should crush confidence and raise a risk flag.
HEALTH_KEYWORDS = (
    "medication",
    "medicine",
    "meds",
    "insulin",
    "pill",
    "injection",
    "dose",
    "vet",
    "appointment",
)


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _build_logger() -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger("pawpal_agent")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(fmt)
        logger.addHandler(stream_handler)
    return logger


logger = _build_logger()


# ---------------------------------------------------------------------------
# Errors & result type
# ---------------------------------------------------------------------------

class MissingAPIKeyError(RuntimeError):
    """Raised when the live agent is invoked with no ANTHROPIC_API_KEY set."""


@dataclass
class CarePlanResult:
    scheduled: List[str]
    skipped: List[str]
    explanation: str
    health_risk_flags: List[str]
    confidence: float
    confidence_reasons: List[str]
    time_used: int
    available_time: int
    conflicts: bool
    iterations: int
    used_llm: bool
    model: str
    trace: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scheduled": self.scheduled,
            "skipped": self.skipped,
            "explanation": self.explanation,
            "health_risk_flags": self.health_risk_flags,
            "confidence": self.confidence,
            "confidence_reasons": self.confidence_reasons,
            "time_used": self.time_used,
            "available_time": self.available_time,
            "conflicts": self.conflicts,
            "iterations": self.iterations,
            "used_llm": self.used_llm,
            "model": self.model,
        }


# ---------------------------------------------------------------------------
# Guardrails — input validation (pure, testable, no network)
# ---------------------------------------------------------------------------

def validate_inputs(available_time: int, tasks: List[Dict[str, Any]]) -> None:
    """Reject malformed input before any AI call. Raises ValueError."""
    if not isinstance(available_time, int) or isinstance(available_time, bool):
        raise ValueError("available_time must be an integer number of minutes.")
    if available_time <= 0:
        raise ValueError("available_time must be greater than 0 minutes.")
    if not tasks:
        raise ValueError("At least one task is required to build a plan.")
    for i, task in enumerate(tasks):
        title = str(task.get("title", "")).strip()
        if not title:
            raise ValueError(f"Task #{i + 1} is missing a title.")
        duration = task.get("duration_minutes")
        if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
            raise ValueError(f"Task '{title}' needs a positive integer duration_minutes.")
        priority = str(task.get("priority", "")).lower()
        if priority not in PRIORITY_WEIGHT:
            raise ValueError(
                f"Task '{title}' has invalid priority '{priority}' "
                "(expected high/medium/low)."
            )


def health_critical(task: Dict[str, Any]) -> bool:
    """A high-priority task whose title reads like medical/appointment care."""
    if str(task.get("priority", "")).lower() != "high":
        return False
    title = str(task.get("title", "")).lower()
    return any(keyword in title for keyword in HEALTH_KEYWORDS)


# ---------------------------------------------------------------------------
# Tool implementation — the agent's grounding in the real Scheduler
# ---------------------------------------------------------------------------

def run_scheduler(available_time: int, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Run the deterministic Scheduler and return a JSON-serializable result.

    This is the body of the ``build_care_schedule`` tool. Keeping it pure means
    the agent's actions are always grounded in the verified Module 1-3 logic.
    """
    owner = Owner(name="Owner", available_time=int(available_time))
    pet = Pet(name="Pet", species="Pet")
    for task in tasks:
        pet.add_task(
            Task(
                title=str(task["title"]),
                duration_minutes=int(task["duration_minutes"]),
                priority=str(task["priority"]),
                recurring=bool(task.get("recurring", False)),
            )
        )
    owner.add_pet(pet)
    result = Scheduler().build_schedule(owner, pet)
    return {
        "scheduled": [t.title for t in result["schedule"]],
        "skipped": [t.title for t in result["skipped"]],
        "time_used": result["time_used"],
        "available_time": result["available_time"],
        "conflicts": result["conflicts"],
    }


# ---------------------------------------------------------------------------
# Confidence scoring (pure, testable, no network)
# ---------------------------------------------------------------------------

def compute_confidence(
    schedule_result: Dict[str, Any], tasks: List[Dict[str, Any]]
) -> tuple[float, List[str]]:
    """Score 0.0-1.0 for how trustworthy/complete the produced plan is.

    Priority-weighted coverage, with heavy penalties for skipped health-critical
    tasks and a smaller penalty when not everything fits.
    """
    if not tasks:
        return 0.0, ["No tasks were provided."]

    scheduled = set(schedule_result.get("scheduled", []))
    total_weight = sum(PRIORITY_WEIGHT.get(str(t["priority"]).lower(), 1) for t in tasks)
    got_weight = sum(
        PRIORITY_WEIGHT.get(str(t["priority"]).lower(), 1)
        for t in tasks
        if t["title"] in scheduled
    )
    coverage = got_weight / total_weight if total_weight else 0.0
    reasons = [f"Priority-weighted coverage: {got_weight}/{total_weight} = {coverage:.2f}"]
    score = coverage

    skipped_health = [
        t["title"] for t in tasks if t["title"] not in scheduled and health_critical(t)
    ]
    if skipped_health:
        score *= 0.5
        reasons.append("Health-critical task(s) skipped: " + ", ".join(skipped_health))

    if schedule_result.get("conflicts"):
        score *= 0.9
        reasons.append("Not every task fit in the available time (time conflict).")

    if not skipped_health and not schedule_result.get("conflicts"):
        reasons.append("All tasks scheduled with no conflicts.")

    score = round(max(0.0, min(1.0, score)), 2)
    return score, reasons


def _risk_flags(schedule_result: Dict[str, Any], tasks: List[Dict[str, Any]]) -> List[str]:
    scheduled = set(schedule_result.get("scheduled", []))
    flags: List[str] = []
    for t in tasks:
        if t["title"] not in scheduled and health_critical(t):
            flags.append(f"Health-critical task skipped: '{t['title']}'")
    if schedule_result.get("conflicts"):
        flags.append("Available time is too short for all tasks.")
    return flags


# ---------------------------------------------------------------------------
# Deterministic fallback — a safe baseline plan with no AI (guardrail)
# ---------------------------------------------------------------------------

def deterministic_plan(available_time: int, tasks: List[Dict[str, Any]]) -> CarePlanResult:
    """Produce a plan using only the Scheduler — used as a fallback when the
    LLM is unavailable, and as a reproducible baseline for tests."""
    validate_inputs(available_time, tasks)
    result = run_scheduler(available_time, tasks)
    confidence, reasons = compute_confidence(result, tasks)
    flags = _risk_flags(result, tasks)
    explanation = (
        f"Baseline plan (no AI): scheduled {len(result['scheduled'])} of {len(tasks)} "
        f"tasks by priority then duration, using {result['time_used']}/"
        f"{result['available_time']} minutes."
    )
    return CarePlanResult(
        scheduled=result["scheduled"],
        skipped=result["skipped"],
        explanation=explanation,
        health_risk_flags=flags,
        confidence=confidence,
        confidence_reasons=reasons,
        time_used=result["time_used"],
        available_time=result["available_time"],
        conflicts=result["conflicts"],
        iterations=0,
        used_llm=False,
        model="none",
        trace=[{"step": "deterministic_fallback", "result": result}],
    )


# ---------------------------------------------------------------------------
# Tool schemas for the Claude agent loop
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "name": "build_care_schedule",
        "description": (
            "Run the verified PawPal+ scheduler on a set of tasks and an available "
            "time budget. Returns which tasks fit (scheduled), which do not "
            "(skipped), total time used, and whether there was a time conflict. "
            "Call this to test a scheduling decision before committing to it."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "available_time": {
                    "type": "integer",
                    "description": "Minutes the owner has available today.",
                },
                "tasks": {
                    "type": "array",
                    "description": "The pet-care tasks to schedule.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "duration_minutes": {"type": "integer"},
                            "priority": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                            },
                            "recurring": {"type": "boolean"},
                        },
                        "required": ["title", "duration_minutes", "priority"],
                    },
                },
            },
            "required": ["available_time", "tasks"],
        },
    },
    {
        "name": "submit_care_plan",
        "description": (
            "Submit the FINAL daily care plan once you are confident it is safe "
            "and optimal. Call this exactly once to finish."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "ordered_tasks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Task titles in the recommended order of the day.",
                },
                "explanation": {
                    "type": "string",
                    "description": "Plain-language explanation of the plan and trade-offs.",
                },
                "health_risk_flags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Any health/safety concerns (e.g. a skipped medication).",
                },
            },
            "required": ["ordered_tasks", "explanation"],
        },
    },
]

SYSTEM_PROMPT = """You are the PawPal+ Care Planner, an agent that builds a safe, \
optimized daily schedule for a pet owner.

Work in a loop:
1. PLAN: think about the tasks, their priorities, durations, and the time budget.
2. ACT: call `build_care_schedule` to test a scheduling decision.
3. CHECK: inspect the result. Did a high-priority or medical task get skipped? \
Is there a time conflict?
4. REVISE: if the plan is unsafe or suboptimal, reason about a better approach and \
call `build_care_schedule` again to test it.
5. SUBMIT: when the plan is as safe and complete as the time budget allows, call \
`submit_care_plan` exactly once.

Safety rules:
- Never silently drop a health-critical task (medication, injections, vet \
appointments). If one cannot fit, say so explicitly in health_risk_flags.
- The scheduler is the source of truth for what fits — always ground your final \
plan in a `build_care_schedule` result.
- Be concise in your explanation."""


# ---------------------------------------------------------------------------
# Interaction trace (agentic reasoning log -> ai_interactions.md)
# ---------------------------------------------------------------------------

def _append_interaction_trace(header: str, trace: List[Dict[str, Any]]) -> None:
    try:
        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
        lines = [f"\n### {header} ({stamp})\n"]
        for step in trace:
            lines.append(f"- **{step.get('step', 'step')}**: "
                         f"{json.dumps(step, default=str)[:500]}")
        with INTERACTIONS_FILE.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")
    except OSError as exc:  # logging must never crash the plan
        logger.warning("Could not write interaction trace: %s", exc)


# ---------------------------------------------------------------------------
# The agent
# ---------------------------------------------------------------------------

class CarePlannerAgent:
    """Runs the Claude-powered plan/act/check/revise loop over the Scheduler."""

    def __init__(self, client: Any = None, model: str = DEFAULT_MODEL):
        self._client = client  # injectable for tests; created lazily otherwise
        self.model = model

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise MissingAPIKeyError(
                "ANTHROPIC_API_KEY is not set. Export your key (or run the "
                "deterministic fallback) before using the live agent."
            )
        import anthropic  # imported lazily so offline tests need no dependency

        self._client = anthropic.Anthropic()
        return self._client

    def plan(self, available_time: int, tasks: List[Dict[str, Any]]) -> CarePlanResult:
        # Guardrail: validate before spending a single token.
        validate_inputs(available_time, tasks)
        logger.info("Planning for %d min, %d task(s), model=%s",
                    available_time, len(tasks), self.model)

        client = self._get_client()
        messages: List[Dict[str, Any]] = [
            {
                "role": "user",
                "content": (
                    "Build the daily care plan.\n"
                    f"Available time: {available_time} minutes.\n"
                    f"Tasks: {json.dumps(tasks)}"
                ),
            }
        ]
        trace: List[Dict[str, Any]] = []
        submitted: Optional[Dict[str, Any]] = None
        iterations = 0

        while iterations < MAX_ITERATIONS:
            iterations += 1
            response = client.messages.create(
                model=self.model,
                max_tokens=MAX_TOKENS,
                system=SYSTEM_PROMPT,
                tools=TOOLS,
                messages=messages,
            )

            # Guardrail: handle a safety refusal instead of crashing.
            if response.stop_reason == "refusal":
                logger.warning("Model refused the request; using fallback.")
                trace.append({"step": "refusal", "iteration": iterations})
                fallback = deterministic_plan(available_time, tasks)
                fallback.trace = trace + fallback.trace
                fallback.iterations = iterations
                _append_interaction_trace("Care plan (refusal fallback)", fallback.trace)
                return fallback

            tool_uses = [b for b in response.content if getattr(b, "type", None) == "tool_use"]
            texts = [b.text for b in response.content if getattr(b, "type", None) == "text"]
            if texts:
                trace.append({"step": "reasoning", "iteration": iterations,
                              "text": " ".join(texts)[:800]})

            if not tool_uses:
                # Model stopped without submitting — fall back gracefully.
                logger.info("No tool call this turn (stop_reason=%s).", response.stop_reason)
                break

            # Append the assistant turn (preserves thinking/tool_use blocks).
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for tool in tool_uses:
                if tool.name == "submit_care_plan":
                    submitted = tool.input
                    trace.append({"step": "submit", "iteration": iterations,
                                  "input": tool.input})
                    break  # finished
                if tool.name == "build_care_schedule":
                    try:
                        result = run_scheduler(
                            tool.input["available_time"], tool.input["tasks"]
                        )
                    except (KeyError, ValueError, TypeError) as exc:
                        result = {"error": str(exc)}
                    trace.append({"step": "build_care_schedule", "iteration": iterations,
                                  "result": result})
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool.id,
                        "content": json.dumps(result),
                    })

            if submitted is not None:
                break
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

        # Ground the final answer in the deterministic scheduler (source of truth).
        final_schedule = run_scheduler(available_time, tasks)
        confidence, reasons = compute_confidence(final_schedule, tasks)
        flags = _risk_flags(final_schedule, tasks)

        if submitted is not None:
            explanation = submitted.get("explanation", "").strip() or \
                "Plan produced by the PawPal+ agent."
            # Merge any model-reported risks with our deterministic checks.
            for flag in submitted.get("health_risk_flags", []) or []:
                if flag not in flags:
                    flags.append(flag)
            ordered = [t for t in submitted.get("ordered_tasks", [])
                       if t in final_schedule["scheduled"]]
            # Keep any scheduled tasks the model forgot to order.
            for t in final_schedule["scheduled"]:
                if t not in ordered:
                    ordered.append(t)
            scheduled = ordered or final_schedule["scheduled"]
        else:
            logger.info("Agent did not submit; using deterministic explanation.")
            explanation = (
                "The agent did not submit a final plan, so PawPal+ returned the "
                "verified scheduler result as a safe baseline."
            )
            scheduled = final_schedule["scheduled"]

        result = CarePlanResult(
            scheduled=scheduled,
            skipped=final_schedule["skipped"],
            explanation=explanation,
            health_risk_flags=flags,
            confidence=confidence,
            confidence_reasons=reasons,
            time_used=final_schedule["time_used"],
            available_time=final_schedule["available_time"],
            conflicts=final_schedule["conflicts"],
            iterations=iterations,
            used_llm=True,
            model=self.model,
            trace=trace,
        )
        logger.info("Plan complete: confidence=%.2f, iterations=%d, flags=%d",
                    result.confidence, iterations, len(flags))
        _append_interaction_trace("Care plan (agentic)", trace)
        return result


def plan_care(
    available_time: int,
    tasks: List[Dict[str, Any]],
    *,
    allow_fallback: bool = True,
    client: Any = None,
    model: str = DEFAULT_MODEL,
) -> CarePlanResult:
    """Convenience entry point used by the CLI demo and the Streamlit app.

    If the live agent cannot run (no API key) and ``allow_fallback`` is True,
    returns the deterministic baseline plan instead of raising.
    """
    agent = CarePlannerAgent(client=client, model=model)
    try:
        return agent.plan(available_time, tasks)
    except MissingAPIKeyError:
        if not allow_fallback:
            raise
        logger.warning("No API key — returning deterministic fallback plan.")
        return deterministic_plan(available_time, tasks)
