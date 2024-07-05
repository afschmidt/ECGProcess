#!/bin/sh
# This is assumed to be running from the root of the repo
echo "[before] running in: $PWD"
# For debugging
echo $CI_COMMIT_BRANCH
echo $CI_DEFAULT_BRANCH
python --version
git branch

# Needed for Sphinx (make in build-base) and pysam (build-base + others)
apk add build-base bzip2-dev zlib-dev xz-dev openblas-dev linux-headers openssh

# start ssh-agent
eval `ssh-agent -s`
# ssh-add -l

# Upgrade pip first
pip install --upgrade pip

# Sphinx doc building requirements
pip install -r resources/ci_cd/sphinx.txt

# install cython to support statsmodels and scipy installs.
# pip install Cython --no-binary :all:
# # install merit requirements
# git clone git@gitlab.com:cfinan/merit.git
# cd merit
# python -m pip install --upgrade -r requirements.txt
# cd ..
# rm -rf merit

# Package requirements
pip install -r requirements.txt


# Install the package being built/tested
pip install .

# Run all the tests
pytest tests
