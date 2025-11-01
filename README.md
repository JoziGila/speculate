# Speculate

AI-powered task graph planning for complex software development. Break down features into atomic tasks with dependency tracking and visual Mermaid diagrams.

## Features

- **Atomic Tasks**: 1-4 hour focused tasks with clear done states
- **Dependency Tracking**: Visualize what blocks what (BLOCKS, RELATES_TO, PART_OF)
- **Visual Diagrams**: Color-coded Mermaid graphs (ready/blocked/in-progress/done)
- **Impact Analysis**: See what unblocks when you complete tasks
- **Claude Integration**: Works seamlessly with Claude Code

## Installation

```bash
# Recommended: pipx for isolated install
pipx install .

# Or use pip
pip install .

# Development with tests
pip install -e ".[dev]"
```

## Quick Start

**Just run:**
```bash
speculate init
```

That's it! Claude will automatically manage task graphs for you when planning complex features. Claude uses `speculate` commands to break down work, track dependencies, and guide you through implementation.

**Manual usage** (if needed):
```bash
# Add tasks
speculate add '{"tasks": [{"id": "design-api", "estimate_hours": 2}], "relationships": [...]}'

# View graph
speculate available

# Work on tasks
speculate start design-api
speculate complete design-api
speculate after design-api  # See what unblocked
```

## Commands

### Task Management
```bash
speculate add '{"tasks": [...], "relationships": [...]}'
speculate update '{"tasks": [{"id": "task-id", "estimate_hours": 3}]}'
speculate delete '{"tasks": ["task-id"]}'
speculate start <task-id>
speculate complete <task-id>
speculate validate
```

### Queries
```bash
speculate available      # Mermaid diagram of pending tasks
speculate after <id>     # Impact of completing this task
speculate show <id>      # Task details
```

## Task Rules

**Naming**: Kebab-case, max 4 words, verb-first
- ✓ `design-api`, `implement-auth`, `test-webhooks`
- ✗ `Design-API` (uppercase), `design api` (spaces), `implement-and-test` (has "and")

**Size**: 1-4 hours each with clear acceptance criteria

**Relationships**:
- `blocks`: A must complete before B starts
- `relates_to`: Thematic connection (can parallelize)
- `part_of`: A is part of epic B

## Example Task
```json
{
  "id": "implement-auth",
  "description": "JWT authentication",
  "estimate_hours": 3,
  "status": "pending",
  "acceptance_criteria": [
    "JWT tokens generated",
    "Login endpoint working",
    "Token validation implemented"
  ],
  "checklist": [
    {"item": "Set up JWT library", "done": false},
    {"item": "Create token generation", "done": false}
  ]
}
```

## Storage

Graphs stored in `.speculate/graph.json` (auto-managed).

## Development

```bash
pytest              # Run tests
black speculate tests    # Format
ruff check speculate tests  # Lint
```

## License

MIT
