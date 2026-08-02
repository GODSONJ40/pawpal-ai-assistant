# 🐾 PawPal+ — Model Card & Responsible-AI Reflection

**System:** PawPal+ Agentic Care Planner — an LLM agent that builds a safe,
prioritized daily pet-care plan, with every decision grounded in a deterministic
scheduler (`pawpal_system.py`).

**Intended use:** Help a pet owner decide which care tasks to do today given
limited time, and surface when something important (e.g. medication) won't fit.
It is a **scheduling aid, not veterinary or medical advice.**

---

## 1. Limitations and Biases

- **Keyword-based health detection is brittle and English-only.** "Health-critical"
  tasks are recognized by matching a fixed word list (`HEALTH_KEYWORDS`:
  *medication, insulin, vet, injection, dose, …*). A task titled "give Rex his
  shot", a misspelling, or a non-English title would **not** be flagged, so a
  genuinely critical task could be skipped without penalty. This biases the safety
  net toward owners who phrase tasks in standard medical vocabulary.
- **Greedy scheduling favors many short tasks over one important long task.** The
  scheduler sorts by priority then *shortest duration* and packs until time runs
  out. Among equal-priority tasks, a 30-minute vet visit loses to several short
  tasks — visible in Scenario 3, where the high-priority **Vet Appointment (30 min)
  is skipped** while shorter tasks are kept.
- **Confidence is a heuristic, not a calibrated probability.** It is
  priority-weighted coverage with fixed multipliers (×0.5 for a skipped health
  task, ×0.9 for a time conflict). It communicates *relative* trust, not a literal
  accuracy percentage.
- **LLM non-determinism.** The live agent may order or explain a plan differently
  across runs. This is bounded by re-grounding the final answer in the
  deterministic scheduler, but wording and task ordering can still vary.
- **Narrow scope.** One owner, one pet, a single day, no specific time-of-day
  slotting or multi-day recurrence.

## 2. Potential for Misuse and Mitigations

- **Risk — treated as medical advice.** An owner could over-read the output
  ("the app scheduled around the medication, so skipping it must be fine").
  *Mitigations:* health-critical tasks are **never silently dropped** — they raise
  explicit `health_risk_flags`, and skipping one multiplies confidence by 0.5 so
  the score drops sharply (0.17 in Scenario 3). The system prompt forbids silently
  dropping medical tasks, and the UI/README state this is not medical advice.
- **Risk — over-trust in an AI plan.** *Mitigations:* every plan is grounded in the
  deterministic scheduler (the LLM cannot invent what "fits"), the engine
  (live agent vs. fallback) and confidence are shown to the user, and inputs are
  validated before any AI call.
- **Prevention going forward:** keep a visible "not medical advice" disclaimer,
  never let a high confidence number hide a skipped health task, and expand health
  detection beyond a static keyword list before relying on it in production.

## 3. What Surprised Me While Testing Reliability

- **The trust came from the deterministic core, not the LLM.** Because the agent is
  forced to schedule through the `build_care_schedule` tool, the "AI" and the
  offline fallback produce the same schedule shape. The safest design gave the LLM
  *less* freedom, not more.
- **Compounding confidence penalties are very legible.** Stacking ×0.5 and ×0.9
  drove Scenario 3 to 0.17 — a clear early-warning signal that the day is
  over-booked and a health task is at risk, which was more useful than expected.
- **A test had a hidden side effect.** Running `pytest` was mutating the tracked
  `ai_interactions.md`, because the trace writer used a real file path. That was a
  reproducibility lesson in itself — fixed with a fixture that redirects the trace
  file to a temp path so the suite is side-effect free.

## 4. AI Collaboration: Helpful vs. Flawed Suggestions

- **Helpful suggestion — ground the agent in the deterministic scheduler.** AI
  proposed an "agent plans, verified logic decides" pattern: expose the existing
  `Scheduler` as a `build_care_schedule` tool so the LLM's plan is always checked
  against real logic instead of hallucinated. This became the backbone of the
  system's trustworthiness and its offline fallback.
- **Flawed suggestion — an integration that only looked wired up.** AI-generated
  `app.py` *imported* `plan_care` but the "Generate Schedule" button still called
  the old `Scheduler` directly — so the AI feature never actually ran in the UI,
  even though the architecture diagram claimed it did. I caught this by tracing the
  actual execution path, then routed the button through `plan_care()` and surfaced
  the confidence score and risk flags. **Lesson:** verify that generated code is on
  the real execution path, not merely imported.

---

## Appendix — Original Module 2 Design & Testing Notes

*(Preserved from the base PawPal+ prototype for context on the system's evolution.)*

### System Design

My initial UML design included four main classes: Owner, Pet, Task, and Scheduler.
The Owner class stored the pet owner's name and available time. The Pet class
represented individual pets and their list of care tasks. The Task class
represented activities such as walking, feeding, or grooming, with attributes like
duration, priority, and recurring. The Scheduler organized tasks into an optimized
daily plan based on available time and priority.

During implementation I simplified the Owner–Scheduler relationship by having the
Scheduler operate directly on the Owner and Pet objects, and refined the Task model
to use a numeric priority mapping (high/medium/low → values) for efficient sorting.

### Scheduling Logic and Trade-offs

The scheduler considers available time, task priority (high before medium/low), and
task duration. Priority and available time were treated as the most important
constraints so essential care (feeding, medication) is completed first. The main
trade-off: lower-priority tasks may be skipped when time is short — reasonable
because essential care should take precedence over optional activities.

### Testing and Verification

The scheduler suite covers adding/removing tasks, priority sorting, respecting
available time, skipping tasks when time runs out, conflict detection, and readable
schedule explanations. The agent suite (added in the final project) covers input
guardrails, scheduler grounding, confidence scoring, health-critical detection, the
deterministic fallback, and the agent loop plus refusal fallback — 25 tests total,
all passing offline.
