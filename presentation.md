# PawPal+ — Demo Day: The Engineer's Pitch

**Repo:** https://github.com/GODSONJ40/pawpal-ai-assistant

A ~6-minute pitch in the four required beats — **Problem → Logic → Reliability →
Reflection** — followed by demo notes and the portfolio paragraph.

---

## 1. The Problem — what did I solve? (~0:45)

- **Say:** "A busy pet owner has 35 free minutes and six things to do for their
  dog — a walk, feeding, and a medication. What gets done, and what gets safely
  dropped?"
- **Say:** "My Module 2 project, PawPal+, was a deterministic Streamlit scheduler
  (`Owner`, `Pet`, `Task`, `Scheduler`) that packed tasks into available time by
  priority. It worked — but it couldn't *reason* about trade-offs or warn me when
  the task it dropped was a medication."
- **Point:** PawPal+ now turns tasks + available time into a **safe, prioritized
  plan** and tells you **how confident** it is.

## 2. The Logic — how does the AI think? (~1:45)

**AI feature: an agentic loop grounded in verified code.**

- **Show:** `diagrams/architecture.mmd` (render at mermaid.live).
- **Say, tracing the flow:**
  - Input → **`validate_inputs()`** rejects bad data *before any AI call*.
  - API-key check → **live Claude agent**, or **deterministic fallback** offline.
  - **Agent loop:** *plan → act → check → revise → submit.* The agent's only tool
    is **`build_care_schedule`**, which runs the real `Scheduler` — so it can't
    hallucinate a plan.
  - The final answer is **re-grounded** in the scheduler, then scored.
- **Key line:** "The LLM reasons about *how* to plan, but it can never override what
  the deterministic scheduler says will *fit*. That's what makes it trustworthy."

## 3. The Reliability — how do I know it works? (~2:30)

**Live demo (reproducible, no API key needed):** `python demo.py --no-llm`

- **Scenario 1 — Comfortable day:** everything fits → **confidence 1.0**.
- **Scenario 2 — Tight budget (35 min):** agent triages — medication + walk kept,
  low-value tasks dropped → **confidence 0.6** + time-conflict flag.
- **Scenario 3 — Over-booked (20 min):** a **Vet Appointment can't fit** →
  **RISK FLAG** and **confidence crashes to 0.17**.
- **Guardrails:** show the two rejected inputs (empty task list; negative duration).

**Then show the tests:** `pytest` → **25 passed**.

- **Point to:** input validation, confidence scoring (priority-weighted coverage
  with health/conflict penalties), health-critical risk flags, a safety-refusal
  handler, and the deterministic fallback so it runs even offline.
- **Say:** "Reliability isn't a vibe here — it's a number and a test suite."

## 4. The Reflection — what surprised me? (~1:00)

- **Biggest surprise:** "The *safest* design gave the LLM **less** freedom, not
  more. Trust came from grounding every AI decision in verified, testable logic."
- **AI collaboration — one helpful, one flawed:**
  - *Helpful:* AI proposed grounding the agent in the scheduler as a **tool** —
    that pattern became the backbone of the system's trustworthiness.
  - *Flawed:* AI-generated `app.py` **imported** the agent but the button still
    called the old scheduler directly — the AI feature never actually ran in the
    UI. I caught it by tracing the real execution path and fixed the integration.
- **Close:** "PawPal+ is small, but it's a complete pattern for reliable AI: reason
  with the model, decide with verified code, measure your confidence, and never
  hide a risk. Full reflection is in `model_card.md`. Thank you — questions?"

---

## Demo backup / tips
- Rehearse `python demo.py --no-llm` once beforehand; it needs no API key and is
  identical every run.
- If the live agent (`python demo.py`) is slow or offline, the `--no-llm` output is
  your safety net and tells the same story.
- Keep `pytest` output and the rendered diagram on slides in case sharing a
  terminal fails.

## Likely Q&A
- **"What if the LLM is wrong?"** -> It can't set the schedule; the deterministic
  `Scheduler` decides what fits, and the plan is re-grounded in it. Worst case, the
  fallback runs.
- **"How is confidence computed?"** -> Priority-weighted coverage of scheduled
  tasks, x0.5 if a health-critical task is skipped, x0.9 on a time conflict.
- **"What are the limits?"** -> Keyword-based (English-only) health detection,
  greedy scheduling, single pet/day. Detailed in `model_card.md`.

---

## Portfolio Reflection Paragraph

*What this project says about me as an AI engineer:*

> PawPal+ shows that I build AI systems to be **trusted, not just impressive**. I
> took a working deterministic app and extended it into an agentic system without
> ever letting the model become the single point of failure — the LLM reasons about
> the plan, but a verified scheduler remains the source of truth for what actually
> fits, and every result carries a confidence score and explicit safety flags. I
> think in terms of guardrails, fallbacks, and reproducible tests: the system
> validates input before spending a token, degrades gracefully with no API key, and
> is covered by 25 automated tests. Just as important, I treat AI as a collaborator
> I verify rather than obey — I caught an AI-generated integration that looked
> correct but never actually ran, and I document both where the model helped and
> where it was wrong. That combination — pairing model reasoning with deterministic
> ground truth, measuring confidence, and staying honest about limitations — is the
> kind of responsible, production-minded engineering I want to be known for.
