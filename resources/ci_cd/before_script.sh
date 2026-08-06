#!/bin/sh
# Dot-sourced under real dash locally, so stays POSIX (no "pipefail").
set -eu
# This is assumed to be running from the root of the repo
echo "[before] running in: $PWD"
# For debugging
echo $CI_COMMIT_BRANCH
echo $CI_DEFAULT_BRANCH
python --version
git branch

# Needed for Sphinx (make in build-base) and pysam (build-base + others)
apt-get update && apt-get install -y build-essential \
                bzip2 \
                zlib1g-dev \
                xz-utils \
                libssl-dev \
                libcurl4-openssl-dev \
                gfortran \
                libopenblas-dev \
                libffi-dev \
                cmake \
                make \
                pkg-config \
                git \
                python3-dev

# start ssh-agent
eval `ssh-agent -s`
# ssh-add -l

# Upgrade pip first
pip install --upgrade pip

# Package and dev requirements (includes sphinx)
pip install -r requirements-dev.txt
pip install -r requirements.txt


# Install the package being built/tested
pip install .
