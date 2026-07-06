import pytest

from pawpal_system import Owner, Pet, Task, Scheduler


def create_sample_pet():
    pet = Pet(name="Mochi", species="Dog")

    pet.add_task(Task("Feed Breakfast", 10, "high"))
    pet.add_task(Task("Morning Walk", 30, "high"))
    pet.add_task(Task("Play Fetch", 20, "medium"))
    pet.add_task(Task("Brush Coat", 15, "low"))

    return pet


def test_add_task():
    pet = Pet(name="Buddy", species="Dog")

    pet.add_task(Task("Walk", 20, "high"))

    assert len(pet.tasks) == 1
    assert pet.tasks[0].title == "Walk"


def test_tasks_sorted_by_priority():
    scheduler = Scheduler()

    tasks = [
        Task("Low Task", 10, "low"),
        Task("High Task", 20, "high"),
        Task("Medium Task", 15, "medium"),
    ]

    sorted_tasks = scheduler.sort_tasks(tasks)

    assert sorted_tasks[0].priority == "high"
    assert sorted_tasks[1].priority == "medium"
    assert sorted_tasks[2].priority == "low"


def test_schedule_respects_available_time():
    owner = Owner(name="Jordan", available_time=40)
    pet = create_sample_pet()

    scheduler = Scheduler()

    result = scheduler.build_schedule(owner, pet)

    assert result["time_used"] <= owner.available_time


def test_skips_tasks_when_time_runs_out():
    owner = Owner(name="Jordan", available_time=25)
    pet = create_sample_pet()

    scheduler = Scheduler()

    result = scheduler.build_schedule(owner, pet)

    assert len(result["skipped"]) > 0


def test_conflict_detection():
    scheduler = Scheduler()

    tasks = [
        Task("Walk", 30, "high"),
        Task("Play", 30, "medium"),
        Task("Feed", 20, "high"),
    ]

    assert scheduler.detect_conflicts(tasks, 60) is True
    assert scheduler.detect_conflicts(tasks, 100) is False


def test_schedule_contains_high_priority_tasks_first():
    owner = Owner(name="Jordan", available_time=60)
    pet = create_sample_pet()

    scheduler = Scheduler()

    result = scheduler.build_schedule(owner, pet)

    priorities = [task.priority for task in result["schedule"]]

    assert priorities[0] == "high"


def test_mark_complete():
    task = Task("Medication", 5, "high")

    assert task.completed is False

    task.mark_complete()

    assert task.completed is True


def test_remove_task():
    pet = Pet(name="Mochi", species="Dog")

    pet.add_task(Task("Walk", 20, "high"))
    pet.add_task(Task("Feed", 10, "high"))

    pet.remove_task("Walk")

    assert len(pet.tasks) == 1
    assert pet.tasks[0].title == "Feed"


def test_get_tasks():
    pet = create_sample_pet()

    tasks = pet.get_tasks()

    assert len(tasks) == 4


def test_schedule_explanation():
    owner = Owner(name="Jordan", available_time=90)
    pet = create_sample_pet()

    scheduler = Scheduler()

    result = scheduler.build_schedule(owner, pet)

    explanation = scheduler.explain_schedule(result)

    assert "Daily Plan" in explanation
    assert pet.name in explanation