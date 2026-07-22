.PHONY: install install-dev
install:
	python -m pip install .

install-dev:
	python -m pip install -e ".[dev]"
	python .githooks/.setup_git_hooks.py
