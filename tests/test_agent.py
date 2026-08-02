"""
Tests for the agentic Care Planner (pawpal_agent.py).

These run fully offline: the deterministic pieces need no network, and the
agent-loop test injects a fake Claude client, so `pytest` is reproducible with
no ANTHROPIC_API_KEY.
"""

import json
from types import SimpleNamespace

import pytest

from pawpal_agent import (
    CarePlannerAgent,
    compute_confidence,
    deterministic_plan,
    health_critical,
    run_scheduler,
    validate_inputs,
)

# ---------------------------------------------------------------------------
# Sample data
# ---------------------------------------------------------------------------

TASKS = [
    {"title": "Give Medication", "duration_minutes": 5, "priority": "high"},
    {"title": "Morning Walk", "duration_minutes": 30, "priority": "high"},
    {"title": "Play Fetch", "duration_minutes": 20, "priority": "medium"},
    {"title": "Brush Coat", "duration_minutes": 15, "priority": "low"},
]


# ---------------------------------------------------------------------------
# Guardrails: validate_inputs
# ---------------------------------------------------------------------------

def test_validate_inputs_accepts_valid():
    validate_inputs(60, TASKS)  # should not raise


def test_validate_inputs_rejects_empty_tasks():
    with pytest.raises(ValueError):
        validate_inputs(60, [])


def test_validate_inputs_rejects_nonpositive_time():
    with pytest.raises(ValueError):
        validate_inputs(0, TASKS)


def test_validate_inputs_rejects_negative_duration():
    with pytest.raises(ValueError):
        validate_inputs(60, [{"title": "Walk", "duration_minutes": -5, "priority": "high"}])


def test_validate_inputs_rejects_bad_priority():
    with pytest.raises(ValueError):
        validate_inputs(60, [{"title": "Walk", "duration_minutes": 10, "priority": "urgent"}])


def test_validate_inputs_rejects_empty_title():
    with pytest.raises(ValueError):
        validate_inputs(60, [{"title": "  ", "duration_minutes": 10, "priority": "low"}])


# ---------------------------------------------------------------------------
# Tool wrapper: run_scheduler matches Scheduler behavior
# ---------------------------------------------------------------------------

def test_run_scheduler_fits_all_when_time_ample():
    result = run_scheduler(120, TASKS)
    assert set(result["scheduled"]) == {t["title"] for t in TASKS}
    assert result["skipped"] == []
    assert result["conflicts"] is False


def test_run_scheduler_skips_when_over_budget():
    result = run_scheduler(35, TASKS)
    assert result["conflicts"] is True
    # High-priority med + walk fit first (5 + 30 = 35); lower priorities skipped.
    assert "Give Medication" in result["scheduled"]
    assert "Brush Coat" in result["skipped"]


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------

def test_confidence_perfect_when_all_scheduled():
    result = run_scheduler(120, TASKS)
    score, reasons = compute_confidence(result, TASKS)
    assert score == 1.0
    assert any("no conflicts" in r.lower() for r in reasons)


def test_confidence_drops_when_health_task_skipped():
    tasks = [
        {"title": "Vet Appointment", "duration_minutes": 30, "priority": "high"},
        {"title": "Feed Dinner", "duration_minutes": 10, "priority": "high"},
    ]
    result = run_scheduler(20, tasks)  # vet (30) can't fit in 20 min
    score, reasons = compute_confidence(result, tasks)
    assert "Vet Appointment" in result["skipped"]
    assert score < 0.6
    assert any("health-critical" in r.lower() for r in reasons)


def test_confidence_zero_for_no_tasks():
    score, _ = compute_confidence({"scheduled": []}, [])
    assert score == 0.0


def test_health_critical_detection():
    assert health_critical({"title": "Give Medication", "priority": "high"})
    assert health_critical({"title": "Vet Appointment", "priority": "high"})
    assert not health_critical({"title": "Play Fetch", "priority": "high"})
    assert not health_critical({"title": "Give Medication", "priority": "low"})


# ---------------------------------------------------------------------------
# Deterministic fallback plan
# ---------------------------------------------------------------------------

def test_deterministic_plan_offline():
    result = deterministic_plan(120, TASKS)
    assert result.used_llm is False
    assert result.confidence == 1.0
    assert set(result.scheduled) == {t["title"] for t in TASKS}


# ---------------------------------------------------------------------------
# Full agent loop with a FAKE client (no network)
# ---------------------------------------------------------------------------

def _block(**kwargs):
    """Build a fake content block that mimics an Anthropic SDK block object."""
    return SimpleNamespace(**kwargs)


class FakeMessages:
    """Returns a scripted sequence of responses, one per .create() call."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return self._responses.pop(0)


class FakeClient:
    def __init__(self, responses):
        self.messages = FakeMessages(responses)


def test_agent_loop_act_then_submit():
    """Agent calls build_care_schedule, then submits — grounded in the Scheduler."""
    responses = [
        # Turn 1: reason + call build_care_schedule
        SimpleNamespace(
            stop_reason="tool_use",
            content=[
                _block(type="text", text="Let me test the schedule."),
                _block(
                    type="tool_use",
                    id="tool_1",
                    name="build_care_schedule",
                    input={"available_time": 120, "tasks": TASKS},
                ),
            ],
        ),
        # Turn 2: submit the final plan
        SimpleNamespace(
            stop_reason="tool_use",
            content=[
                _block(
                    type="tool_use",
                    id="tool_2",
                    name="submit_care_plan",
                    input={
                        "ordered_tasks": [
                            "Give Medication", "Morning Walk", "Play Fetch", "Brush Coat",
                        ],
                        "explanation": "All tasks fit; medication first for safety.",
                        "health_risk_flags": [],
                    },
                ),
            ],
        ),
    ]
    agent = CarePlannerAgent(client=FakeClient(responses), model="fake-model")
    result = agent.plan(120, TASKS)

    assert result.used_llm is True
    assert result.iterations == 2
    assert result.confidence == 1.0
    assert result.scheduled[0] == "Give Medication"
    assert "medication first" in result.explanation.lower()
    # The build_care_schedule tool result was fed back before submit.
    assert len(agent._client.messages.calls) == 2


def test_agent_refusal_falls_back():
    """A safety refusal returns the deterministic baseline instead of crashing."""
    responses = [SimpleNamespace(stop_reason="refusal", content=[])]
    agent = CarePlannerAgent(client=FakeClient(responses), model="fake-model")
    result = agent.plan(120, TASKS)
    assert result.used_llm is False  # fell back
    assert set(result.scheduled) == {t["title"] for t in TASKS}
