"""Command-line interface for speculate - AI-powered task graph planning."""

import click
import json
import sys
from pathlib import Path
from typing import Optional

from speculate import __version__
from speculate.graph_engine import (
    TaskGraph, Task, TaskStatus, RelationType, validate_task_id
)
from speculate.mermaid_generator import render_mermaid


GRAPH_FILE = Path(".speculate/graph.json")


def ensure_graph_dir():
    """Ensure .speculate directory exists"""
    GRAPH_FILE.parent.mkdir(exist_ok=True)


def load_graph() -> TaskGraph:
    """Load graph from file or create empty graph"""
    if GRAPH_FILE.exists():
        return TaskGraph.load(GRAPH_FILE)
    return TaskGraph()


def save_graph(graph: TaskGraph):
    """Save graph to file atomically"""
    ensure_graph_dir()
    graph.save(GRAPH_FILE)


@click.group()
@click.version_option(version=__version__)
def main():
    """Speculate - AI-powered task graph planning.

    Transform complex software goals into executable task graphs with atomic
    decomposition, dependency tracking, and visual Mermaid diagrams.
    """
    pass


# ============================================================================
# Init Command
# ============================================================================

@main.command()
@click.option('--force', is_flag=True, help='Overwrite existing skill')
@click.option('--no-install-tools', is_flag=True, help='Skip automatic installation of missing tools')
def init(force, no_install_tools):
    """Initialize Claude skill for speculate integration.

    Creates .claude/skills/speculate/ with the skill definition that allows
    Claude to use speculate for task planning.
    """
    skill_dir = Path(".claude/skills/speculate")
    skill_file = skill_dir / "SKILL.md"

    if skill_file.exists() and not force:
        click.echo(f"Error: Skill already exists at {skill_file}", err=True)
        click.echo("Use --force to overwrite", err=True)
        sys.exit(1)

    # Create skill directory
    skill_dir.mkdir(parents=True, exist_ok=True)

    # Read SKILL.md template from package
    template_path = Path(__file__).parent / "markdown" / "SKILL.md"

    if not template_path.exists():
        click.echo(f"Error: Template file not found at {template_path}", err=True)
        sys.exit(1)

    skill_content = template_path.read_text()

    # Write SKILL.md to current directory's .claude/skills/speculate/
    skill_file.write_text(skill_content)

    click.echo(f"✓ Created Claude skill at {skill_file}")

    # Check for recommended tools
    import shutil
    import platform

    # Detect platform and set install commands
    system = platform.system()
    if system == "Darwin":  # macOS
        pkg_manager = "brew install"
    elif system == "Linux":
        # Try to detect Linux package manager
        if shutil.which("apt"):
            pkg_manager = "apt install"
        elif shutil.which("dnf"):
            pkg_manager = "dnf install"
        elif shutil.which("pacman"):
            pkg_manager = "pacman -S"
        else:
            pkg_manager = "# (use your package manager)"
    else:  # Windows or other
        pkg_manager = "# (install via package manager)"

    recommended_tools = {
        'fd': f'{pkg_manager} fd-find' if 'apt' in pkg_manager else f'{pkg_manager} fd',
        'rg': f'{pkg_manager} ripgrep',
        'ast-grep': f'{pkg_manager} ast-grep',
        'jq': f'{pkg_manager} jq',
        'yq': f'{pkg_manager} yq',
        'tokei': f'{pkg_manager} tokei',
        'tree': f'{pkg_manager} tree',
        'fzf': f'{pkg_manager} fzf'
    }

    missing_tools = []
    for tool, install_cmd in recommended_tools.items():
        if not shutil.which(tool):
            missing_tools.append((tool, install_cmd))

    if missing_tools:
        if not no_install_tools:
            # Attempt to install missing tools (default behavior)
            click.echo(f"\n📦 Installing recommended tools...")
            import subprocess

            failed_installs = []
            for tool, install_cmd in missing_tools:
                try:
                    # Parse the install command
                    if pkg_manager != "# (install via package manager)" and pkg_manager != "# (use your package manager)":
                        click.echo(f"  {tool}...", nl=False)
                        result = subprocess.run(install_cmd.split(), capture_output=True, text=True)
                        if result.returncode != 0:
                            click.secho(f" ✗", fg='red')
                            failed_installs.append((tool, install_cmd))
                        else:
                            click.secho(f" ✓", fg='green')
                    else:
                        failed_installs.append((tool, install_cmd))
                except Exception as e:
                    click.secho(f" ✗", fg='red')
                    failed_installs.append((tool, install_cmd))

            if failed_installs:
                click.echo(f"\n⚠️  Some tools could not be installed automatically:")
                for tool, install_cmd in failed_installs:
                    click.secho(f"  {install_cmd}", fg='yellow')
        else:
            # User opted out of auto-install
            click.echo(f"\n💡 Recommended tools for faster codebase exploration:")
            for tool, install_cmd in missing_tools:
                click.echo(f"  {install_cmd}")

    click.secho(f"\n✨ Skill ready. Claude will use 'speculate' for task planning.", fg='cyan', bold=True)


# ============================================================================
# Write Commands (modify graph, auto-save)
# ============================================================================

@main.command()
@click.argument('json_payload')
def add(json_payload):
    """Add tasks and relationships from JSON.

    Example:
        speculate add '{"tasks": [{"id": "design-api", "estimate_hours": 2}]}'
    """
    try:
        data = json.loads(json_payload)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON: {e}", err=True)
        sys.exit(1)

    graph = load_graph()

    if "tasks" not in data and "relationships" not in data:
        click.echo("Error: JSON must contain 'tasks' and/or 'relationships'", err=True)
        sys.exit(1)

    tasks_to_add = data.get("tasks", [])
    relationships_to_add = data.get("relationships", [])

    # Validate all tasks
    for task_data in tasks_to_add:
        if "id" not in task_data:
            click.echo("Error: Each task must have an 'id' field", err=True)
            sys.exit(1)

        task_id = task_data["id"]
        is_valid, error = validate_task_id(task_id)
        if not is_valid:
            click.echo(f"Error: {error}", err=True)
            sys.exit(1)

        if task_id in graph.nodes:
            click.echo(f"Error: Task ID already exists: {task_id}", err=True)
            sys.exit(1)

    # Validate relationships
    for rel in relationships_to_add:
        if "from" not in rel or "to" not in rel or "type" not in rel:
            click.echo("Error: Each relationship must have 'from', 'to', and 'type' fields", err=True)
            sys.exit(1)

        all_task_ids = set(graph.nodes.keys()) | {t["id"] for t in tasks_to_add}

        if rel["from"] not in all_task_ids:
            click.echo(f"Error: Relationship references non-existent task: {rel['from']}", err=True)
            sys.exit(1)

        if rel["to"] not in all_task_ids:
            click.echo(f"Error: Relationship references non-existent task: {rel['to']}", err=True)
            sys.exit(1)

        try:
            RelationType(rel["type"])
        except ValueError:
            click.echo(f"Error: Invalid relationship type: {rel['type']}", err=True)
            click.echo(f"Valid types: blocks, relates_to, part_of", err=True)
            sys.exit(1)

    # Add tasks
    for task_data in tasks_to_add:
        task = Task(
            id=task_data["id"],
            description=task_data.get("description", ""),
            status=TaskStatus(task_data.get("status", "pending")),
            acceptance_criteria=task_data.get("acceptance_criteria", []),
            checklist=task_data.get("checklist", []),
            estimate_hours=task_data.get("estimate_hours")
        )
        graph.add_task(task)

    # Add relationships
    for rel in relationships_to_add:
        graph.add_relationship(
            rel["from"],
            rel["to"],
            RelationType(rel["type"])
        )

    save_graph(graph)
    click.echo(f"Added {len(tasks_to_add)} task(s) and {len(relationships_to_add)} relationship(s)")


@main.command()
@click.argument('json_payload')
def update(json_payload):
    """Update task properties from JSON.

    Example:
        speculate update '{"tasks": [{"id": "design-api", "estimate_hours": 3}]}'
    """
    try:
        data = json.loads(json_payload)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON: {e}", err=True)
        sys.exit(1)

    graph = load_graph()
    tasks_to_update = data.get("tasks", [])

    if not tasks_to_update:
        click.echo("Error: JSON must contain 'tasks' array", err=True)
        sys.exit(1)

    # Validate
    for task_data in tasks_to_update:
        if "id" not in task_data:
            click.echo("Error: Each task must have an 'id' field", err=True)
            sys.exit(1)

        if task_data["id"] not in graph.nodes:
            click.echo(f"Error: Task not found: {task_data['id']}", err=True)
            sys.exit(1)

        if "status" in task_data:
            try:
                TaskStatus(task_data["status"])
            except ValueError:
                click.echo(f"Error: Invalid status: {task_data['status']}", err=True)
                click.echo(f"Valid statuses: pending, in_progress, done", err=True)
                sys.exit(1)

    # Apply updates
    for task_data in tasks_to_update:
        task_id = task_data["id"]
        updates = {k: v for k, v in task_data.items() if k != "id"}
        graph.update_task(task_id, **updates)

    save_graph(graph)
    click.echo(f"Updated {len(tasks_to_update)} task(s)")


@main.command()
@click.argument('json_payload')
def delete(json_payload):
    """Delete tasks and relationships from JSON.

    Example:
        speculate delete '{"tasks": ["old-task"]}'
    """
    try:
        data = json.loads(json_payload)
    except json.JSONDecodeError as e:
        click.echo(f"Error: Invalid JSON: {e}", err=True)
        sys.exit(1)

    graph = load_graph()
    tasks_to_delete = data.get("tasks", [])
    relationships_to_delete = data.get("relationships", [])

    deleted_tasks = 0
    for task_id in tasks_to_delete:
        if task_id in graph.nodes:
            graph.delete_task(task_id)
            deleted_tasks += 1

    deleted_rels = 0
    for rel in relationships_to_delete:
        if "from" in rel and "to" in rel:
            rel_type = RelationType(rel["type"]) if "type" in rel else None
            before_count = len(graph.edges)
            graph.delete_relationship(rel["from"], rel["to"], rel_type)
            after_count = len(graph.edges)
            deleted_rels += (before_count - after_count)

    save_graph(graph)
    click.echo(f"Deleted {deleted_tasks} task(s) and {deleted_rels} relationship(s)")


@main.command()
@click.argument('task_id')
def start(task_id):
    """Mark task as in_progress.

    Example:
        speculate start design-api
    """
    graph = load_graph()

    if task_id not in graph.nodes:
        click.echo(f"Error: Task not found: {task_id}", err=True)
        sys.exit(1)

    graph.update_task(task_id, status=TaskStatus.IN_PROGRESS)
    save_graph(graph)
    click.echo(f"Started task: {task_id}")


@main.command()
@click.argument('task_id')
def complete(task_id):
    """Mark task as done.

    Example:
        speculate complete design-api
    """
    graph = load_graph()

    if task_id not in graph.nodes:
        click.echo(f"Error: Task not found: {task_id}", err=True)
        sys.exit(1)

    graph.update_task(task_id, status=TaskStatus.DONE)
    save_graph(graph)
    click.echo(f"Completed task: {task_id}")


@main.command()
def validate():
    """Validate graph health - check for cycles, orphans, and integrity issues."""
    graph = load_graph()

    issues = []

    # Check for cycles
    cycles = graph.detect_cycles()
    if cycles:
        issues.append(f"Found {len(cycles)} cycle(s):")
        for i, cycle in enumerate(cycles, 1):
            cycle_path = " → ".join(cycle)
            issues.append(f"  {i}. {cycle_path}")

    # Check for orphans
    orphans = graph.find_orphans()
    if orphans:
        issues.append(f"\nFound {len(orphans)} orphaned task(s) (no relationships):")
        for orphan in orphans:
            issues.append(f"  - {orphan}")

    # Validate task IDs
    invalid_ids = []
    for task_id in graph.nodes.keys():
        is_valid, error = validate_task_id(task_id)
        if not is_valid:
            invalid_ids.append((task_id, error))

    if invalid_ids:
        issues.append(f"\nFound {len(invalid_ids)} task(s) with invalid IDs:")
        for task_id, error in invalid_ids:
            issues.append(f"  - {task_id}: {error}")

    # Check relationship integrity
    broken_rels = []
    for edge in graph.edges:
        if edge.from_task not in graph.nodes:
            broken_rels.append(f"{edge.from_task} → {edge.to_task} (source missing)")
        elif edge.to_task not in graph.nodes:
            broken_rels.append(f"{edge.from_task} → {edge.to_task} (target missing)")

    if broken_rels:
        issues.append(f"\nFound {len(broken_rels)} broken relationship(s):")
        for rel in broken_rels:
            issues.append(f"  - {rel}")

    if issues:
        click.echo("Validation FAILED:\n")
        click.echo("\n".join(issues))
        sys.exit(1)
    else:
        click.echo("Validation PASSED: Graph is healthy")
        click.echo(f"  - {len(graph.nodes)} tasks")
        click.echo(f"  - {len(graph.edges)} relationships")
        click.echo(f"  - No cycles, orphans, or integrity issues")


# ============================================================================
# Query Commands (read-only)
# ============================================================================

@main.command()
def available():
    """Show all pending tasks with ready/blocked status (Mermaid diagram).

    Ready tasks (green) can be started immediately.
    Blocked tasks (gray) are waiting on dependencies.
    """
    graph = load_graph()

    if not graph.nodes:
        click.echo("No tasks in graph")
        return

    mermaid = render_mermaid(
        graph,
        highlight_ready=True,
        filter_pending_only=True
    )
    click.echo(mermaid)


@main.command()
@click.argument('task_id')
def after(task_id):
    """Show downstream tasks after completing a task (Mermaid diagram).

    Visualizes what tasks would become unblocked (bright green) if this
    task were completed.

    Example:
        speculate after design-api
    """
    graph = load_graph()

    if task_id not in graph.nodes:
        click.echo(f"Error: Task not found: {task_id}", err=True)
        sys.exit(1)

    mermaid = render_mermaid(
        graph,
        highlight_downstream=task_id,
        filter_pending_only=True
    )
    click.echo(mermaid)


@main.command()
@click.argument('task_id')
def show(task_id):
    """Show detailed information about a task.

    Example:
        speculate show design-api
    """
    graph = load_graph()

    if task_id not in graph.nodes:
        click.echo(f"Error: Task not found: {task_id}", err=True)
        sys.exit(1)

    task = graph.nodes[task_id]

    click.echo(f"Task: {task.id}")
    click.echo(f"Status: {task.status.value}")

    if task.description:
        click.echo(f"\nDescription:")
        click.echo(f"  {task.description}")

    if task.estimate_hours:
        click.echo(f"\nEstimate: {task.estimate_hours}h")

    if task.acceptance_criteria:
        click.echo(f"\nAcceptance Criteria:")
        for i, criterion in enumerate(task.acceptance_criteria, 1):
            click.echo(f"  {i}. {criterion}")

    if task.checklist:
        click.echo(f"\nChecklist:")
        completed, total = task.checklist_progress()
        click.echo(f"  Progress: {completed}/{total}")
        for item in task.checklist:
            status = "✓" if item.get("done", False) else "○"
            click.echo(f"  {status} {item['item']}")

    # Show blocking dependencies
    blockers = graph.get_blocking_dependencies(task.id)
    if blockers:
        click.echo(f"\nBlocked by:")
        for blocker in blockers:
            status_icon = "✓" if blocker.is_complete() else "○"
            click.echo(f"  {status_icon} {blocker.id} ({blocker.status.value})")

    # Show blocked tasks
    blocked = graph.get_blocked_tasks(task.id)
    if blocked:
        click.echo(f"\nBlocks:")
        for b in blocked:
            click.echo(f"  - {b.id} ({b.status.value})")


if __name__ == '__main__':
    main()
