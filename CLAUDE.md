# AGENTS.md - Agent Coding Guidelines

This document provides guidelines for agents working on this codebase.

## Project Overview

- **Project name**: djay-tsaf-parser
- **Type**: Python research project
- **Goal**: Understand the TSAF binary format used by djay macOS application
- **Python version**: 3.11.15

## Environment Setup

This project uses [uv](https://docs.astral.sh/uv/) to manage Python version, virtualenv, and dependencies.

```bash
# Install dependencies
uv sync

# Activate virtual environment
source .venv/bin/activate
```

## Build, Lint, and Test Commands

### Running Tests

```bash
# Run all tests
uv run pytest

# Run a single test (specify exact test name)
uv run pytest tests/your_test_file.py::test_function_name

# Run tests matching a pattern
uv run pytest -k "test_pattern"

# Run with verbose output
uv run pytest -v

# Run with coverage (if coverage is installed)
uv run pytest --cov=src --cov-report=term-missing
```

## Code Style Guidelines

### General Principles

- Follow [PEP 8](https://peps.python.org/pep-0008/) style guide
- Use 4 spaces for indentation (no tabs)
- Use LF line endings (enforced by `.editorconfig`)
- Add trailing newline to files
- Maximum line length: 88 characters (Black default)

### Imports

- Use absolute imports (`from package import module`)
- Group imports in the following order:
  1. Standard library
  2. Third-party libraries
  3. Local application imports
- Sort imports alphabetically within each group
- Use `isort` for automatic import sorting

```python
# Good
import os
import sys
from typing import Any

import pytest
from package import module

from djay_tsaf_parser import parser
```

### Naming Conventions

- **Variables/functions**: `snake_case` (e.g., `parse_entity`, `media_item_data`)
- **Classes**: `PascalCase` (e.g., `TSAFParser`, `EntityDecoder`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAGIC_BYTES`, `MAX_ENTITY_COUNT`)
- **Private members**: Prefix with underscore (e.g., `_internal_method`)
- **Type aliases**: `PascalCase` (e.g., `EntityMap = dict[str, Any]`)

### Type Annotations

- Use type hints for all function parameters and return values
- Use `typing` module for complex types (Union, Optional, etc.)
- Prefer modern Python 3.11+ union syntax (`str | None` over `Optional[str]`)

```python
# Good
def parse_header(data: bytes) -> dict[str, int]:
    ...

def process_entity(entity_type: str | None = None) -> list[Entity]:
    ...

# Avoid
def parse_header(data):  # Missing type hints
    ...
```

### Error Handling

- Use specific exception types
- Provide meaningful error messages
- Prefer explicit error handling over bare `except:`

```python
# Good
class TSAFParseError(Exception):
    """Raised when TSAF data cannot be parsed."""
    pass

def parse_data(data: bytes) -> ParsedData:
    if len(data) < HEADER_SIZE:
        raise TSAFParseError(f"Data too short: {len(data)} bytes, expected {HEADER_SIZE}")
    ...
```

### Docstrings

- Use Google-style or NumPy-style docstrings
- Include docstrings for all public classes and functions

```python
def parse_header(data: bytes) -> dict[str, int]:
    """Parse the TSAF header from binary data.

    Args:
        data: Raw binary data containing the TSAF header.

    Returns:
        Dictionary with keys: magic, version, entity_count.

    Raises:
        TSAFParseError: If the header is invalid.
    """
    ...
```

### File Organization

- One module per file
- Related modules in packages (directories with `__init__.py`)
- Keep modules focused and cohesive
- Use `__all__` to explicitly declare public API

### Testing Guidelines

- Place tests in `tests/` directory
- Mirror source directory structure in tests
- Use descriptive test names: `test_<function>_<scenario>_<expected>`
- Use fixtures for common test setup
- Assert specific exceptions with `pytest.raises`

```python
def test_parse_header_valid_magic():
    """Test that valid TSAF header parses correctly."""
    data = b"TSAF" + b"\x00\x03\x00\x03" + b"\x01\x00\x00\x00" + b"\x00\x00\x00\x00"
    result = parse_header(data)
    assert result["magic"] == "TSAF"
    assert result["entity_count"] == 1


def test_parse_header_invalid_magic_raises():
    """Test that invalid magic raises TSAFParseError."""
    data = b"XXXX" + b"\x00\x03\x00\x03" + b"\x01\x00\x00\x00"
    with pytest.raises(TSAFParseError, match="Invalid magic"):
        parse_header(data)
```

### Data Files

- Test data is stored in `/data` directory
- Binary blobs are named with pattern: `<song>_<column>.bin`
- Document format findings in TSAF.md if they are new discoveries

## Project Structure

```
djay-tsaf-parser/
├── .venv/              # Virtual environment (generated)
├── data/               # Test binary data
│   ├── guiboratto_*.bin
│   └── happysong_*.bin
├── src/
│   └── djay_tsaf_parser/  # Main package
├── tests/              # Test suite
├── .editorconfig       # Editor configuration
├── .gitattributes      # Git attributes
├── .python-version     # Python version specification
├── pyproject.toml      # Project configuration
└── uv.lock             # Dependency lock file
```

## Common Tasks

### Adding a new dependency

```bash
uv add <package>
uv add --group dev <dev-package>
```

### Running a specific test file

```bash
uv run pytest tests/test_parser.py
```
