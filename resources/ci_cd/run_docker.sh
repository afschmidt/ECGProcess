#!/bin/bash
# Run a test build using docker on local PC, this can be used to debug CI/CD
# gitlab builds without repeated commits. The documentation is uploaded to
# pCloud static web pages for viewing.
# This will create a container called gwas_norm and do the build before closing
# and removing the container. The container will also be removed on error.
# Usage
# ./run_docker.sh <image name> <repo_root>
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

# The docker image to use is the first argument and the repository root is
# the second
image="$1"
repo_root="$(readlink -f "$2")"
repo_base="$(basename "$repo_root")"

# Set up the documentation build dir
build_dir=$HOME/pCloudDrive/Public\ Folder/skeleton-package/
build_dir=${3:-"$build_dir"}
mkdir -p "$build_dir"

# This will be the working directory in the docker image, this corresponds to
# the repository root
workdir="/tests"
echo "[info] starting directory: $PWD"
echo "[info] repo root: $repo_root"

echo "[info] starting container..."
docker run \
       -w "$workdir" \
       --name "$container_name" \
       -dit "$image" /bin/sh

# -v "$repo_root":/"$workdir" \
echo "[info] copying repo to docker..."
# copying .ssh directory to docker
# docker exec "$container_name" mkdir -p "/root/.ssh"
# export SSH_PRIVATE_KEY="/root/.ssh/.private_key"
# tar cf - -C "$HOME" .ssh | docker exec -i "$container_name" \
#     tar xf - -C /root \
#     && docker exec "$container_name" cp /root/.ssh/gitlab /root/.ssh/.private_key \
#     && docker exec "$container_name" chown -R root:root /root/.ssh \
#     && docker exec "$container_name" chmod -R 400 /root/.ssh \
#     && echo "HOST *" | docker exec -i "$container_name" tee -a /root/.ssh/config \
#     && echo "IdentityFile $SSH_PRIVATE_KEY" | docker exec -i "$container_name" tee -a /root/.ssh/config \
#     && echo "IdentitiesOnly yes" | docker exec -i "$container_name" tee -a /root/.ssh/config \
#     && echo "StrictHostKeyChecking no" | docker exec -i "$container_name" tee -a /root/.ssh/config
# # confirm ssh settings
# docker exec "$container_name" ls -la /root/.ssh
# docker exec "$container_name" cat /root/.ssh/config
# docker exec "$container_name" chmod -R 400 "/root/.ssh"
docker container cp "$repo_root" "$container_name":"$workdir"/
echo "[info] executing build..."
# docker exec "$container_name" /bin/sh
docker exec --workdir "${workdir}"/"$repo_base" "$container_name" \
       /bin/sh "${workdir}"/"$repo_base"/resources/ci_cd/run_pages.sh
echo "[info] copying from docker..."

docker container cp "$container_name":"${workdir}"/"$repo_base"/public "$temp_dir"

cd "$repo_root"
rsync -avz "$temp_dir"/public/* "$build_dir"
echo "*** END ***"
