#!/usr/bin/env bash
set -euo pipefail
# Use the repository root as the build context so the Dockerfile COPY
# instructions read the canonical requirements files at the repo root;
# no files are duplicated on disk.
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "${script_dir}/../../../.." && pwd)"
docker buildx build --load -t floriaan1/ecgprocess:py313 \
    -f "${script_dir}/Dockerfile" "${repo_root}"
