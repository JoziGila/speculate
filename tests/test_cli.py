"""Tests for CLI functionality."""

import json
import tempfile
from pathlib import Path
from click.testing import CliRunner
from speculate.cli import main


def test_version():
    """Test version option."""
    runner = CliRunner()
    result = runner.invoke(main, ['--version'])
    assert result.exit_code == 0
    assert '0.1.0' in result.output


def test_add_tasks():
    """Test adding tasks to graph."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmpdir):
            payload = json.dumps({
                "tasks": [
                    {"id": "design-api", "estimate_hours": 2},
                    {"id": "implement-api", "estimate_hours": 4}
                ],
                "relationships": [
                    {"from": "design-api", "to": "implement-api", "type": "blocks"}
                ]
            })
            result = runner.invoke(main, ['add', payload])
            assert result.exit_code == 0
            assert "Added 2 task(s)" in result.output
            assert Path(".speculate/graph.json").exists()


def test_start_task():
    """Test marking task as in_progress."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmpdir):
            # First add a task
            payload = json.dumps({"tasks": [{"id": "test-task", "estimate_hours": 1}]})
            runner.invoke(main, ['add', payload])

            # Then start it
            result = runner.invoke(main, ['start', 'test-task'])
            assert result.exit_code == 0
            assert "Started task: test-task" in result.output


def test_complete_task():
    """Test marking task as done."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmpdir):
            # Add and complete a task
            payload = json.dumps({"tasks": [{"id": "test-task", "estimate_hours": 1}]})
            runner.invoke(main, ['add', payload])

            result = runner.invoke(main, ['complete', 'test-task'])
            assert result.exit_code == 0
            assert "Completed task: test-task" in result.output


def test_validate_empty_graph():
    """Test validation on empty graph."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmpdir):
            result = runner.invoke(main, ['validate'])
            assert result.exit_code == 0
            assert "PASSED" in result.output


def test_invalid_task_id():
    """Test that invalid task IDs are rejected."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=tmpdir):
            payload = json.dumps({
                "tasks": [{"id": "Invalid-Task-Name", "estimate_hours": 1}]
            })
            result = runner.invoke(main, ['add', payload])
            assert result.exit_code == 1
            assert "must be lowercase" in result.output
