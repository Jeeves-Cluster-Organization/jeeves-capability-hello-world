# Contributing to Jeeves Hello World

Thank you for your interest in contributing to Jeeves Hello World! This repository serves as both a working chatbot capability and a learning resource for understanding the Jeeves ecosystem.

## Before You Start

Please read our documentation to understand the project:

1. [README.md](README.md) - Project overview and quick start
2. [CONSTITUTION.md](jeeves_capability_hello_world/CONSTITUTION.md) - Architectural rules and boundaries
3. [Jeeves Core README](jeeves-core/README.md) - Understanding the micro-kernel

## Understanding the Ecosystem

Jeeves Hello World is part of a layered architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│  Capabilities (User Space) ← THIS REPOSITORY                    │
│  jeeves-capability-hello-world, other capabilities              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  jeeves-infra (Infrastructure + Orchestration Layer)            │
│  LLM providers, database clients, orchestration framework      │
└─────────────────────────────────────────────────────────────────┘
                              │ IPC (TCP+msgpack)
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│  jeeves-core (Micro-Kernel - Rust)                              │
│  Pipeline orchestration, envelope state, resource quotas        │
└─────────────────────────────────────────────────────────────────┘
```

## Contribution Guidelines

### What We're Looking For

Contributions should:

1. **Respect layer boundaries** - Capabilities import from jeeves_infra infrastructure layer
2. **Follow Constitution R7** - Import boundaries are enforced by tests
3. **Include tests** - All new code needs test coverage
4. **Update documentation** - Keep docs in sync with code changes

### Layer Boundaries

Before contributing, verify your change belongs in this layer:

| Change Type | Belongs In |
|-------------|------------|
| Domain-specific prompts | jeeves-capability-hello-world (here) |
| Custom tools | jeeves-capability-hello-world (here) |
| Pipeline configuration | jeeves-capability-hello-world (here) |
| LLM provider adapters | jeeves-infra |
| Database clients | jeeves-infra |
| Pipeline orchestration | jeeves-core |
| Envelope state management | jeeves-core |

### Types of Contributions

#### Good First Issues

- Improving documentation
- Adding examples to prompts
- Writing additional tests
- Fixing typos or clarifying comments

#### Feature Contributions

- Adding new tools (follow the pattern in `tools/hello_world_tools.py`)
- Enhancing prompts for better responses
- Adding new pipeline configurations
- Improving the Gradio UI

#### Documentation

- Explaining concepts for newcomers
- Adding tutorials or guides
- Improving code comments
- Creating diagrams

## How to Contribute

### Reporting Issues

Please use the following format:

```markdown
## Summary
Brief description of the issue or feature request.

## Layer Verification
- [ ] This belongs in the capability layer (not infra or core)
- [ ] I've read CONSTITUTION.md

## Current Behavior
What happens now?

## Expected Behavior
What should happen?

## Steps to Reproduce (for bugs)
1. Step one
2. Step two
3. ...

## Environment
- Python version:
- OS:
- LLM provider:

## Additional Context
Any other relevant information.
```

### Submitting Pull Requests

1. Fork the repository
2. Create a feature branch from `jeeves-capability-hello-world`
3. Make your changes with tests
4. Ensure all tests pass: `pytest`
5. Submit a PR with the following template:

```markdown
## Summary
What does this PR do?

## Layer Verification
Why does this belong in the capability layer?

## Changes
- List of changes

## Testing
- How was this tested?
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated

## Checklist
- [ ] I've read CONSTITUTION.md
- [ ] Tests pass locally
- [ ] Documentation updated if needed
- [ ] No breaking changes to the API
```

## Development Setup

```bash
# Clone the repository with submodules
git clone --recursive <repository-url>
cd jeeves-capability-hello-world
git checkout jeeves-capability-hello-world

# If you already cloned without --recursive
git submodule update --init --recursive

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements/all.txt

# Install dev dependencies
pip install pytest pytest-asyncio black ruff mypy

# Run tests
pytest

# Run linting
ruff check .
black --check .

# Run type checking
mypy jeeves_capability_hello_world/
```

### Running the Application

```bash
# Option 1: With Docker (recommended)
bash docker/setup_hello_world.sh --build
docker compose -f docker/docker-compose.hello-world.yml up -d

# Option 2: Local development
export LLM_PROVIDER=openai
export OPENAI_API_KEY=your_key
python gradio_app.py
```

## Code Style

- Follow PEP 8 conventions
- Use type hints for all function signatures
- Run `black` for formatting
- Run `ruff` for linting
- Keep functions focused and single-purpose
- Add docstrings for public functions

### Naming Conventions

- Classes: `PascalCase`
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`

### Import Order

1. Standard library imports
2. Third-party imports
3. Local imports (from jeeves_capability_hello_world)
4. Relative imports

## Testing

### Test Structure

```
jeeves_capability_hello_world/
└── tests/
    ├── unit/           # Fast, isolated tests
    ├── integration/    # Tests with real dependencies
    └── contract/       # Layer boundary tests
```

### Writing Tests

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_my_feature():
    """Test description explaining what's being tested."""
    # Arrange
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = "expected response"

    # Act
    result = await my_function(mock_llm)

    # Assert
    assert result == expected_value
```

### Running Specific Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest jeeves_capability_hello_world/tests/test_streaming.py

# Run with coverage
pytest --cov=jeeves_capability_hello_world

# Run verbose
pytest -v
```

## Documentation

### Where to Document

| Type | Location |
|------|----------|
| API documentation | Docstrings in code |
| Architecture | docs/ directory |
| Quick start | README.md |
| Contribution | CONTRIBUTING.md (this file) |
| Security | SECURITY.md |

### Documentation Style

- Use clear, concise language
- Include code examples
- Keep examples runnable
- Update docs when changing code

## Questions?

- Open an issue with the `question` label
- Check existing issues and documentation first
- Provide context about what you're trying to achieve

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.

See [LICENSE.txt](LICENSE.txt) for the full license text.
