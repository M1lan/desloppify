.PHONY: \
	ci \
	ci-fast \
	lint \
	typecheck \
	arch \
	ci-contracts \
	integration-roslyn \
	tests \
	tests-full \
	sync-docs \
	package-smoke \
	install-hooks \
	install-ci-tools \
	install-full-tools

# PROJECT POLICY: every Python invocation MUST go through `uv`. Never call
# python/pip/pytest/mypy/ruff/twine/build directly. `uv` provisions the
# interpreter (per requires-python) and the locked dependency set.
UV ?= uv
IMPORTLINTER_CONFIG ?= .github/importlinter.ini
PYTEST_XML ?=
PYTEST_XML_FLAG := $(if $(PYTEST_XML),--junitxml=$(PYTEST_XML),)

sync-docs:
	mkdir -p desloppify/data/global
	find desloppify/data/global -maxdepth 1 -type f -name '*.md' -delete
	cp docs/*.md desloppify/data/global/

install-hooks:
	@mkdir -p .git/hooks
	@if command -v prek >/dev/null 2>&1; then \
		prek install >/dev/null 2>&1 && echo "prek hooks installed (banned-word + legacy docs-sync)."; \
	else \
		cp .githooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit && echo "Git hooks installed."; \
	fi

install-ci-tools: install-hooks
	$(UV) sync

install-full-tools: install-hooks
	$(UV) sync --extra full

lint: install-ci-tools
	$(UV) run ruff check . --select E9,F63,F7,F82

typecheck: install-ci-tools
	$(UV) run mypy

arch: install-ci-tools
	@if [ ! -f "$(IMPORTLINTER_CONFIG)" ]; then \
		echo "Missing $(IMPORTLINTER_CONFIG). Add import contracts before running arch gate."; \
		exit 1; \
	fi
	$(UV) run lint-imports --config $(IMPORTLINTER_CONFIG)

ci-contracts: install-ci-tools
	$(UV) run pytest -q desloppify/tests/ci/test_ci_contracts.py
	$(UV) run pytest -q desloppify/tests/commands/test_lifecycle_transitions.py -k "assessment_then_score_when_no_review_followup"

integration-roslyn: install-ci-tools
	$(UV) run pytest -q desloppify/tests/lang/csharp/test_csharp_deps.py -k "roslyn"

tests: install-ci-tools
	$(UV) run pytest -q $(PYTEST_XML_FLAG)

tests-full: install-full-tools
	$(UV) run --extra full pytest -q $(PYTEST_XML_FLAG)

package-smoke: install-ci-tools
	rm -rf dist
	$(UV) build
	$(UV) run --with twine twine check dist/*
	@WHEEL=$$(ls -t dist/desloppify-*.whl | head -n 1) && \
		$(UV) run --no-project --with "$$WHEEL[full]" python -c "from importlib.resources import files; from pathlib import Path; docs=Path('docs'); bundled=files('desloppify.data.global'); names=sorted(p.name for p in docs.glob('*.md')); assert names; missing=[name for name in names if not bundled.joinpath(name).is_file()]; assert not missing, f'missing bundled docs: {missing}'; mismatched=[name for name in names if bundled.joinpath(name).read_text(encoding='utf-8') != (docs / name).read_text(encoding='utf-8')]; assert not mismatched, f'mismatched bundled docs: {mismatched}'" && \
		$(UV) run --no-project --with "$$WHEEL[full]" python -c "import importlib.metadata as m,sys; extras=set(m.metadata('desloppify').get_all('Provides-Extra') or []); required={'full','treesitter','python-security','scorecard'}; missing=required-extras; print('missing extras metadata:', sorted(missing)) if missing else None; sys.exit(1 if missing else 0)" && \
		$(UV) run --no-project --with "$$WHEEL[full]" desloppify --help > /dev/null

ci-fast: lint typecheck arch ci-contracts tests

ci: ci-fast tests-full package-smoke
