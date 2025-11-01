"""Tests for CLI functionality."""

from click.testing import CliRunner
from speculate.cli import main


def test_hello_default():
    """Test hello command with default name."""
    runner = CliRunner()
    result = runner.invoke(main, ['hello'])
    assert result.exit_code == 0
    assert 'Hello, World!' in result.output


def test_hello_custom_name():
    """Test hello command with custom name."""
    runner = CliRunner()
    result = runner.invoke(main, ['hello', '--name', 'Alice'])
    assert result.exit_code == 0
    assert 'Hello, Alice!' in result.output


def test_info():
    """Test info command."""
    runner = CliRunner()
    result = runner.invoke(main, ['info'])
    assert result.exit_code == 0
    assert 'Speculate version' in result.output
    assert 'pipx' in result.output


def test_version():
    """Test version option."""
    runner = CliRunner()
    result = runner.invoke(main, ['--version'])
    assert result.exit_code == 0
    assert '0.1.0' in result.output
