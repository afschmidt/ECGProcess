#!/bin/sh
# Dot-sourced under real dash locally, so stays POSIX (no "pipefail").
set -eu
# This is assumed to be running from the root of the repo, after
# resources/ci_cd/before_script.sh has installed the base package.

# Phase 1: run the tests WITHOUT any optional dependencies installed
# (the docker image deliberately does not bake them in). tensorflow-
# and wfdb-marked tests skip and the lazy-import guarantees are
# exercised in a genuinely dependency-free environment.
pytest tests

# Phase 2: install every optional extra and re-run the full suite,
# but only on the newest supported version (PYTHON_TAG=py313) so CI
# doesn't pay the tensorflow/wfdb install cost on every matrix leg.
if [ "${PYTHON_TAG:-}" = "py313" ]; then
    pip install .[all]
    pytest tests
fi
