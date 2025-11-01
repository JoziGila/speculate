#!/usr/bin/env python3
"""
Graph-based task planner
Generates optimal task graphs from user goals
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Set, Tuple
from enum import Enum
import json
from pathlib import Path
import re


class TaskStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"


class RelationType(Enum):
    BLOCKS = "blocks"          # A must be done before B (hard dependency)
    RELATES_TO = "relates_to"  # Thematically related (no dependency)
    PART_OF = "part_of"        # A is part of epic/group B (grouping)


@dataclass
class Task:
    """A node in the task graph - ID is the display name"""
    id: str  # Kebab-case, max 4 words, verb-first (e.g., "design-2fa-flow")
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    acceptance_criteria: List[str] = field(default_factory=list)
    checklist: List[Dict[str, bool]] = field(default_factory=list)  # [{"item": str, "done": bool}]
    estimate_hours: Optional[float] = None

    def is_complete(self) -> bool:
        return self.status == TaskStatus.DONE

    def checklist_progress(self) -> Tuple[int, int]:
        """Returns (completed, total)"""
        if not self.checklist:
            return (0, 0)
        completed = sum(1 for item in self.checklist if item.get("done", False))
        return (completed, len(self.checklist))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "acceptance_criteria": self.acceptance_criteria,
            "checklist": self.checklist,
            "estimate_hours": self.estimate_hours
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Task":
        return cls(
            id=data["id"],
            description=data.get("description", ""),
            status=TaskStatus(data.get("status", "pending")),
            acceptance_criteria=data.get("acceptance_criteria", []),
            checklist=data.get("checklist", []),
            estimate_hours=data.get("estimate_hours")
        )


@dataclass
class Relationship:
    """An edge in the task graph"""
    from_task: str  # task ID
    to_task: str    # task ID
    relation_type: RelationType

    def to_dict(self) -> dict:
        return {
            "from": self.from_task,
            "to": self.to_task,
            "type": self.relation_type.value
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Relationship":
        return cls(
            from_task=data["from"],
            to_task=data["to"],
            relation_type=RelationType(data["type"])
        )


def validate_task_id(task_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate task ID follows atomic naming rules:
    - Kebab-case (lowercase with hyphens)
    - Max 4 words
    - Verb-first pattern recommended

    Returns (is_valid, error_message)
    """
    # Check for uppercase
    if task_id != task_id.lower():
        return (False, f"Task ID must be lowercase: '{task_id}'")

    # Check for spaces
    if ' ' in task_id:
        return (False, f"Task ID must use hyphens, not spaces: '{task_id}'")

    # Check kebab-case pattern
    if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', task_id):
        return (False, f"Task ID must be kebab-case (lowercase alphanumeric with hyphens): '{task_id}'")

    # Check word count (max 4 words)
    words = task_id.split('-')
    if len(words) > 4:
        return (False, f"Task ID has {len(words)} words, max 4 allowed: '{task_id}'")

    return (True, None)


class TaskGraph:
    """A global directed graph of tasks"""

    def __init__(self):
        self.nodes: Dict[str, Task] = {}
        self.edges: List[Relationship] = []

    def add_task(self, task: Task) -> None:
        """Add a task to the graph"""
        # Validate task ID
        is_valid, error = validate_task_id(task.id)
        if not is_valid:
            raise ValueError(f"Invalid task ID: {error}")

        if task.id in self.nodes:
            raise ValueError(f"Task ID already exists: {task.id}")

        self.nodes[task.id] = task

    def update_task(self, task_id: str, **updates) -> None:
        """Update task properties"""
        if task_id not in self.nodes:
            raise ValueError(f"Task not found: {task_id}")

        task = self.nodes[task_id]
        for key, value in updates.items():
            if key == "status" and isinstance(value, str):
                value = TaskStatus(value)
            if hasattr(task, key):
                setattr(task, key, value)

    def delete_task(self, task_id: str) -> None:
        """Delete task and cascade relationships"""
        if task_id in self.nodes:
            del self.nodes[task_id]

        # Remove all relationships involving this task
        self.edges = [
            edge for edge in self.edges
            if edge.from_task != task_id and edge.to_task != task_id
        ]

    def add_relationship(self, from_id: str, to_id: str, rel_type: RelationType) -> None:
        """Add a relationship between tasks"""
        if from_id not in self.nodes:
            raise ValueError(f"Source task not found: {from_id}")
        if to_id not in self.nodes:
            raise ValueError(f"Target task not found: {to_id}")

        # Avoid duplicates
        for rel in self.edges:
            if rel.from_task == from_id and rel.to_task == to_id and rel.relation_type == rel_type:
                return

        self.edges.append(Relationship(from_id, to_id, rel_type))

    def delete_relationship(self, from_id: str, to_id: str, rel_type: Optional[RelationType] = None) -> None:
        """Delete relationship(s) between tasks"""
        if rel_type:
            self.edges = [
                edge for edge in self.edges
                if not (edge.from_task == from_id and edge.to_task == to_id and edge.relation_type == rel_type)
            ]
        else:
            # Delete all relationships between these tasks
            self.edges = [
                edge for edge in self.edges
                if not (edge.from_task == from_id and edge.to_task == to_id)
            ]

    def get_blocking_dependencies(self, task_id: str) -> List[Task]:
        """Get tasks that block this task (must be done first)"""
        blockers = []
        for rel in self.edges:
            if rel.to_task == task_id and rel.relation_type == RelationType.BLOCKS:
                blockers.append(self.nodes[rel.from_task])
        return blockers

    def get_blocked_tasks(self, task_id: str) -> List[Task]:
        """Get tasks that this task blocks"""
        blocked = []
        for rel in self.edges:
            if rel.from_task == task_id and rel.relation_type == RelationType.BLOCKS:
                blocked.append(self.nodes[rel.to_task])
        return blocked

    def get_downstream_tasks(self, task_id: str) -> Set[str]:
        """
        Get all tasks downstream from this task (transitive closure).
        Returns task IDs that would be affected by completing this task.
        """
        downstream = set()
        queue = [task_id]
        visited = set()

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # Find all tasks this one blocks
            for rel in self.edges:
                if rel.from_task == current and rel.relation_type == RelationType.BLOCKS:
                    downstream.add(rel.to_task)
                    queue.append(rel.to_task)

        return downstream

    def is_blocked(self, task_id: str) -> bool:
        """Check if task is blocked by incomplete dependencies"""
        deps = self.get_blocking_dependencies(task_id)
        return any(not dep.is_complete() for dep in deps)

    def get_available_tasks(self) -> List[Tuple[Task, bool]]:
        """
        Get pending tasks with ready/blocked status.
        Returns list of (task, is_ready) tuples.
        """
        available = []
        for task in self.nodes.values():
            if task.status == TaskStatus.PENDING:
                is_ready = not self.is_blocked(task.id)
                available.append((task, is_ready))
        return available

    def detect_cycles(self) -> List[List[str]]:
        """
        Detect cycles in the graph (only for BLOCKS relationships).
        Returns list of cycles, where each cycle is a list of task IDs.
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            # Follow BLOCKS relationships
            for edge in self.edges:
                if edge.from_task == node and edge.relation_type == RelationType.BLOCKS:
                    neighbor = edge.to_task
                    if neighbor not in visited:
                        dfs(neighbor, path.copy())
                    elif neighbor in rec_stack:
                        # Found a cycle
                        cycle_start = path.index(neighbor)
                        cycles.append(path[cycle_start:] + [neighbor])

            rec_stack.remove(node)

        for node_id in self.nodes.keys():
            if node_id not in visited:
                dfs(node_id, [])

        return cycles

    def find_orphans(self) -> List[str]:
        """Find tasks with no relationships (isolated nodes)"""
        connected = set()
        for edge in self.edges:
            connected.add(edge.from_task)
            connected.add(edge.to_task)

        orphans = [task_id for task_id in self.nodes.keys() if task_id not in connected]
        return orphans

    def to_json(self) -> str:
        """Serialize to JSON string"""
        data = {
            "nodes": {task_id: task.to_dict() for task_id, task in self.nodes.items()},
            "edges": [edge.to_dict() for edge in self.edges]
        }
        return json.dumps(data, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "TaskGraph":
        """Deserialize from JSON string"""
        data = json.loads(json_str)
        graph = cls()

        # Load nodes
        for task_id, task_data in data.get("nodes", {}).items():
            task = Task.from_dict(task_data)
            graph.nodes[task_id] = task

        # Load edges
        for edge_data in data.get("edges", []):
            graph.edges.append(Relationship.from_dict(edge_data))

        return graph

    def save(self, filepath: Path) -> None:
        """Save graph to JSON file atomically"""
        # Write to temp file first
        temp_path = filepath.with_suffix('.tmp')
        with open(temp_path, 'w') as f:
            f.write(self.to_json())

        # Atomic rename
        temp_path.replace(filepath)

    @classmethod
    def load(cls, filepath: Path) -> "TaskGraph":
        """Load graph from JSON file"""
        with open(filepath, 'r') as f:
            json_str = f.read()
        return cls.from_json(json_str)
