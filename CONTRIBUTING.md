# Contributing to Kabbalah

Thank you for your interest in contributing to Kabbalah! This document provides guidelines and instructions for contributing.

## Code of Conduct

Please be respectful and constructive in all interactions with other contributors.

## Getting Started

### 1. Fork the Repository

```bash
git clone https://github.com/yourusername/kabbalah.git
cd kabbalah
```

### 2. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 3. Set Up Development Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e ".[dev]"
```

## Development Workflow

### Code Style

- Follow PEP 8 style guide
- Use Black for code formatting
- Use isort for import sorting
- Use mypy for type checking

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Check types
mypy src/

# Lint code
flake8 src/ tests/
```

### Testing

- Write tests for all new features
- Maintain >80% test coverage
- Use pytest for unit tests
- Use hypothesis for property-based tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=src/kabbalah --cov-report=html

# Run specific test file
pytest tests/unit/test_intake_node.py -v

# Run property-based tests
pytest tests/property/ -v
```

### Documentation

- Update docstrings for all functions and classes
- Follow Google-style docstrings
- Update README.md if adding new features
- Update relevant spec documents

Example docstring:

```python
def parse_request(self, request: UserRequest) -> Tuple[Specification, str]:
    """
    Parse user request into premium specification.
    
    Args:
        request: User's project request
        
    Returns:
        Tuple of (specification, run_id)
        
    Raises:
        InvalidRequestError: If request is malformed
        SpecificationError: If specification cannot be generated
    """
    pass
```

## Commit Guidelines

- Use clear, descriptive commit messages
- Reference issues when applicable
- Keep commits focused and atomic

Example:

```bash
git commit -m "feat: add FSM enforcement module

- Implement FSMEnforcementModule class
- Add support for BOOTSTRAP, DAY1, DAY2 modes
- Add immutable audit logging
- Fixes #123"
```

## Pull Request Process

1. **Update your branch** with latest main:
   ```bash
   git fetch origin
   git rebase origin/main
   ```

2. **Run tests locally**:
   ```bash
   pytest tests/ -v --cov=src/kabbalah
   ```

3. **Format code**:
   ```bash
   black src/ tests/
   isort src/ tests/
   mypy src/
   flake8 src/ tests/
   ```

4. **Push your branch**:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request** on GitHub with:
   - Clear title describing the change
   - Description of what was changed and why
   - Reference to related issues
   - Screenshots/examples if applicable

6. **Address review feedback**:
   - Make requested changes
   - Push updates to the same branch
   - Respond to comments

## Implementation Guidelines

### Phase-Based Development

Follow the implementation phases defined in the spec:

1. **Phase 1**: Core Orchestration
2. **Phase 2**: Runtime Hardening
3. **Phase 3**: Memory Subsystem
4. **Phase 4**: Provider Abstraction
5. **Phase 5**: Tool Execution
6. **Phase 6**: Observability
7. **Phase 7**: Parser/Pretty Printer
8. **Phase 8**: Configuration
9. **Phase 9**: Day 2 Operations
10. **Phase 10**: Integration Testing
11. **Phase 11**: Documentation

### Requirement Traceability

- Each task must reference a requirement
- Each requirement must have acceptance criteria
- Each acceptance criterion must be testable
- Each test must reference a requirement

### Contract Enforcement

All operations must define:
- **Pre-conditions**: Input validation
- **Post-conditions**: Output validation
- **Invariants**: State that must always be true

Example:

```python
class Operation:
    def execute(self, inputs: Dict) -> Dict:
        # Pre-condition: validate inputs
        assert self.validate_preconditions(inputs), "Invalid inputs"
        
        # Execute operation
        result = self._do_work(inputs)
        
        # Post-condition: validate outputs
        assert self.validate_postconditions(result), "Invalid outputs"
        
        return result
```

### Property-Based Testing

Use Hypothesis for property-based testing:

```python
from hypothesis import given, strategies as st

@given(st.lists(st.integers()))
def test_operation_idempotent(values):
    """Test that operation is idempotent."""
    result1 = operation(values)
    result2 = operation(result1)
    assert result1 == result2
```

## Reporting Issues

When reporting issues, please include:

1. **Description**: Clear description of the issue
2. **Steps to Reproduce**: How to reproduce the issue
3. **Expected Behavior**: What should happen
4. **Actual Behavior**: What actually happens
5. **Environment**: Python version, OS, etc.
6. **Logs/Screenshots**: Any relevant logs or screenshots

## Feature Requests

When requesting features, please include:

1. **Use Case**: Why this feature is needed
2. **Proposed Solution**: How you envision the feature
3. **Alternatives**: Other approaches considered
4. **Additional Context**: Any other relevant information

## Questions?

- Check existing issues and discussions
- Read the documentation in `docs/specs/`
- Open a discussion on GitHub

## Recognition

Contributors will be recognized in:
- README.md contributors section
- Release notes
- GitHub contributors page

Thank you for contributing to Kabbalah!
