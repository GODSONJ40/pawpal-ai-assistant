from dataclasses import dataclass, field
from typing import List


PRIORITY_VALUES = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


@dataclass
class Task:
    title: str
    duration_minutes: int
    priority: str
    recurring: bool = False
    completed: bool = False

    def mark_complete(self):
        self.completed = True

    @property
    def priority_value(self):
        return PRIORITY_VALUES.get(self.priority.lower(), 0)


@dataclass
class Pet:
    name: str
    species: str
    tasks: List[Task] = field(default_factory=list)

    def add_task(self, task: Task):
        self.tasks.append(task)

    def remove_task(self, title: str):
        self.tasks = [task for task in self.tasks if task.title != title]

    def get_tasks(self):
        return self.tasks


@dataclass
class Owner:
    name: str
    available_time: int = 60
    pets: List[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet):
        self.pets.append(pet)

    def get_pets(self):
        return self.pets


class Scheduler:
    """
    Schedules pet care tasks based on:
    - Priority
    - Duration
    - Available time
    """

    def sort_tasks(self, tasks: List[Task]) -> List[Task]:
        return sorted(
            tasks,
            key=lambda task: (-task.priority_value, task.duration_minutes)
        )

    def detect_conflicts(self, tasks: List[Task], available_time: int):
        total = sum(task.duration_minutes for task in tasks)
        return total > available_time

    def build_schedule(self, owner: Owner, pet: Pet):
        available = owner.available_time

        sorted_tasks = self.sort_tasks(pet.get_tasks())

        schedule = []
        skipped = []
        time_used = 0

        for task in sorted_tasks:
            if time_used + task.duration_minutes <= available:
                schedule.append(task)
                time_used += task.duration_minutes
            else:
                skipped.append(task)

        return {
            "pet": pet.name,
            "owner": owner.name,
            "schedule": schedule,
            "skipped": skipped,
            "time_used": time_used,
            "available_time": available,
            "conflicts": self.detect_conflicts(
                pet.get_tasks(),
                available
            )
        }

    def explain_schedule(self, result):
        lines = []

        lines.append(
            f"Daily Plan for {result['pet']}"
        )

        lines.append(
            f"Available Time: {result['available_time']} minutes\n"
        )

        for task in result["schedule"]:
            lines.append(
                f"• {task.title} ({task.duration_minutes} min) "
                f"[{task.priority.title()}]"
            )

        if result["skipped"]:
            lines.append("\nSkipped Tasks:")

            for task in result["skipped"]:
                lines.append(
                    f"- {task.title} "
                    f"(Not enough available time)"
                )

        lines.append(
            f"\nTime Used: {result['time_used']}/"
            f"{result['available_time']} minutes"
        )

        if result["conflicts"]:
            lines.append(
                "Warning: Not every task could be scheduled."
            )
        else:
            lines.append(
                "All tasks were successfully scheduled."
            )

        return "\n".join(lines)