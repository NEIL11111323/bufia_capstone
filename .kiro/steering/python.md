---
inclusion: always
---

# Python Best Practices and Standards

## Code Style

- Follow PEP 8 style guide
- Use 4 spaces for indentation (no tabs)
- Limit line length to 100 characters
- Use descriptive variable and function names
- Use `snake_case` for variables, functions, and methods
- Use `PascalCase` for classes
- Use `UPPER_SCASE` for constants

## Imports

- Group imports in this order: standard library, third-party, local application
- Use absolute imports over relative imports
- Avoid wildcard imports (`from module import *`)
- Sort imports alphabetically within groups

## Functions

- Keep functions small and focused (single responsibility)
- Use type hints for function parameters and return values
- Write docstrings for all public functions and classes
- Prefer returning early over nested conditionals
- Use `*args` and `**kwargs` sparingly

## Classes

- Use composition over inheritance when appropriate
- Use `@property` for computed attributes
- Implement `__str__` and `__repr__` for debugging
- Use dataclasses for simple data containers (Python 3.7+)

## Error Handling

- Use specific exceptions (not bare `except:`)
- Handle exceptions at the appropriate level
- Clean up resources with `finally` or context managers
- Log errors with meaningful context
- Don't swallow exceptions silently

## Type Hints

- Use type hints for function signatures
- Use `Union`, `Optional`, and `List` from `typing`
- Consider `TypedDict` for structured dictionaries
- Use `Protocol` for structural subtyping

## Performance

- Use list comprehensions over loops when appropriate
- Use generators for large sequences
- Prefer built-in methods over custom implementations
- Use `__slots__` for memory optimization in classes with many instances

## Documentation

- Write docstrings in Google style or NumPy style
- Comment why, not what
- Keep comments up to date with code changes
- Use type hints to reduce need for parameter documentation

## Testing

- Write tests before fixing bugs (TDD when appropriate)
- Use `pytest` for testing
- Use `pytest-django` for Django projects
- Mock external dependencies in unit tests
- Aim for meaningful coverage, not just high numbers

## Virtual Environments

- Always use a virtual environment
- Use `requirements.txt` for dependencies
- Pin versions for reproducibility
- Use `pip freeze > requirements.txt` to update