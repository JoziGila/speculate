#!/usr/bin/env python3
"""
Mermaid diagram generator for task graphs
"""

from typing import List, Set, Optional
from speculate.graph_engine import TaskGraph, Task, TaskStatus, RelationType


def render_mermaid(
    graph: TaskGraph,
    highlight_ready: bool = False,
    highlight_downstream: Optional[str] = None,
    filter_pending_only: bool = False
) -> str:
    """
    Render task graph as Mermaid flowchart.

    Args:
        graph: The task graph to render
        highlight_ready: If True, highlight ready tasks in green, dim blocked in gray
        highlight_downstream: If set, highlight downstream tasks from this task ID
        filter_pending_only: If True, only show pending tasks

    Returns:
        Mermaid flowchart markdown
    """
    lines = ["```mermaid", "graph TD"]

    # Determine which tasks to include
    tasks_to_show = {}
    for task_id, task in graph.nodes.items():
        if filter_pending_only and task.status != TaskStatus.PENDING:
            continue
        tasks_to_show[task_id] = task

    if not tasks_to_show:
        lines.append("  empty[\"No tasks to display\"]")
        lines.append("```")
        return "\n".join(lines)

    # Calculate downstream tasks if needed
    downstream_ids = set()
    if highlight_downstream and highlight_downstream in graph.nodes:
        downstream_ids = graph.get_downstream_tasks(highlight_downstream)

    # Render nodes with labels and styling
    for task_id, task in tasks_to_show.items():
        label = _format_node_label(task)
        node_def = f"  {_sanitize_id(task_id)}[\"{label}\"]"
        lines.append(node_def)

    # Render edges (only between visible tasks)
    for edge in graph.edges:
        if edge.from_task in tasks_to_show and edge.to_task in tasks_to_show:
            from_id = _sanitize_id(edge.from_task)
            to_id = _sanitize_id(edge.to_task)

            # Different arrow styles for different relationship types
            if edge.relation_type == RelationType.BLOCKS:
                lines.append(f"  {from_id} --> {to_id}")
            elif edge.relation_type == RelationType.PART_OF:
                lines.append(f"  {from_id} -.-> {to_id}")
            elif edge.relation_type == RelationType.RELATES_TO:
                lines.append(f"  {from_id} ~~~ {to_id}")

    # Apply styling
    lines.append("")
    lines.extend(_generate_styles(
        graph,
        tasks_to_show,
        highlight_ready,
        highlight_downstream,
        downstream_ids
    ))

    lines.append("```")
    return "\n".join(lines)


def _format_node_label(task: Task) -> str:
    """Format node label with task ID, estimate, and status icon"""
    # Status icons
    icon_map = {
        TaskStatus.DONE: "✓",
        TaskStatus.IN_PROGRESS: "⟳",
        TaskStatus.PENDING: "○"
    }
    icon = icon_map.get(task.status, "○")

    # Build label
    parts = [task.id]

    if task.estimate_hours:
        parts.append(f"({task.estimate_hours}h)")

    parts.append(f"[{icon}]")

    return " ".join(parts)


def _sanitize_id(task_id: str) -> str:
    """Sanitize task ID for use as Mermaid node ID"""
    # Replace hyphens with underscores for Mermaid compatibility
    return task_id.replace("-", "_")


def _generate_styles(
    graph: TaskGraph,
    tasks_to_show: dict,
    highlight_ready: bool,
    highlight_downstream: Optional[str],
    downstream_ids: Set[str]
) -> List[str]:
    """Generate CSS styling for nodes"""
    styles = []

    # Status-based coloring (base layer)
    done_nodes = []
    in_progress_nodes = []
    pending_nodes = []

    for task_id, task in tasks_to_show.items():
        sanitized_id = _sanitize_id(task_id)

        if task.status == TaskStatus.DONE:
            done_nodes.append(sanitized_id)
        elif task.status == TaskStatus.IN_PROGRESS:
            in_progress_nodes.append(sanitized_id)
        elif task.status == TaskStatus.PENDING:
            pending_nodes.append(sanitized_id)

    # Apply base status colors
    if done_nodes:
        styles.append(f"  classDef done fill:#90EE90,stroke:#333,stroke-width:2px")
        styles.append(f"  class {','.join(done_nodes)} done")

    if in_progress_nodes:
        styles.append(f"  classDef inProgress fill:#ADD8E6,stroke:#333,stroke-width:2px")
        styles.append(f"  class {','.join(in_progress_nodes)} inProgress")

    if pending_nodes:
        styles.append(f"  classDef pending fill:#F5F5DC,stroke:#333,stroke-width:2px")
        styles.append(f"  class {','.join(pending_nodes)} pending")

    # Highlight ready/blocked (overrides base pending color)
    if highlight_ready:
        ready_nodes = []
        blocked_nodes = []

        for task_id, task in tasks_to_show.items():
            if task.status == TaskStatus.PENDING:
                is_blocked = graph.is_blocked(task_id)
                sanitized_id = _sanitize_id(task_id)

                if is_blocked:
                    blocked_nodes.append(sanitized_id)
                else:
                    ready_nodes.append(sanitized_id)

        if ready_nodes:
            styles.append(f"  classDef ready fill:#98FB98,stroke:#2E7D32,stroke-width:3px")
            styles.append(f"  class {','.join(ready_nodes)} ready")

        if blocked_nodes:
            styles.append(f"  classDef blocked fill:#D3D3D3,stroke:#666,stroke-width:1px")
            styles.append(f"  class {','.join(blocked_nodes)} blocked")

    # Highlight downstream tasks (overrides ready/blocked)
    if highlight_downstream and downstream_ids:
        unblocked_downstream = []
        still_blocked_downstream = []

        for task_id in downstream_ids:
            if task_id not in tasks_to_show:
                continue

            task = tasks_to_show[task_id]
            if task.status != TaskStatus.PENDING:
                continue

            sanitized_id = _sanitize_id(task_id)

            # Check if this task would become unblocked
            blockers = graph.get_blocking_dependencies(task_id)
            would_be_unblocked = all(
                blocker.is_complete() or blocker.id == highlight_downstream
                for blocker in blockers
            )

            if would_be_unblocked:
                unblocked_downstream.append(sanitized_id)
            else:
                still_blocked_downstream.append(sanitized_id)

        if unblocked_downstream:
            styles.append(f"  classDef willUnblock fill:#00FA9A,stroke:#006400,stroke-width:4px")
            styles.append(f"  class {','.join(unblocked_downstream)} willUnblock")

        if still_blocked_downstream:
            styles.append(f"  classDef stillBlocked fill:#FFE4B5,stroke:#DAA520,stroke-width:2px")
            styles.append(f"  class {','.join(still_blocked_downstream)} stillBlocked")

    return styles
