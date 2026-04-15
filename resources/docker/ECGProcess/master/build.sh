#!/usr/bin/env bash
set -euo pipefail
docker buildx build --load -t floriaan1/ecgprocess:master .
