set shell := ["bash", "-uc"]
set positional-arguments := true

python := "python3"
uv := "uv"

# Default task: list all recipes
default:
    @just --list

# Run all CI fast checks
ci-fast: lint typecheck arch ci-contracts tests

# Run full CI suite including smoke tests
ci: ci-fast tests-full package-smoke

# Sync project dependencies (replaces install-ci-tools)
install:
    {{ uv }} sync --all-extras --dev

# Install standalone single-file executable to ~/bin/
install-standalone:
    @mkdir -p ~/bin
    {{ uv }} run --with shiv --with pip shiv ".[full]" --console-script desloppify -o ~/bin/desloppify
    @echo "Installed standalone desloppify to ~/bin/desloppify"

# Run linter
lint:
    {{ uv }} run ruff check . --select E9,F63,F7,F82

# Run type checker
typecheck:
    {{ uv }} run mypy

# Run architectural contract checks
arch:
    @if [ ! -f ".github/importlinter.ini" ]; then \
        echo "Missing .github/importlinter.ini. Add import contracts before running arch gate."; \
        exit 1; \
    fi
    {{ uv }} run lint-imports --config .github/importlinter.ini

# Run CI specific contract tests
ci-contracts:
    {{ uv }} run pytest -q desloppify/tests/ci/test_ci_contracts.py
    {{ uv }} run pytest -q desloppify/tests/commands/test_lifecycle_transitions.py -k "assessment_then_score_when_no_review_followup"

# Run Roslyn integration tests
integration-roslyn:
    {{ uv }} run pytest -q desloppify/tests/lang/csharp/test_csharp_deps.py -k "roslyn"

# Run standard tests
tests:
    {{ uv }} run pytest -q

# Run full suite of tests with all extras
tests-full:
    {{ uv }} run --extra full pytest -q

# Build package and verify extras metadata (smoke test)
package-smoke:
    rm -rf dist
    {{ uv }} build
    {{ uv }} run --with twine twine check dist/*
    # Verify wheel installation and extras metadata without polluting the project env
    @WHEEL=$(ls -t dist/desloppify-*.whl | head -n 1) && \
    echo "Smoke testing wheel: $WHEEL" && \
    {{ uv }} run --no-project --with "$WHEEL[full]" desloppify --help > /dev/null && \
    {{ uv }} run --no-project --with "$WHEEL[full]" {{ python }} -c "import importlib.metadata as m,sys; extras=set(m.metadata('desloppify').get_all('Provides-Extra') or []); required={'full','treesitter','python-security','scorecard'}; missing=required-extras; print('missing extras metadata:', sorted(missing)) if missing else None; sys.exit(1 if missing else 0)"
    @echo "Package smoke test passed."
