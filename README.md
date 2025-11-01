# Speculate

AI-powered task graph planning for complex software development goals. Transform complex features into executable task graphs with atomic decomposition, dependency tracking, and visual Mermaid diagrams.

## Features

- **Atomic Task Decomposition**: Break down complex goals into 1-4 hour focused tasks
- **Dependency Tracking**: Visualize what blocks what with BLOCKS, RELATES_TO, and PART_OF relationships
- **Visual Mermaid Diagrams**: See your task graph with color-coded status (ready/blocked/in-progress/done)
- **Impact Analysis**: Understand what tasks will unblock when you complete work
- **Graph Validation**: Detect cycles, orphans, and integrity issues
- **Claude Integration**: Works seamlessly with Claude Code via skills

## Installation

### Using pipx (Recommended)

pipx installs the application in an isolated environment:

```bash
pipx install .
```

Or install directly from a git repository:

```bash
pipx install git+https://github.com/yourusername/speculate.git
```

### Using pip

You can also install with pip if you prefer:

```bash
pip install .
```

### Development Installation

For development, install with dev dependencies:

```bash
pip install -e ".[dev]"
```

## Quick Start

### 1. Initialize Claude Skill (Optional)

If you use Claude Code, create the skill integration:

```bash
speculate init
```

This creates `.claude/skills/speculate/SKILL.md` so Claude can use speculate for task planning.

### 2. Create Your First Task Graph

```bash
speculate add '{
  "tasks": [
    {
      "id": "design-api",
      "description": "Design REST API endpoints and data models",
      "estimate_hours": 2,
      "acceptance_criteria": [
        "API spec documented",
        "Data models defined",
        "Endpoints listed"
      ]
    },
    {
      "id": "implement-api",
      "description": "Implement the REST API",
      "estimate_hours": 4,
      "acceptance_criteria": [
        "All endpoints working",
        "Tests passing"
      ]
    }
  ],
  "relationships": [
    {"from": "design-api", "to": "implement-api", "type": "blocks"}
  ]
}'
```

### 3. View Your Task Graph

```bash
speculate available
```

This shows a Mermaid diagram with:
- **Green tasks**: Ready to start (no blockers)
- **Gray tasks**: Blocked (waiting on dependencies)
- **Blue tasks**: In progress
- **Light green tasks**: Completed

### 4. Start Working

```bash
speculate start design-api
```

### 5. Complete and See Impact

```bash
speculate complete design-api
speculate after design-api
```

See what tasks just became unblocked!

## Usage

### Task Management Commands

**Add tasks and relationships:**
```bash
speculate add '{"tasks": [...], "relationships": [...]}'
```

**Update task properties:**
```bash
speculate update '{"tasks": [{"id": "design-api", "estimate_hours": 3}]}'
```

**Delete tasks:**
```bash
speculate delete '{"tasks": ["old-task"]}'
```

**Quick status changes:**
```bash
speculate start <task-id>
speculate complete <task-id>
```

**Validate graph health:**
```bash
speculate validate
```

### Query Commands

**Show pending tasks (Mermaid diagram):**
```bash
speculate available
```

**Show downstream impact (Mermaid diagram):**
```bash
speculate after <task-id>
```

**Show task details:**
```bash
speculate show <task-id>
```

## Task Naming Rules

Tasks must follow atomic naming conventions:

- **Kebab-case**: `design-api-schema` (not `Design-API-Schema`)
- **Max 4 words**: `implement-user-auth` (not `implement-user-authentication-and-authorization`)
- **Verb-first**: `test-webhooks`, `refactor-database`
- **Single action**: No "and" in task names

Examples:
- ✓ `design-api-schema`, `implement-crud`, `test-webhooks`
- ✗ `Design-API-Schema` (uppercase)
- ✗ `design api schema` (spaces)
- ✗ `implement-and-test-api` (has "and")

## Relationship Types

**blocks**: Hard dependency (A must complete before B starts)
```json
{"from": "design-schema", "to": "implement-api", "type": "blocks"}
```

**relates_to**: Thematic connection (can parallelize)
```json
{"from": "implement-frontend", "to": "implement-backend", "type": "relates_to"}
```

**part_of**: Grouping (A is part of epic B)
```json
{"from": "design-login", "to": "add-authentication", "type": "part_of"}
```

## Task Structure

Each task includes:

```json
{
  "id": "implement-auth",
  "description": "Implement JWT authentication",
  "estimate_hours": 3,
  "status": "pending",
  "acceptance_criteria": [
    "JWT tokens generated",
    "Login endpoint working",
    "Token validation implemented"
  ],
  "checklist": [
    {"item": "Set up JWT library", "done": false},
    {"item": "Create token generation", "done": false},
    {"item": "Add middleware", "done": false}
  ]
}
```

## File Storage

Task graphs are stored in `.speculate/graph.json` in your project directory. This file is automatically created and managed by the CLI.

## Claude Code Integration

When you run `speculate init`, a Claude skill is created that allows Claude to:

- Detect when planning is needed
- Generate task graphs automatically
- Track dependencies and suggest next tasks
- Visualize progress with Mermaid diagrams
- Integrate with TodoWrite for active task tracking

Claude will use the `speculate` commands to manage your task graph during complex development work.

## Development

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black speculate tests
```

### Linting

```bash
ruff check speculate tests
```

## Project Structure

```
speculate/
├── speculate/              # Main package
│   ├── __init__.py        # Package initialization
│   ├── cli.py             # CLI commands
│   ├── graph_engine.py    # Task graph engine
│   └── mermaid_generator.py  # Mermaid diagram rendering
├── tests/                 # Test suite
│   ├── __init__.py
│   └── test_cli.py
├── .claude/               # Claude Code integration (created by init)
│   └── skills/
│       └── speculate/
│           └── SKILL.md
├── pyproject.toml         # Project configuration
└── README.md              # This file
```

## Requirements

- Python 3.9 or higher
- Click 8.0+ (for CLI)

## License

MIT
