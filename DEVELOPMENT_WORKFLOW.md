# Edge Mining Development Workflow

This guide describes the recommended workflow for contributing to the Edge Mining project.

## Initial Setup

### 1. Clone the repository and enter the directory

```bash
git clone https://github.com/edge-mining/core.git
cd core
```

### 2. Setup development environment

```bash
make setup
```

This command:

- Installs development dependencies from `requirements-dev.txt`
- Configures pre-commit hooks for automatic code quality checking

### 3. Verify everything works

```bash
make pre-commit
```

## Development Workflow

### 1. Before starting development

```bash
# Clean temporary files
make clean

# Update dependencies if necessary
make install-dev
```

### 2. During development

#### Automatic code formatting

```bash
make format
```

#### Code quality check

```bash
make lint
```

#### Running tests

```bash
make test
```

#### Complete check before commit

```bash
make pre-commit
```

### 3. Before committing

Pre-commit hooks run automatically, but you can run them manually:

```bash
make pre-commit
```

If there are errors, fix them and try again.

### 4. Commit and Push

```bash
git add .
git commit -m "feat: feature description"
git push
```

## Useful Commands

### Common problem solving

#### Auto-fix linting issues

```bash
make lint-fix
```

#### Clean the environment completely

```bash
make clean

# Remove virtual environment if necessary
rm -rf .venv
python -m venv .venv
make setup
```

#### Tests with detailed coverage

```bash
make test-cov
```

This will generate an HTML report in `htmlcov/index.html`

#### Security check

```bash
bandit -r edge_mining/
```

#### Type checking con mypy

```bash
mypy edge_mining/
```

## Tools Structure

See the [DEV_TOOLS.md](DEV_TOOLS.md) file for detailed information about the tools used in this project.

## Troubleshooting

### Pre-commit doesn't work

```bash
# Reinstall pre-commit
pre-commit uninstall
make pre-commit-install

# Update hooks
pre-commit autoupdate
```

### Import or dependency errors

```bash
# Check virtual environment
which python
# Should point to .venv/bin/python

# Reinstall dependencies
make clean
make install-dev
```

### Mypy errors

```bash
# Mypy is configured to be permissive during development
# Errors don't block commits but it's good to resolve them

# To run mypy manually:
mypy edge_mining/
```

### Formatting conflicts

```bash
# If black and flake8 are in conflict:
make format
make lint

# The makefile is configured to handle most conflicts
```

## Best Practices

1. **Always run `make pre-commit` before committing**
2. **Use `make format` to automatically format code**
3. **Write tests for new features**
4. **Maintain high test coverage**
5. **Use type hints when possible**
6. **Follow Python naming conventions (PEP 8)**
7. **Write docstrings for public functions and classes**

## Commit Conventions

Use conventional commits:

- `feat:` for new features
- `fix:` for bug fixes
- `docs:` for documentation updates
- `style:` for formatting changes
- `refactor:` for code refactoring
- `test:` for adding/modifying tests
- `chore:` for maintenance tasks

Example commit messages:

```bash
git commit -m "feat: add energy monitoring adapter for solar panels"
git commit -m "fix: resolve memory leak in optimization service"
git commit -m "docs: update API documentation for miner endpoints"
```
