#!/bin/bash
# A script to initialise the dock building within the docker container. This
# is not designed to be run by gitlab , rather for local tests of gitlab
# CI/CD scripts inside the docker container.
# It is assumed that you are in the repo mounted as the working directory
# echo "[info] current dir (start)"
# ls -lah

if [ -e ./docs/build ]; then
    rm -r ./docs/build
fi

# removing cache
for cache_dir in \
    ./docs/.jupyter_cache \
    ./docs/source/.jupyter_cache \
    ./.jupyter_cache; do
    if [ -e "$cache_dir" ]; then
        echo "[run_pages] removing $cache_dir"
        rm -rf "$cache_dir"
    fi
done

# This is the directory where all the CI/CD scripts are located
ci_cd="resources/ci_cd"

# Run in the root of the repo
root_dir=$(basename "$PWD")
echo "[run_pages] root_dir=$root_dir"
# Spoof these values that are gitlab variables
# NOTE DOES NOT DO ANYTHING 
CI_COMMIT_BRANCH=dev
CI_DEFAULT_BRANCH=dev

# Make sure git likes our mounted tests dir
git config --global --add safe.directory "$PWD"

# Now run the CI/CD scripts
. "$ci_cd"/before_script.sh
. "$ci_cd"/pages.sh

echo "[info] current dir (end)"
ls -lah
echo "*** END run_pages.sh ***"
