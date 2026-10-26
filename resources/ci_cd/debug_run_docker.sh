#!/usr/bin/env bash
# ---------------------------------------------------------------
# debug_run_docker.sh -- portable wrapper around run_docker.sh
#
# Reproduces the full GitLab CI pipeline locally (test matrix then
# pages deploy) so failures can be debugged without committing to
# GitLab. Auto-detects the repo root from this script's own location,
# derives image names and test tags from .gitlab-ci.yml, and picks a
# sensible documentation build directory. All defaults can be overridden
# via environment variables.
#
# Usage:
#   resources/ci_cd/debug_run_docker.sh [--help]
#
# Environment overrides:
#   IMAGE_BASE   Docker image name without tag. Default: parsed from
#                <repo_root>/.gitlab-ci.yml top-level image name,
#                falling back to floriaan1/ecgprocess.
#   TEST_TAGS    Space-separated Python version tags to use in the test
#                stage. Default: parsed from the PYTHON_TAG matrix in
#                .gitlab-ci.yml.
#   PAGES_TAG    Tag used for the deploy (pages) job image. Default:
#                parsed from .gitlab-ci.yml top-level image tag,
#                falling back to py314.
#   BUILD_DIR    Directory to receive rendered docs. Default:
#                ${HOME}/google_drive/Research/ci_docs_builds/
#                <repo_basename>/ when that parent exists, otherwise
#                /tmp/<repo_basename>-docs.
#
# Pipeline stages reproduced:
#   test    -- runs before_script + pytest in each TEST_TAGS image
#              (parallel in CI; sequential here)
#   deploy  -- runs before_script + pytest + sphinx in the PAGES_TAG image
#
# Pre-flight: verifies that 'docker' is on PATH and the daemon is
# reachable. If not, prints OS-aware install/start hints and exits
# with a non-zero status without invoking run_docker.sh.
#
# Example:
#   resources/ci_cd/debug_run_docker.sh
#   IMAGE_BASE=myorg/ecgprocess TEST_TAGS="py311 py313" \
#       resources/ci_cd/debug_run_docker.sh
# ---------------------------------------------------------------

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    sed -n '2,/^# ---/p' "$0" | head -n -1 | sed -E 's/^# ?//'
    exit 0
fi

set -euo pipefail

readonly DEFAULT_IMAGE_BASE="floriaan1/ecgprocess"
readonly DEFAULT_TEST_TAGS="py311 py312 py313 py314"
readonly DEFAULT_PAGES_TAG="py314"
readonly PREFERRED_BUILD_PARENT="${HOME}/google_drive/Research/ci_docs_builds"
readonly DOCKER_INSTALL_URL="https://docs.docker.com/engine/install/"
readonly DOCKER_GET_URL="https://docs.docker.com/get-docker/"

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
log_info()  { echo "[info]  $(date '+%Y-%m-%d %H:%M:%S') $*"; }
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
log_warn()  { echo "[warn]  $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; }
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
log_error() { echo "[error] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2; }

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# -----------------------------------------------------------------------
# Print install hints for the current operating system to stderr.
#
# Parameters
# ----------
#   None.
#
# Returns
# -------
#   Always 0.
#
# Outputs
# -------
#   Multi-line install instructions to stderr, tailored by `uname -s`.
# -----------------------------------------------------------------------
print_docker_install_hint() {
    local os
    os="$(uname -s)"
    case "${os}" in
        Linux)
            log_error "Install Docker Engine: ${DOCKER_INSTALL_URL}"
            log_error "On Ubuntu/Debian, follow the apt instructions on that"
            log_error "page, then add yourself to the docker group:"
            log_error "  sudo usermod -aG docker \"\$USER\" && newgrp docker"
            ;;
        Darwin)
            log_error "Install Docker Desktop for macOS, e.g.:"
            log_error "  brew install --cask docker"
            log_error "or download from: ${DOCKER_GET_URL}"
            ;;
        *)
            log_error "Install Docker for your platform: ${DOCKER_GET_URL}"
            ;;
    esac
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# -----------------------------------------------------------------------
# Verify docker is installed and the daemon is reachable.
#
# Parameters
# ----------
#   None.
#
# Returns
# -------
#   0 if docker is usable. Calls `exit 1` otherwise (does not return).
#
# Outputs
# -------
#   Diagnostic messages to stderr on failure, an info line on success.
# -----------------------------------------------------------------------
check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is not installed (no 'docker' on PATH)."
        print_docker_install_hint
        exit 1
    fi
    if ! docker info >/dev/null 2>&1; then
        log_error "Docker is installed but the daemon is not reachable."
        log_error "Start it (e.g. 'sudo systemctl start docker') and"
        log_error "ensure your user is in the 'docker' group, or re-run"
        log_error "with sudo."
        exit 1
    fi
    log_info "docker check passed"
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# -----------------------------------------------------------------------
# Resolve the base image name (without tag) from env or .gitlab-ci.yml.
#
# Parameters
# ----------
#   $1 - repo_root : Absolute path to the repository root.
#
# Returns
# -------
#   0 always.
#
# Outputs
# -------
#   Prints the image base (e.g. floriaan1/ecgprocess) to stdout.
#   Honours IMAGE_BASE env var first, then parses .gitlab-ci.yml's
#   top-level `image: { name: ... }` block and strips the tag,
#   then falls back to DEFAULT_IMAGE_BASE.
# -----------------------------------------------------------------------
resolve_image_base() {
    local repo_root="${1:?Error: repo_root required}"
    if [[ -n "${IMAGE_BASE:-}" ]]; then
        echo "${IMAGE_BASE}"
        return 0
    fi
    local parsed=""
    if [[ -f "${repo_root}/.gitlab-ci.yml" ]]; then
        parsed="$(awk '/^image:/{f=1; next} f && /name:/{print $2; exit}' \
            "${repo_root}/.gitlab-ci.yml" 2>/dev/null || true)"
        parsed="${parsed%:*}"
    fi
    echo "${parsed:-${DEFAULT_IMAGE_BASE}}"
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# -----------------------------------------------------------------------
# Resolve the list of Python version tags to test from env or .gitlab-ci.yml.
#
# Parameters
# ----------
#   $1 - repo_root : Absolute path to the repository root.
#
# Returns
# -------
#   0 always.
#
# Outputs
# -------
#   Prints a space-separated list of tags (e.g. "py311 py312 py313")
#   to stdout. Honours TEST_TAGS env var first, then parses the
#   PYTHON_TAG matrix from .gitlab-ci.yml, then falls back to
#   DEFAULT_TEST_TAGS.
# -----------------------------------------------------------------------
resolve_test_tags() {
    local repo_root="${1:?Error: repo_root required}"
    if [[ -n "${TEST_TAGS:-}" ]]; then
        echo "${TEST_TAGS}"
        return 0
    fi
    local parsed=""
    if [[ -f "${repo_root}/.gitlab-ci.yml" ]]; then
        parsed="$(awk '/PYTHON_TAG:/{gsub(/.*\[|\]|,/, ""); gsub(/^ +| +$/, ""); gsub(/ +/, " "); print; exit}' \
            "${repo_root}/.gitlab-ci.yml" 2>/dev/null || true)"
    fi
    echo "${parsed:-${DEFAULT_TEST_TAGS}}"
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# -----------------------------------------------------------------------
# Resolve the tag for the pages deploy image from env or .gitlab-ci.yml.
#
# Parameters
# ----------
#   $1 - repo_root : Absolute path to the repository root.
#
# Returns
# -------
#   0 always.
#
# Outputs
# -------
#   Prints the tag string to stdout. Honours PAGES_TAG
#   env var first, then parses the tag from .gitlab-ci.yml's top-level
#   image name, then falls back to DEFAULT_PAGES_TAG.
# -----------------------------------------------------------------------
resolve_pages_tag() {
    local repo_root="${1:?Error: repo_root required}"
    if [[ -n "${PAGES_TAG:-}" ]]; then
        echo "${PAGES_TAG}"
        return 0
    fi
    local parsed=""
    if [[ -f "${repo_root}/.gitlab-ci.yml" ]]; then
        parsed="$(awk '/^image:/{f=1; next} f && /name:/{print $2; exit}' \
            "${repo_root}/.gitlab-ci.yml" 2>/dev/null || true)"
        parsed="${parsed##*:}"
    fi
    echo "${parsed:-${DEFAULT_PAGES_TAG}}"
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# -----------------------------------------------------------------------
# Resolve the documentation build directory.
#
# Parameters
# ----------
#   $1 - repo_base : Basename of the repository root.
#
# Returns
# -------
#   0 always.
#
# Outputs
# -------
#   Prints the resolved build dir to stdout. Honours BUILD_DIR env var
#   first, then prefers ${PREFERRED_BUILD_PARENT}/<repo_base>/ when
#   that parent directory exists (preserving the maintainer's existing
#   layout), and finally falls back to /tmp/<repo_base>-docs.
# -----------------------------------------------------------------------
resolve_build_dir() {
    local repo_base="${1:?Error: repo_base required}"
    if [[ -n "${BUILD_DIR:-}" ]]; then
        echo "${BUILD_DIR}"
        return 0
    fi
    if [[ -d "${PREFERRED_BUILD_PARENT}" ]]; then
        echo "${PREFERRED_BUILD_PARENT}/${repo_base}"
        return 0
    fi
    echo "/tmp/${repo_base}-docs"
}

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# -----------------------------------------------------------------------
# Entry point: resolve all defaults, run pre-flight, then run the test
# matrix and pages deploy stages via run_docker.sh.
#
# Parameters
# ----------
#   None.
#
# Returns
# -------
#   The exit code of the last run_docker.sh call.
# -----------------------------------------------------------------------
main() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
    local repo_root
    repo_root="$(cd "${script_dir}/../.." && pwd -P)"
    local repo_base
    repo_base="$(basename "${repo_root}")"
    local runner="${script_dir}/run_docker.sh"
    if [[ ! -x "${runner}" ]]; then
        log_error "run_docker.sh not found or not executable: ${runner}"
        exit 1
    fi
    local image_base
    image_base="$(resolve_image_base "${repo_root}")"
    local test_tags
    test_tags="$(resolve_test_tags "${repo_root}")"
    local pages_tag
    pages_tag="$(resolve_pages_tag "${repo_root}")"
    local build_dir
    build_dir="$(resolve_build_dir "${repo_base}")"
    log_info "repo root:  ${repo_root}"
    log_info "image base: ${image_base}"
    log_info "test tags:  ${test_tags}"
    log_info "pages tag:  ${pages_tag}"
    log_info "build dir:  ${build_dir}"
    check_docker
    for tag in ${test_tags}; do
        log_info "=== [test stage] ${image_base}:${tag} ==="
        "${runner}" "${image_base}:${tag}" "${repo_root}" /dev/null test
    done
    log_info "=== [deploy stage] ${image_base}:${pages_tag} ==="
    "${runner}" "${image_base}:${pages_tag}" "${repo_root}" "${build_dir}" pages
    log_info "*** ALL STAGES COMPLETE ***"
}

main "$@"
