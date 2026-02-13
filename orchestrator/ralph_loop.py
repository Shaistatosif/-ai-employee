"""
Ralph Wiggum Loop - Multi-Step Task Persistence for Personal AI Employee System.

Manages multi-step tasks that persist across system restarts.
Each task is a sequence of steps that can be paused, resumed,
and require approval at specific points.

Named after the "I'm in danger" meme - because multi-step tasks
are always in danger of being interrupted.
"""

import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

from config import settings
from config.database import log_action

logger = logging.getLogger(__name__)


@dataclass
class TaskStep:
    """A single step in a multi-step task."""
    name: str
    action: str  # action type (e.g., "email_send", "linkedin_draft", "general")
    requires_approval: bool = False
    status: str = "pending"  # pending | completed | failed
    result: Optional[dict] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "action": self.action,
            "requires_approval": self.requires_approval,
            "status": self.status,
            "result": self.result,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskStep":
        return cls(
            name=data["name"],
            action=data["action"],
            requires_approval=data.get("requires_approval", False),
            status=data.get("status", "pending"),
            result=data.get("result"),
        )


@dataclass
class MultiStepTask:
    """A multi-step task with persistence."""
    id: str
    title: str
    steps: list[TaskStep]
    current_step: int = 0
    status: str = "pending"  # pending | in_progress | paused | completed | failed
    created: str = ""
    updated: str = ""

    def __post_init__(self):
        if not self.created:
            self.created = datetime.now().isoformat()
        if not self.updated:
            self.updated = datetime.now().isoformat()

    @property
    def state_file(self) -> Path:
        """Path to the persisted state file."""
        return settings.multistep_path / f"{self.id}.yaml"

    @property
    def current_step_obj(self) -> Optional[TaskStep]:
        """Get the current step object."""
        if 0 <= self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    @property
    def progress(self) -> str:
        """Get progress string."""
        completed = sum(1 for s in self.steps if s.status == "completed")
        return f"{completed}/{len(self.steps)}"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "steps": [s.to_dict() for s in self.steps],
            "current_step": self.current_step,
            "status": self.status,
            "created": self.created,
            "updated": self.updated,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MultiStepTask":
        steps = [TaskStep.from_dict(s) for s in data.get("steps", [])]
        return cls(
            id=data["id"],
            title=data["title"],
            steps=steps,
            current_step=data.get("current_step", 0),
            status=data.get("status", "pending"),
            created=data.get("created", ""),
            updated=data.get("updated", ""),
        )


class RalphWiggumLoop:
    """
    Manages multi-step tasks with persistence.

    Features:
    - Create multi-step tasks with ordered steps
    - Persist task state to YAML files
    - Resume incomplete tasks on startup
    - Handle approval requirements per step
    - Track progress and results
    """

    def __init__(self):
        self._tasks: dict[str, MultiStepTask] = {}
        settings.multistep_path.mkdir(parents=True, exist_ok=True)

    def create_task(self, title: str, steps: list[dict]) -> MultiStepTask:
        """
        Create a new multi-step task.

        Args:
            title: Task title
            steps: List of step dicts with keys: name, action, requires_approval

        Returns:
            The created MultiStepTask
        """
        task_id = f"ms_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"

        task_steps = [
            TaskStep(
                name=s["name"],
                action=s.get("action", "general"),
                requires_approval=s.get("requires_approval", False),
            )
            for s in steps
        ]

        task = MultiStepTask(
            id=task_id,
            title=title,
            steps=task_steps,
            status="pending",
        )

        self._tasks[task_id] = task
        self._persist_state(task)

        log_action(
            action_type="multistep_created",
            target=task_id,
            parameters={"title": title, "step_count": len(steps)},
            result="success",
        )

        logger.info(f"Multi-step task created: {task_id} ({title}, {len(steps)} steps)")
        return task

    def resume_all(self) -> int:
        """
        On startup, scan state_dir and resume incomplete tasks.

        Returns:
            Number of tasks resumed
        """
        resumed = 0

        try:
            for state_file in settings.multistep_path.glob("*.yaml"):
                try:
                    content = state_file.read_text(encoding="utf-8")
                    data = yaml.safe_load(content)
                    if not data:
                        continue

                    task = MultiStepTask.from_dict(data)

                    # Only resume tasks that were in progress
                    if task.status in ("pending", "in_progress", "paused"):
                        self._tasks[task.id] = task
                        resumed += 1
                        logger.info(
                            f"Resumed multi-step task: {task.id} "
                            f"({task.title}, step {task.current_step + 1}/{len(task.steps)})"
                        )

                except Exception as e:
                    logger.error(f"Failed to resume task from {state_file}: {e}")

        except Exception as e:
            logger.error(f"Failed to scan multi-step tasks: {e}")

        if resumed:
            logger.info(f"Resumed {resumed} multi-step task(s)")

        return resumed

    def advance(self, task_id: str, step_result: Optional[dict] = None) -> bool:
        """
        Complete the current step and advance to the next.

        Args:
            task_id: Task ID
            step_result: Optional result data from the completed step

        Returns:
            True if advanced to next step, False if task is complete or failed
        """
        task = self._tasks.get(task_id)
        if not task:
            logger.error(f"Multi-step task not found: {task_id}")
            return False

        current = task.current_step_obj
        if not current:
            logger.warning(f"No current step for task {task_id}")
            return False

        # Mark current step as completed
        current.status = "completed"
        current.result = step_result
        task.updated = datetime.now().isoformat()

        logger.info(f"Step completed: {current.name} ({task.progress})")

        # Check if there are more steps
        next_index = task.current_step + 1
        if next_index >= len(task.steps):
            # Task complete
            task.status = "completed"
            task.current_step = next_index
            self._persist_state(task)

            log_action(
                action_type="multistep_completed",
                target=task_id,
                parameters={"title": task.title},
                result="success",
            )
            logger.info(f"Multi-step task completed: {task.id} ({task.title})")
            return False

        # Advance to next step
        task.current_step = next_index
        task.status = "in_progress"
        next_step = task.steps[next_index]

        # Check if next step requires approval
        if next_step.requires_approval:
            task.status = "paused"
            self._create_approval_request(task, next_step)
            logger.info(f"Step requires approval: {next_step.name}")

        self._persist_state(task)
        return True

    def _execute_step(self, task: MultiStepTask, step: TaskStep) -> Optional[dict]:
        """
        Execute a single step of a multi-step task.

        This creates a task file for the step and lets the normal
        workflow pipeline handle it.
        """
        if step.requires_approval:
            self._create_approval_request(task, step)
            return None

        # Create a task file for the step
        now = datetime.now()
        filename = f"{now.strftime('%Y%m%d_%H%M%S')}_multistep_{task.id}_step{task.current_step}.md"
        task_path = settings.needs_action_path / filename

        content = f"""---
title: '{task.title} - Step {task.current_step + 1}: {step.name}'
source: 'Multi-Step Task: {task.id}'
priority: normal
created: '{now.isoformat()}'
type: '{step.action}'
multistep_id: '{task.id}'
step_index: {task.current_step}
status: pending
---

# {step.name}

## Multi-Step Task: {task.title}

**Task ID**: {task.id}
**Step**: {task.current_step + 1} of {len(task.steps)}
**Action**: {step.action}

## Instructions

Execute step: {step.name}

---

*Part of multi-step task: {task.title}*
"""

        task_path.write_text(content, encoding="utf-8")
        logger.info(f"Created task file for step: {task_path}")
        return {"task_path": str(task_path)}

    def _create_approval_request(self, task: MultiStepTask, step: TaskStep) -> None:
        """Create an approval request for a step that requires human review."""
        now = datetime.now()
        filename = (
            f"{now.strftime('%Y%m%d_%H%M%S')}_approval_"
            f"{task.id}_step{task.current_step}.md"
        )
        approval_path = settings.pending_approval_path / filename

        content = f"""---
title: 'Approval Required: {task.title} - {step.name}'
source: 'Multi-Step Task: {task.id}'
priority: high
created: '{now.isoformat()}'
type: '{step.action}'
multistep_id: '{task.id}'
step_index: {task.current_step}
status: pending_approval
requires_approval: true
---

# Approval Required

## Multi-Step Task: {task.title}

**Task ID**: {task.id}
**Step**: {task.current_step + 1} of {len(task.steps)}
**Action**: {step.name}

## Progress So Far

{self._format_progress(task)}

## Action Required

Review and approve this step before execution proceeds.

Move this file to `Approved/` to continue the multi-step task.

---

*Part of multi-step task: {task.title}*
"""

        approval_path.write_text(content, encoding="utf-8")
        logger.info(f"Approval request created: {approval_path}")

    def _format_progress(self, task: MultiStepTask) -> str:
        """Format task progress for display."""
        lines = []
        for i, step in enumerate(task.steps):
            if step.status == "completed":
                lines.append(f"- [x] Step {i + 1}: {step.name}")
            elif i == task.current_step:
                lines.append(f"- [ ] Step {i + 1}: {step.name} **(current)**")
            else:
                lines.append(f"- [ ] Step {i + 1}: {step.name}")
        return "\n".join(lines)

    def _persist_state(self, task: MultiStepTask) -> None:
        """Write task state to YAML file."""
        try:
            settings.multistep_path.mkdir(parents=True, exist_ok=True)
            state_data = task.to_dict()
            task.state_file.write_text(
                yaml.dump(state_data, default_flow_style=False, allow_unicode=True),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"Failed to persist multi-step task state: {e}")

    def get_active_tasks(self) -> list[dict]:
        """Get all active (non-completed) multi-step tasks."""
        return [
            {
                "id": t.id,
                "title": t.title,
                "status": t.status,
                "progress": t.progress,
                "current_step": t.current_step,
                "total_steps": len(t.steps),
            }
            for t in self._tasks.values()
            if t.status not in ("completed", "failed")
        ]

    def get_task(self, task_id: str) -> Optional[MultiStepTask]:
        """Get a specific multi-step task."""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> list[dict]:
        """Get all multi-step tasks."""
        return [t.to_dict() for t in self._tasks.values()]
