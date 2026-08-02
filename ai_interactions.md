# AI Interactions Log

> **Stretch features only.** Only fill in the sections that apply to stretch features you attempted. If you did not attempt a stretch feature, leave its section blank or delete it. This file is not required for the core project.

---

## Agent Workflow (SF7)

> Document your experience using an AI agent (e.g., Cursor Agent, Claude, Copilot) to make multi-step changes autonomously.

**What task did you give the agent?**

<!-- Describe the goal you asked the agent to accomplish -->

**What did the agent do?**

<!-- List the steps the agent took (files edited, commands run, etc.) -->

**What did you have to verify or fix manually?**

<!-- Describe anything the agent got wrong or that required human review -->

---

## Prompt Comparison (SF11)

> Compare two different prompts (or two different models) on the same task.

| | Option A | Option B |
|-|----------|----------|
| **Model / tool used** | | |
| **Prompt** | | |
| **Response summary** | | |
| **What was useful** | | |
| **Problems noticed** | | |
| **Decision** | | |

**Which approach did you use in your final implementation and why?**

<!-- Your conclusion -->

### Care plan (agentic) (2026-08-02 01:08:43Z)

- **reasoning**: {"step": "reasoning", "iteration": 1, "text": "Let me test the schedule."}
- **build_care_schedule**: {"step": "build_care_schedule", "iteration": 1, "result": {"scheduled": ["Give Medication", "Morning Walk", "Play Fetch", "Brush Coat"], "skipped": [], "time_used": 70, "available_time": 120, "conflicts": false}}
- **submit**: {"step": "submit", "iteration": 2, "input": {"ordered_tasks": ["Give Medication", "Morning Walk", "Play Fetch", "Brush Coat"], "explanation": "All tasks fit; medication first for safety.", "health_risk_flags": []}}

### Care plan (refusal fallback) (2026-08-02 01:08:43Z)

- **refusal**: {"step": "refusal", "iteration": 1}
- **deterministic_fallback**: {"step": "deterministic_fallback", "result": {"scheduled": ["Give Medication", "Morning Walk", "Play Fetch", "Brush Coat"], "skipped": [], "time_used": 70, "available_time": 120, "conflicts": false}}

### Care plan (agentic) (2026-08-02 01:47:55Z)

- **reasoning**: {"step": "reasoning", "iteration": 1, "text": "Let me test the schedule."}
- **build_care_schedule**: {"step": "build_care_schedule", "iteration": 1, "result": {"scheduled": ["Give Medication", "Morning Walk", "Play Fetch", "Brush Coat"], "skipped": [], "time_used": 70, "available_time": 120, "conflicts": false}}
- **submit**: {"step": "submit", "iteration": 2, "input": {"ordered_tasks": ["Give Medication", "Morning Walk", "Play Fetch", "Brush Coat"], "explanation": "All tasks fit; medication first for safety.", "health_risk_flags": []}}

### Care plan (refusal fallback) (2026-08-02 01:47:55Z)

- **refusal**: {"step": "refusal", "iteration": 1}
- **deterministic_fallback**: {"step": "deterministic_fallback", "result": {"scheduled": ["Give Medication", "Morning Walk", "Play Fetch", "Brush Coat"], "skipped": [], "time_used": 70, "available_time": 120, "conflicts": false}}
