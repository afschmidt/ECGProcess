#!/bin/bash
parse_git_branch() {
    git branch 2> /dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/\1/'
}

abort() {
    echo "[info] aborting..." 1>&2
    cd "$curdir"
    exit 1
}
PROG_NAME="=== increment-version ==="
USAGE=$(
cat <<EOF
$PROG_NAME
Bump the version number. In most cases <version> should be
major, minor, patch or release, although this may depend on the
.bumpversion.cfg file.

USAGE: $0 [flags] <repo_root> <version>
EOF
)
. shflags

FLAGS_HELP="$USAGE"

# parse the command-line
FLAGS "$@" || exit $?
eval set -- "${FLAGS_ARGV}"

# Make sure the root directory is set
if [[ -z "$1" ]]; then
  echo "[error] no repo root defined" 2>&1
  exit 1
fi

# Make sure the root directory is set
if [[ -z "$2" ]]; then
  echo "[error] no version defined" 2>&1
  exit 1
fi

# exit on error and undef not allowed
set -eu

# source in some common functions
run_dir="$(dirname $0)"
. "$run_dir"/common.sh

ROOT_DIR=$(readlink -f "$1")
# Version should be major, minor, patch, release, build
VERSION="$2"

echo "$PROG_NAME"
echo "[info] repo root: $ROOT_DIR"
echo "[info] bumping version: $VERSION"

# Make sure all the expected files and dirs are available
# **** this also sets a load of variables that will be used below ****
check_repo "$ROOT_DIR"

curdir="$PWD"

trap 'abort' SIGINT

# Do a dry from
cd "$ROOT_DIR"
git_branch="$(parse_git_branch)"
bumpversion --list --dry-run "${VERSION}"

# Now ask the user if that is ok
echo "[${git_branch}] Do you want to increment the version? Press [ENTER] to increment or [CTRL-C] to quit? "
read GO

if [[ "$GO" == "" ]]; then
    echo "[${git_branch}] bumping version number..."
    bumpversion "${VERSION}"
    echo "[${git_branch}] pushing..."
    git push origin "$git_branch" --follow-tags
    # Not sure if this is needed? - need to test
    # git push --tags
fi

cd "$curdir"
echo "*** END ***"
