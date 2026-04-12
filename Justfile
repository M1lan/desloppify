# Justfile for desloppify -- Multi-language codebase health scanner
# https://github.com/peteromallet/desloppify
#
# Python 3.11+ project managed with uv. Supports 29 languages.
# Run `just` (no args) to list all recipes.

# ===========================================================================
# Settings
# ===========================================================================

set shell := ["bash", "-euo", "pipefail", "-c"]
set positional-arguments := true
set dotenv-load := false

# ===========================================================================
# Variables (override on CLI: just python=python3.12 tests)
# ===========================================================================

python  := env("PYTHON", "python3")
uv      := env("UV", "uv")
srcdir  := justfile_directory()
pkgname := "desloppify"
version := `sed -n 's/^version *= *"\(.*\)"/\1/p' pyproject.toml`

# ===========================================================================
# Default / interactive
# ===========================================================================

# Interactive recipe picker (requires fzf)
[no-cd]
default:
    @just --choose 2>/dev/null || just --list --unsorted

# Show all available recipes
list:
    @just --list --unsorted

# ===========================================================================
# Dependencies
# ===========================================================================

# Sync project dependencies (all extras + dev)
install:
    {{ uv }} sync --all-extras --dev

# Install standalone single-file executable to ~/bin/
install-standalone:
    @mkdir -p ~/bin
    {{ uv }} run --with shiv --with pip shiv ".[full]" --console-script desloppify -o ~/bin/desloppify
    @echo "Installed standalone desloppify to ~/bin/desloppify"

# Update uv.lock to latest compatible versions
deps-update:
    {{ uv }} lock --upgrade

# Show dependency tree
deps-tree:
    {{ uv }} pip tree 2>/dev/null || {{ uv }} run pip list --format columns

# Verify required development dependencies are available
deps-check:
    @echo "Checking development dependencies..."
    @command -v {{ uv }} >/dev/null || { echo "error: uv not found -- install via: curl -LsSf https://astral.sh/uv/install.sh | sh" >&2; exit 1; }
    @command -v {{ python }} >/dev/null || { echo "error: {{ python }} not found" >&2; exit 1; }
    @{{ python }} -c "import sys; assert sys.version_info >= (3, 11), f'Python 3.11+ required, got {sys.version}'" \
        || { echo "error: Python 3.11+ required" >&2; exit 1; }
    @echo "All dependencies satisfied."

# Show build configuration
deps-show:
    @printf 'uv       = %s (%s)\n' "{{ uv }}" "$({{ uv }} --version 2>/dev/null)"
    @printf 'python   = %s (%s)\n' "{{ python }}" "$({{ python }} --version 2>/dev/null)"
    @printf 'version  = %s\n' "{{ version }}"
    @printf 'srcdir   = %s\n' "{{ srcdir }}"

# ===========================================================================
# Lint / Typecheck / Format
# ===========================================================================

# Run ruff linter (fatal errors only -- matches CI)
lint:
    {{ uv }} run ruff check . --select E9,F63,F7,F82

# Run full ruff lint (all configured rules)
lint-full:
    {{ uv }} run ruff check .

# Run ruff linter with auto-fix
lint-fix:
    {{ uv }} run ruff check . --fix

# Run type checker (mypy)
typecheck:
    {{ uv }} run mypy

# Format Python sources with ruff
fmt:
    {{ uv }} run ruff format .

# Check formatting without modifying files
fmt-check:
    {{ uv }} run ruff format --check .

# Run architectural contract checks (import-linter)
arch:
    @if [ ! -f ".github/importlinter.ini" ]; then \
        echo "Missing .github/importlinter.ini. Add import contracts before running arch gate."; \
        exit 1; \
    fi
    {{ uv }} run lint-imports --config .github/importlinter.ini

# ===========================================================================
# Testing
# ===========================================================================

# Run standard tests
tests *ARGS:
    {{ uv }} run pytest -q {{ ARGS }}

# Run full suite of tests with all extras
tests-full *ARGS:
    {{ uv }} run --extra full pytest -q {{ ARGS }}

# Run tests with verbose output and no capture
tests-verbose *ARGS:
    {{ uv }} run pytest -v --no-header -s {{ ARGS }}

# Run tests matching a keyword pattern (e.g. `just test-k "scan"`)
test-k pattern *ARGS:
    {{ uv }} run pytest -q -k "{{ pattern }}" {{ ARGS }}

# Run tests for a specific file
test-file file *ARGS:
    {{ uv }} run pytest -q "{{ file }}" {{ ARGS }}

# Run tests with coverage report
test-cov *ARGS:
    {{ uv }} run pytest --cov=desloppify --cov-report=term-missing --cov-report=html {{ ARGS }}
    @echo "HTML coverage report: htmlcov/index.html"

# Run CI specific contract tests
ci-contracts:
    {{ uv }} run pytest -q desloppify/tests/ci/test_ci_contracts.py
    {{ uv }} run pytest -q desloppify/tests/commands/test_lifecycle_transitions.py -k "assessment_then_score_when_no_review_followup"

# Run Roslyn integration tests
integration-roslyn:
    {{ uv }} run pytest -q desloppify/tests/lang/csharp/test_csharp_deps.py -k "roslyn"

# ===========================================================================
# Run
# ===========================================================================

# Run desloppify with arbitrary arguments
run *ARGS:
    {{ uv }} run desloppify {{ ARGS }}

# Scan the current directory
scan *ARGS:
    {{ uv }} run desloppify scan --path . {{ ARGS }}

# Show desloppify status
status:
    {{ uv }} run desloppify status

# Show next recommended action
next *ARGS:
    {{ uv }} run desloppify next {{ ARGS }}

# Show the execution plan
plan *ARGS:
    {{ uv }} run desloppify plan {{ ARGS }}

# ===========================================================================
# Packaging
# ===========================================================================

# Build package and verify extras metadata (smoke test)
package-smoke:
    rm -rf dist
    {{ uv }} build
    {{ uv }} run --with twine twine check dist/*
    @WHEEL=$(ls -t dist/desloppify-*.whl | head -n 1) && \
    echo "Smoke testing wheel: $WHEEL" && \
    {{ uv }} run --no-project --with "$WHEEL[full]" desloppify --help > /dev/null && \
    {{ uv }} run --no-project --with "$WHEEL[full]" {{ python }} -c "import importlib.metadata as m,sys; extras=set(m.metadata('desloppify').get_all('Provides-Extra') or []); required={'full','treesitter','python-security','scorecard'}; missing=required-extras; print('missing extras metadata:', sorted(missing)) if missing else None; sys.exit(1 if missing else 0)"
    @echo "Package smoke test passed."

# Build sdist and wheel
build-pkg:
    rm -rf dist
    {{ uv }} build

# ===========================================================================
# CI gauntlets
# ===========================================================================

# Run all CI fast checks (mirrors GitHub Actions ci-fast)
ci-fast: lint typecheck arch ci-contracts tests

# Run full CI suite including smoke tests
ci: ci-fast tests-full package-smoke
    @printf '\nFull CI passed.\n'

# Pre-commit: format, lint, typecheck, fast tests
pre-commit: fmt lint typecheck tests

# ===========================================================================
# Code quality / Search
# ===========================================================================

# Show all TODO/FIXME/HACK/XXX comments in source
todos:
    @rg -n 'TODO|FIXME|HACK|XXX|BUG' --type py || echo "None found."

# Search Python source for a pattern
search pattern:
    @rg "{{ pattern }}" --type py

# Show Python files with most lines (potential god modules)
largest-files:
    @fd -e py -t f . desloppify/ | xargs wc -l 2>/dev/null | sort -rn | head -20

# Count lines of code
loc:
    @if command -v tokei >/dev/null; then \
        tokei desloppify/; \
    elif command -v cloc >/dev/null; then \
        cloc desloppify/; \
    else \
        fd -e py -t f . desloppify/ | xargs wc -l | tail -1; \
    fi

# List all source files tracked by git
sources:
    @git ls-files '*.py' 2>/dev/null || fd -e py -t f

# Show test file count and distribution
test-stats:
    @echo "Test directories:"
    @fd -t d . desloppify/tests/ --max-depth 1 | while read d; do \
        count=$(fd -e py -t f . "$d" | wc -l | tr -d ' '); \
        printf "  %3d  %s\n" "$count" "$d"; \
    done
    @echo ""
    @total=$(fd -e py -t f . desloppify/tests/ | wc -l | tr -d ' '); \
    printf "Total test files: %s\n" "$total"

# ===========================================================================
# Documentation sync
# ===========================================================================

# Sync docs/ markdown into bundled package data
sync-docs:
    mkdir -p desloppify/data/global
    fd -e md --max-depth 1 . docs/ -x rm -f desloppify/data/global/{/}
    fd -e md --max-depth 1 . docs/ -x cp {} desloppify/data/global/{/}

# ===========================================================================
# Git hooks
# ===========================================================================

# Install git pre-commit hooks
install-hooks:
    @if [ -d .githooks ]; then \
        mkdir -p .git/hooks; \
        cp .githooks/pre-commit .git/hooks/pre-commit; \
        chmod +x .git/hooks/pre-commit; \
        echo "Git hooks installed from .githooks/."; \
    else \
        printf '#!/bin/sh\nexec just pre-commit\n' > .git/hooks/pre-commit; \
        chmod +x .git/hooks/pre-commit; \
        echo "Pre-commit hook installed (runs just pre-commit)."; \
    fi

# Uninstall git pre-commit hooks
uninstall-hooks:
    @rm -f .git/hooks/pre-commit
    @echo "Pre-commit hook uninstalled."

# ===========================================================================
# Housekeeping
# ===========================================================================

# Remove build artifacts, caches, and compiled bytecode
clean:
    rm -rf dist/ build/ *.egg-info htmlcov/ .coverage
    fd -I -g '*.pyc' -x rm -f {}
    fd -I -t d -g '__pycache__' -x rm -rf {}
    @echo "Cleaned."

# Aggressive clean: also remove .mypy_cache, .ruff_cache, .pytest_cache
distclean: clean
    rm -rf .mypy_cache/ .ruff_cache/ .pytest_cache/ .pkg-smoke/
    @echo "Deep cleaned."

# ===========================================================================
# Project info
# ===========================================================================

# Print version from pyproject.toml
version:
    @echo "{{ pkgname }} {{ version }}"

# Print full project info
info: deps-show
    @echo ""
    @just loc

# Show supported languages
languages:
    @{{ uv }} run {{ python }} -c "from desloppify.languages import available_langs; print('\n'.join(sorted(available_langs())))"

# ===========================================================================
# fzf helpers
# ===========================================================================

# Fuzzy-pick a Python source file to open in $EDITOR
fzf-edit:
    #!/usr/bin/env bash
    set -euo pipefail
    file=$(fd -e py -t f . desloppify/ | fzf --preview 'bat --color=always --style=numbers {}')
    [[ -n "${file}" ]] && "${EDITOR:-emacsclient -c}" "${file}"

# Fuzzy-pick a recipe to run
fzf:
    @just --choose

# Fuzzy-search source code and jump to match
fzf-grep:
    #!/usr/bin/env bash
    set -euo pipefail
    match=$(rg --line-number --no-heading '.' --type py | \
      fzf --delimiter ':' --preview 'bat --color=always --style=numbers --highlight-line {2} {1}')
    [[ -n "${match}" ]] && "${EDITOR:-emacsclient -c}" "+$(echo "${match}" | cut -d: -f2)" "$(echo "${match}" | cut -d: -f1)"

# Fuzzy-pick a class/function definition to jump to
fzf-def:
    #!/usr/bin/env bash
    set -euo pipefail
    match=$(rg -n '^\s*(def |class )' --type py | fzf --delimiter ':' \
      --preview 'bat --color=always --style=numbers --highlight-line {2} {1}')
    [[ -n "${match}" ]] && "${EDITOR:-emacsclient -c}" "+$(echo "${match}" | cut -d: -f2)" "$(echo "${match}" | cut -d: -f1)"

# Fuzzy-pick a test file to run
fzf-test:
    #!/usr/bin/env bash
    set -euo pipefail
    file=$(fd -e py -g 'test_*' . desloppify/tests/ | fzf --preview 'bat --color=always --style=numbers {}')
    [[ -n "${file}" ]] && just test-file "${file}"
