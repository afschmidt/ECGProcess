#!/bin/bash
# A script to run before_script + test inside the Docker container.
# Not designed to be run by GitLab; for local reproduction of the test-matrix
# stage via debug_run_docker.sh (mode=test).
# It is assumed that you are in the repo root as the working directory.

ci_cd="resources/ci_cd"

root_dir=$(basename "$PWD")
echo "[run_tests] root_dir=$root_dir"

# Spoof GitLab CI variables for scripts that reference them
CI_COMMIT_BRANCH=dev
CI_DEFAULT_BRANCH=dev

git config --global --add safe.directory "$PWD"

. "$ci_cd"/before_script.sh
. "$ci_cd"/test.sh

echo "*** END run_tests.sh ***"
