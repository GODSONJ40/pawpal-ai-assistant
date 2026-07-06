import streamlit as st
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")

st.title("🐾 PawPal+")
st.write("Plan your pet's daily care schedule based on priorities and available time.")

# -------------------------
# Owner & Pet Information
# -------------------------
st.header("Owner & Pet Information")

owner_name = st.text_input("Owner Name", value="Jordan")
pet_name = st.text_input("Pet Name", value="Mochi")
species = st.selectbox("Species", ["Dog", "Cat", "Other"])
available_time = st.number_input(
    "Available Time (minutes)",
    min_value=15,
    max_value=480,
    value=90,
)

st.divider()

# -------------------------
# Task Input
# -------------------------
st.header("Add Pet Care Tasks")

if "tasks" not in st.session_state:
    st.session_state.tasks = []

col1, col2, col3 = st.columns(3)

with col1:
    task_title = st.text_input("Task Title", value="Morning Walk")

with col2:
    duration = st.number_input(
        "Duration (minutes)",
        min_value=1,
        max_value=240,
        value=20,
    )

with col3:
    priority = st.selectbox(
        "Priority",
        ["high", "medium", "low"],
    )

recurring = st.checkbox("Recurring Task")

if st.button("Add Task"):
    st.session_state.tasks.append(
        {
            "title": task_title,
            "duration": int(duration),
            "priority": priority,
            "recurring": recurring,
        }
    )
    st.success(f"Added '{task_title}'.")

if st.session_state.tasks:
    st.subheader("Current Tasks")
    st.table(st.session_state.tasks)
else:
    st.info("No tasks added yet.")

st.divider()

# -------------------------
# Generate Schedule
# -------------------------
st.header("Daily Schedule")

if st.button("Generate Schedule"):

    owner = Owner(
        name=owner_name,
        available_time=available_time,
    )

    pet = Pet(
        name=pet_name,
        species=species,
    )

    owner.add_pet(pet)

    for item in st.session_state.tasks:
        pet.add_task(
            Task(
                title=item["title"],
                duration_minutes=item["duration"],
                priority=item["priority"],
                recurring=item["recurring"],
            )
        )

    scheduler = Scheduler()

    result = scheduler.build_schedule(owner, pet)

    st.success("Schedule Generated!")

    st.subheader("Scheduled Tasks")

    if result["schedule"]:

        for task in result["schedule"]:

            st.markdown(
                f"✅ **{task.title}** "
                f"({task.duration_minutes} min) "
                f"- {task.priority.title()} Priority"
            )

    else:
        st.warning("No tasks could be scheduled.")

    if result["skipped"]:

        st.subheader("Skipped Tasks")

        for task in result["skipped"]:

            st.markdown(
                f"❌ {task.title} "
                f"({task.duration_minutes} min)"
            )

    st.subheader("Schedule Explanation")

    st.code(
        scheduler.explain_schedule(result),
        language="text",
    )

    st.metric(
        "Time Used",
        f"{result['time_used']} / {result['available_time']} min",
    )

    if result["conflicts"]:
        st.warning("Some tasks could not be scheduled due to limited available time.")
    else:
        st.success("All tasks fit within the available time.")