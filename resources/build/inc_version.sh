#!/usr/bin/env bash
set -euo pipefail

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Increment the package version using bump2version.
#
# This script wraps bump2version with a dry-run preview, user confirmation,
# CHANGELOG date insertion, and automatic push. Run from the resources/build
# directory (one level below the repo root where .bumpversion.cfg lives).
#
# Parameters
# ----------
#   $1 - version_part : The version part to bump (major, minor, or patch).
#
# Example
# -------
#   cd resources/build
#   bash inc_version.sh patch
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

readonly CURDIR="${PWD}"
readonly REPO_ROOT="$(cd ../.. && pwd)"

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
cleanup() {
    cd "${CURDIR}"
}
trap cleanup EXIT

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
abort() {
    echo "[info] aborting..." >&2
    exit 1
}
trap 'abort' SIGINT

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# NOTE lists the local branches, finds and deletes all lines not starting with
# "*" so you only get the active branch name
parse_git_branch() {
    git branch 2>/dev/null | sed -e '/^[^*]/d' -e 's/* \(.*\)/\1/'
}

# NOTE moves to root, confirms the version is maj/min/patch, gets the
# git branch
cd "${REPO_ROOT}"
readonly VERSION="${1:?Error: version part required (major, minor, or patch)}"
readonly GIT_BRANCH="$(parse_git_branch)"

# Capture the new version from dry-run
readonly NEW_VER="$(bumpversion --list --dry-run "${VERSION}" \
    | grep '^new_version=' | cut -d= -f2)"

# #### Bumpversion dry run
# Show dry-run output
bumpversion --list --dry-run "${VERSION}"

# Confirm with user
echo "[${GIT_BRANCH}] New version will be ${NEW_VER}."
echo "Press [ENTER] to increment or [CTRL-C] to quit."
read -r _

# #### Actual bumpversion run
echo "[${GIT_BRANCH}] bumping version number..."
bumpversion "${VERSION}"

# #### Update the CHANGELOG.md
# Insert date after version heading in CHANGELOG.md
readonly TODAY="$(date '+%Y-%m-%d')"
sed -i "s/^### \[${NEW_VER}\]$/### [${NEW_VER}] - ${TODAY}/" CHANGELOG.md

# Add a fresh [Unreleased] section after the # Changelog heading
# NOTE find # Changelog$ and "a" appends "\n### [Unreleased]
sed -i '/^# Changelog$/a\\n### [Unreleased]' CHANGELOG.md

# Amend the bump commit to include CHANGELOG date and new Unreleased section
git add CHANGELOG.md
git commit --amend --no-edit

# ##### Add tag
# Re-tag (amending moved HEAD, so the old tag points to the wrong commit)
readonly TAG_NAME="v${NEW_VER}"
git tag -d "${TAG_NAME}"
git tag -a "${TAG_NAME}" -m "chore(release): bump version to ${NEW_VER}"

# ##### Push
echo "[${GIT_BRANCH}] pushing..."
git push origin "${GIT_BRANCH}" --follow-tags

echo "*** END ***"
