# 🐾 PawPal+ Project Reflection

## 1. System Design
**a. Initial design**

My initial UML design included four main classes: Owner, Pet, Task, and Scheduler. The Owner class was responsible for storing the pet owner's name and available time for pet care. The Pet class represented individual pets and stored a list of care tasks associated with each pet. The Task class represented individual activities such as walking, feeding, or grooming, and included attributes like duration, priority, and whether the task was recurring. The Scheduler class was responsible for organizing tasks into an optimized daily plan based on constraints like available time and task priority.

Overall, the design followed a simple object-oriented structure where data is separated into clear entities and the Scheduler handles all decision-making logic.

**b. Design changes**

During implementation, I made a few adjustments to the original design. One key change was simplifying the relationship between Owner and Scheduler by having the Scheduler operate directly on the Owner and Pet objects rather than managing a separate global task system.

I also refined the Task model to include a numeric priority mapping (high, medium, low → values) to make sorting more efficient. This improved the scheduling logic by making it easier to prioritize tasks programmatically rather than relying on string comparisons.

## 2. Scheduling Logic and Tradeoffs
**a. Constraints and priorities**

The scheduler considers three main constraints:

Available time (maximum number of minutes per day)
Task priority (high tasks are scheduled before medium and low)
Task duration (to ensure tasks fit within remaining time)

Priority and available time were treated as the most important constraints because the main goal of the system is to ensure essential pet care tasks (like feeding and medication) are completed first. Time constraints ensure the schedule remains realistic and usable for a daily routine.

**b. Tradeoffs**

One major tradeoff is that the scheduler may skip lower-priority tasks if there is not enough available time. This means that not all tasks will always be completed in a given day.

This tradeoff is reasonable because in real-world pet care, essential tasks must take priority over optional activities. It is better to guarantee that high-priority care is completed than to attempt to fit every task into an unrealistic schedule.

## 3. AI Collaboration
**a. How you used AI**

I used AI throughout the project for multiple purposes, including designing the initial system architecture, generating UML diagrams, scaffolding Python class structures, debugging Streamlit integration issues, and creating test cases for scheduling logic.

The most helpful prompts were those that asked AI to explain design decisions, review my class structure for missing relationships, and help translate object-oriented design into working Python code.

**b. Judgment and verification**

One instance where I did not accept an AI suggestion was when it recommended simplifying the system by removing the Owner class and having the Scheduler operate directly on tasks. I chose not to follow this because it reduced the clarity of the object-oriented design and made the system less realistic.

I evaluated this by comparing both designs and reasoning about how a real pet care system would work. Keeping the Owner and Pet classes made the structure more natural and easier to extend later.

## 4. Testing and Verification
**a. What you tested**

I tested several key behaviors:

Adding and removing tasks from a pet
Sorting tasks based on priority
Ensuring tasks do not exceed available time
Skipping tasks when time runs out
Detecting when total task time exceeds available capacity
Generating a readable schedule explanation

These tests were important because they verify that the core scheduling logic behaves correctly under normal and edge-case conditions.

**b. Confidence**

I am confident that the scheduler works correctly for standard use cases, including prioritization, time constraints, and task ordering.

If I had more time, I would test additional edge cases such as:

Tasks with identical priority and duration
Extremely large numbers of tasks
Zero available time
Invalid or missing task inputs
Duplicate task entries

## 5. Reflection
**a. What went well**

I am most satisfied with how the scheduling system was implemented. The combination of priority sorting and time-based filtering produced a clean and logical daily plan that is easy to understand and explain.

**b. What you would improve**

If I had another iteration, I would improve the scheduling algorithm to support more advanced features such as time-slot scheduling (assigning specific start times), recurring tasks across multiple days, and smarter optimization instead of simple greedy selection.

I would also improve the Streamlit UI to allow editing and deleting tasks more easily instead of only adding them.

**c. Key takeaway**

One important thing I learned from this project is that designing the system structure first makes implementation significantly easier. I also learned that AI is most useful when it is used as a collaborative assistant rather than a replacement for decision-making, since human judgment is still needed to evaluate design tradeoffs and ensure correctness.

If you want, I can also do a final submission audit (README + tests + UML + code consistency) to make sure you get full credit with no surprises.
