#!/bin/sh
# Dot-sourced under real dash locally, so stays POSIX (no "pipefail").
set -eu
# This is assumed to be running from the root of the repo
echo "[pages] running in: $PWD"

# Ensure the documentation build directory is present
mkdir -p ./docs/build

cd docs
make html
cd ..

echo "[pages] removing public"
if [ -e public ]; then
    rm -r public
fi
echo "[pages] creating public"
mkdir -p public
echo "[pages] moving HTML to public"
mv docs/build/html/* public/
echo "[pages] PWD: $PWD"
echo "[pages] contents of public"
ls "$PWD"/public
