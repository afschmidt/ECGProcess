#!/bin/bash
# Run a test build using docker on local PC, this can be used to debug CI/CD
# gitlab builds without repeated commits. The documentation is uploaded to
# pCloud static web pages for viewing.
# This will create a container called ecgprocess and do the build before closing
# and removing the container. The container will also be removed on error.
# Usage
# ./run_docker.sh <image> <repo_root> [build_dir] [mode]
#   mode "pages" (default) runs before_script+run_tests+pages and rsyncs
#                output to build_dir
#   mode "test"            runs before_script+run_tests only (no rsync,
#                build_dir ignored)
container_name="ecgprocess"
init_dir="$PWD"
temp_dir=$(mktemp -d)

stop_docker() {
    echo "[info] stopping container..."
    docker stop "$container_name"
    echo "[info] removing container..."
    docker rm "$container_name"
    rm -r "$temp_dir"
    cd "$init_dir"
}
trap stop_docker EXIT INT SIGHUP SIGINT SIGQUIT SIGABRT SIGTERM ERR
set -eu

image="$1"
repo_root="$(cd "$2" && pwd -P)"
repo_base="$(basename "$repo_root")"
default_build_dir="$HOME/pCloudDrive/Public Folder/skeleton-package/"
build_dir="${3:-$default_build_dir}"
mode="${4:-pages}"

workdir="/tests"
echo "[info] starting directory: $PWD"
echo "[info] repo root: $repo_root"
echo "[info] mode: $mode"

if [[ "$mode" == "pages" ]]; then
    mkdir -p "$build_dir"
fi

echo "[info] starting container..."
docker run \
       -w "$workdir" \
       --name "$container_name" \
       -dit "$image" /bin/sh

echo "[info] copying repo to docker..."
docker container cp "$repo_root" "$container_name":"$workdir"/

if [[ "$mode" == "test" ]]; then
    inner_script="${workdir}/${repo_base}/resources/ci_cd/run_tests.sh"
else
    inner_script="${workdir}/${repo_base}/resources/ci_cd/run_pages.sh"
fi

echo "[info] executing build (mode: $mode)..."
docker exec --workdir "${workdir}"/"$repo_base" "$container_name" \
       /bin/sh "$inner_script"

if [[ "$mode" == "pages" ]]; then
    echo "[info] copying from docker..."
    docker container cp "$container_name":"${workdir}"/"$repo_base"/public "$temp_dir"
    cd "$repo_root"
    rsync -avz "$temp_dir"/public/* "$build_dir"
fi
echo "*** END ***"
