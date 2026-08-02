"""
demo.py — CLI-first demo for the PawPal+ agentic Care Planner.

Runs the agent on three sample scenarios and prints reproducible execution
evidence (inputs, outputs, confidence, guardrail behavior). Paste this output
into README.md as the graded execution evidence.

Usage:
    python demo.py                # live agent if ANTHROPIC_API_KEY is set,
                                  # otherwise deterministic fallback
    python demo.py --no-llm       # force the deterministic baseline (offline)
"""

from __future__ import annotations

import argparse
import os

from pawpal_agent import CarePlannerAgent, deterministic_plan, plan_care, validate_inputs

SCENARIOS = [
    {
        "name": "1. Comfortable day (everything fits)",
        "available_time": 120,
        "tasks": [
            {"title": "Morning Walk", "duration_minutes": 30, "priority": "high"},
            {"title": "Give Medication", "duration_minutes": 5, "priority": "high"},
            {"title": "Feed Breakfast", "duration_minutes": 10, "priority": "high"},
            {"title": "Play Fetch", "duration_minutes": 20, "priority": "medium"},
            {"title": "Brush Coat", "duration_minutes": 15, "priority": "low"},
        ],
    },
    {
        "name": "2. Tight budget (agent must triage)",
        "available_time": 35,
        "tasks": [
            {"title": "Give Medication", "duration_minutes": 5, "priority": "high"},
            {"title": "Morning Walk", "duration_minutes": 30, "priority": "high"},
            {"title": "Play Fetch", "duration_minutes": 20, "priority": "medium"},
            {"title": "Brush Coat", "duration_minutes": 15, "priority": "low"},
        ],
    },
    {
        "name": "3. Over-booked (health task at risk)",
        "available_time": 20,
        "tasks": [
            {"title": "Long Training Session", "duration_minutes": 25, "priority": "medium"},
            {"title": "Vet Appointment", "duration_minutes": 30, "priority": "high"},
            {"title": "Feed Dinner", "duration_minutes": 10, "priority": "high"},
        ],
    },
]


def print_result(result) -> None:
    print(f"    Engine        : {'Claude agent (' + result.model + ')' if result.used_llm else 'deterministic fallback'}")
    print(f"    Agent turns   : {result.iterations}")
    print(f"    Scheduled     : {', '.join(result.scheduled) or '(none)'}")
    print(f"    Skipped       : {', '.join(result.skipped) or '(none)'}")
    print(f"    Time used     : {result.time_used}/{result.available_time} min")
    print(f"    Confidence    : {result.confidence}")
    for reason in result.confidence_reasons:
        print(f"        - {reason}")
    if result.health_risk_flags:
        print("    RISK FLAGS    :")
        for flag in result.health_risk_flags:
            print(f"        ! {flag}")
    print(f"    Explanation   : {result.explanation}")


def run_scenarios(force_offline: bool) -> None:
    live = bool(os.environ.get("ANTHROPIC_API_KEY")) and not force_offline
    banner = "LIVE CLAUDE AGENT" if live else "DETERMINISTIC FALLBACK (no API key / --no-llm)"
    print("=" * 70)
    print(f"PawPal+ Care Planner - {banner}")
    print("=" * 70)

    for scenario in SCENARIOS:
        print(f"\n>>> Scenario {scenario['name']}")
        print(f"    Available time: {scenario['available_time']} min")
        print(f"    Tasks: {[t['title'] for t in scenario['tasks']]}")
        if force_offline:
            result = deterministic_plan(scenario["available_time"], scenario["tasks"])
        else:
            result = plan_care(scenario["available_time"], scenario["tasks"])
        print_result(result)

    # Guardrail demonstration: malformed input is rejected before any AI call.
    print("\n>>> Guardrail check: empty task list")
    try:
        validate_inputs(60, [])
    except ValueError as exc:
        print(f"    Rejected as expected: {exc}")

    print("\n>>> Guardrail check: negative duration")
    try:
        validate_inputs(60, [{"title": "Walk", "duration_minutes": -5, "priority": "high"}])
    except ValueError as exc:
        print(f"    Rejected as expected: {exc}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PawPal+ Care Planner demo")
    parser.add_argument("--no-llm", action="store_true",
                        help="Force the deterministic baseline (no API calls).")
    args = parser.parse_args()
    run_scenarios(force_offline=args.no_llm)
