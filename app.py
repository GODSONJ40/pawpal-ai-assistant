import os

import streamlit as st

from pawpal_agent import plan_care

st.set_page_config(
    page_title="PawPal+ — Pet care planner",
    page_icon=":material/pets:",
    layout="wide",
)

# Priority label -> inline badge color.
PRIORITY_BADGE = {"high": "red", "medium": "orange", "low": "gray"}

# Accent color (matches the config.toml coral by default). The picker recolors
# the primary accent live; presets and a reset control drive it via session_state.
DEFAULT_ACCENT = "#E2542A"
ACCENT_PRESETS = {
    "Coral": "#E2542A",
    "Amber": "#F59E0B",
    "Rose": "#E11D48",
    "Violet": "#8B5CF6",
    "Indigo": "#6366F1",
    "Emerald": "#10B981",
    "Sky": "#0EA5E9",
}


def _apply_accent_preset():
    choice = st.session_state.get("accent_preset")
    if choice in ACCENT_PRESETS:
        st.session_state["accent_color"] = ACCENT_PRESETS[choice]


def _reset_accent():
    st.session_state["accent_color"] = DEFAULT_ACCENT
    st.session_state["accent_preset"] = "Coral"


if "tasks" not in st.session_state:
    st.session_state.tasks = []
st.session_state.setdefault("accent_color", DEFAULT_ACCENT)
st.session_state.setdefault("accent_preset", "Coral")

# ---------------------------------------------------------------------------
# Sidebar — owner/pet context and planner engine status
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header(":material/pets: PawPal+")
    st.caption("Smart daily care planning for your pet.")

    st.subheader("Owner & pet")
    owner_name = st.text_input("Owner name", value="Jordan")
    pet_name = st.text_input("Pet name", value="Mochi")
    species = st.selectbox("Species", ["Dog", "Cat", "Other"])
    available_time = st.number_input(
        "Available time (minutes)",
        min_value=15,
        max_value=480,
        value=90,
        step=5,
    )

    st.subheader("Planner engine")
    # The agent uses the live Claude loop only when an API key is present;
    # otherwise it falls back to the deterministic scheduler.
    if os.environ.get("ANTHROPIC_API_KEY"):
        st.badge("AI agent active", icon=":material/smart_toy:", color="green")
        st.caption("Live Claude agent: plan → act → check → revise.")
    else:
        st.badge("Deterministic fallback", icon=":material/calculate:", color="orange")
        st.caption("No API key set — safe baseline planner, no AI.")

    st.subheader("Appearance")
    # Quick presets set the picker; the picker allows any color at will; the
    # reset control snaps back to the config.toml theme default.
    st.pills(
        "Accent presets",
        list(ACCENT_PRESETS),
        key="accent_preset",
        on_change=_apply_accent_preset,
        label_visibility="collapsed",
    )
    st.color_picker(
        "Accent color",
        key="accent_color",
        help="Recolors buttons and links live. Pick any color you like.",
    )
    st.button(
        "Reset to theme default",
        icon=":material/restart_alt:",
        on_click=_reset_accent,
        type="tertiary",
    )

# Apply the user-chosen accent color at runtime. The base theme comes from
# .streamlit/config.toml; this small CSS override lets the user recolor the
# primary accent (buttons, links) live from the sidebar.
accent = st.session_state["accent_color"]
st.html(
    f"""
    <style>
    :root {{ --primary-color: {accent}; }}
    .stButton button[kind="primary"],
    .stFormSubmitButton button[kind="primary"],
    button[data-testid="stBaseButton-primary"],
    button[data-testid="stBaseButton-primaryFormSubmit"] {{
        background-color: {accent};
        border-color: {accent};
    }}
    [data-testid="stMarkdownContainer"] a {{ color: {accent}; }}
    </style>
    """
)

# ---------------------------------------------------------------------------
# Main — task builder and daily schedule
# ---------------------------------------------------------------------------
st.title("Daily care planner")
st.caption(f"Plan {pet_name or 'your pet'}'s day by priority within the available time.")

add_col, list_col = st.columns(2, gap="large")

# ---- Add a task ----
with add_col:
    with st.container(border=True):
        st.subheader("Add a task")
        with st.form("add_task", clear_on_submit=True, border=False):
            title = st.text_input("Task title", value="Morning walk")
            field1, field2 = st.columns(2)
            duration = field1.number_input(
                "Duration (minutes)", min_value=1, max_value=240, value=20, step=5
            )
            priority = field2.selectbox("Priority", ["high", "medium", "low"])
            recurring = st.checkbox("Recurring task")
            submitted = st.form_submit_button(
                "Add task", icon=":material/add:", type="primary"
            )
        if submitted:
            if title.strip():
                st.session_state.tasks.append(
                    {
                        "title": title.strip(),
                        "duration": int(duration),
                        "priority": priority,
                        "recurring": recurring,
                    }
                )
                st.toast(f"Added “{title.strip()}”.", icon=":material/check:")
            else:
                st.warning("Give the task a title first.")

# ---- Current tasks ----
with list_col:
    with st.container(border=True):
        st.subheader("Current tasks")
        if not st.session_state.tasks:
            st.caption("No tasks yet — add one on the left.")
        else:
            head = st.columns([4, 2, 3, 1], vertical_alignment="center")
            head[0].markdown("**Task**")
            head[1].markdown("**Duration**")
            head[2].markdown("**Priority**")
            head[3].markdown("**Remove**")

            for i, item in enumerate(st.session_state.tasks):
                row = st.columns([4, 2, 3, 1], vertical_alignment="center")
                row[0].write(item["title"])
                if item.get("recurring"):
                    row[0].caption(":material/repeat: Recurring")
                row[1].write(f"{item['duration']} min")
                color = PRIORITY_BADGE.get(item["priority"], "gray")
                row[2].markdown(f":{color}-badge[{item['priority'].title()}]")
                if row[3].button(
                    "", icon=":material/delete:", key=f"del_{i}",
                    help=f"Remove '{item['title']}'", type="tertiary",
                ):
                    st.session_state.tasks.pop(i)
                    st.rerun()

            if st.button("Clear all", icon=":material/delete_sweep:", key="clear_all"):
                st.session_state.tasks = []
                st.rerun()

# ---- Daily schedule ----
st.subheader("Daily schedule")

generate = st.button(
    "Generate schedule",
    icon=":material/bolt:",
    type="primary",
    disabled=not st.session_state.tasks,
)
if not st.session_state.tasks:
    st.caption("Add at least one task to generate a schedule.")

if generate:
    # Map the UI task shape onto the keys the agent/guardrails expect.
    agent_tasks = [
        {
            "title": item["title"],
            "duration_minutes": int(item["duration"]),
            "priority": item["priority"],
            "recurring": item.get("recurring", False),
        }
        for item in st.session_state.tasks
    ]

    # Guardrail: invalid input is rejected before any AI call.
    try:
        with st.spinner("Planning the day…"):
            result = plan_care(int(available_time), agent_tasks)
    except ValueError as exc:
        st.error(f"Could not build a plan: {exc}", icon=":material/error:")
        st.stop()

    engine = f"Claude agent ({result.model})" if result.used_llm else "deterministic fallback"
    st.success(f"Schedule generated by the {engine}.", icon=":material/check_circle:")

    # KPI cards
    conf = result.confidence
    conf_color = "green" if conf >= 0.8 else "orange" if conf >= 0.5 else "red"
    kpi1, kpi2, kpi3 = st.columns(3)
    kpi1.metric("Confidence", f"{conf:.2f}", border=True)
    kpi2.metric("Agent turns", result.iterations, border=True)
    kpi3.metric(
        "Time used", f"{result.time_used} / {result.available_time} min", border=True
    )
    st.markdown(f"Confidence rating: :{conf_color}-badge[{conf:.2f}]")

    if result.health_risk_flags:
        st.error(
            "**Health risk flags**\n\n"
            + "\n".join(f"- {flag}" for flag in result.health_risk_flags),
            icon=":material/warning:",
        )

    sched_col, skip_col = st.columns(2, gap="large")
    with sched_col:
        with st.container(border=True):
            st.markdown("**Scheduled**")
            if result.scheduled:
                for title in result.scheduled:
                    st.markdown(f":material/check_circle: {title}")
            else:
                st.caption("Nothing could be scheduled.")
    with skip_col:
        with st.container(border=True):
            st.markdown("**Skipped**")
            if result.skipped:
                for title in result.skipped:
                    st.markdown(f":material/cancel: {title}")
            else:
                st.caption("Nothing skipped — everything fit.")

    with st.container(border=True):
        st.markdown("**AI explanation**")
        st.write(result.explanation)

    with st.expander("Why this confidence score?", icon=":material/query_stats:"):
        for reason in result.confidence_reasons:
            st.markdown(f"- {reason}")

    if result.conflicts:
        st.warning(
            "Some tasks couldn't fit in the available time.", icon=":material/schedule:"
        )
    else:
        st.success("All tasks fit within the available time.", icon=":material/task_alt:")
