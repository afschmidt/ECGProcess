# CI/CD scripts

These scripts let you reproduce the full GitLab CI/CD pipeline locally so
failures can be debugged without repeated commits to GitLab.

## How the pieces fit together

```
debug_run_docker.sh          ← single entry point for local use
        │
        └─▶ run_docker.sh   ← spins up a Docker container and dispatches
                │                to an inner script based on mode
                ├─▶ run_tests.sh   (mode=test)   ← test stage
                │       ├── before_script.sh
                │       └── test.sh
                │
                └─▶ run_pages.sh  (mode=pages)  ← deploy stage
                        ├── before_script.sh
                        ├── test.sh
                        └── pages.sh
```

The inner scripts (`run_tests.sh`, `run_pages.sh`) are not designed to be
run directly; they are copied into the container by `run_docker.sh` and
executed there.

## File descriptions

### Host-side scripts (macOS and Linux)

| File | Purpose |
|---|---|
| `debug_run_docker.sh` | **Start here.** Reproduces the full pipeline locally: loops over all Python-version test images then runs the pages deploy. Reads image names and test tags from `.gitlab-ci.yml` automatically; all defaults can be overridden with env vars (`IMAGE_BASE`, `TEST_TAGS`, `PAGES_TAG`, `BUILD_DIR`). Runs a docker pre-flight check before doing anything. |
| `run_docker.sh` | Low-level Docker wrapper called by `debug_run_docker.sh`. Starts a named container, copies the repo into it, dispatches to the appropriate inner script, and cleans up on exit. Accepts `mode=test` (no rsync) or `mode=pages` (rsyncs rendered docs to `build_dir`). |

### Inner scripts (run inside the Docker container)

| File | Purpose |
|---|---|
| `before_script.sh` | Installs build dependencies via `apt-get` and pip-installs `requirements.txt`, `requirements-dev.txt`, and the package itself. Sourced by both `run_tests.sh` and `run_pages.sh`. |
| `test.sh` | Runs the pytest suite: once without optional dependencies installed (tensorflow-/wfdb-marked tests skip), then once with `.[all]` installed. Sourced after `before_script.sh` in both the test and pages pipelines. |
| `run_tests.sh` | Inside-container entry point for the **test stage**. Sets spoofed GitLab env vars, then sources `before_script.sh` and `test.sh`. |
| `run_pages.sh` | Inside-container entry point for the **deploy stage**. Sets spoofed GitLab env vars, then sources `before_script.sh`, `test.sh`, and `pages.sh` (docs build). |
| `pages.sh` | Runs `make html` in `docs/` and moves the output to `public/` for GitLab Pages. |

## Relationship to `.gitlab-ci.yml`

The GitLab pipeline has two active stages:

```
test stage   → calls before_script.sh (before_script) + test.sh (script)
               runs in parallel across py311 / py312 / py313 / py314 images

deploy stage → calls before_script.sh (before_script) + pages.sh (script)
               runs only on the default branch
```

`debug_run_docker.sh` reproduces this exactly: it runs the test stage
sequentially across all Python images, then runs the deploy stage.

## Usage

```bash
# Reproduce the full pipeline (test matrix + pages deploy)
resources/ci_cd/debug_run_docker.sh

# Override the Python versions to test
TEST_TAGS="py311 py313" resources/ci_cd/debug_run_docker.sh

# Send docs output to a custom directory
BUILD_DIR=/tmp/my-docs resources/ci_cd/debug_run_docker.sh

# Use a different image repository
IMAGE_BASE=myorg/ecgprocess resources/ci_cd/debug_run_docker.sh
```

## Docker images

Images are built from `resources/docker/ECGProcess/` and pushed to Docker Hub
under `floriaan1/ecgprocess`. One image per supported Python version:

| Tag | Python | Dockerfile |
|---|---|---|
| `py311` | 3.11 | `resources/docker/ECGProcess/py311/` |
| `py312` | 3.12 | `resources/docker/ECGProcess/py312/` |
| `py313` | 3.13 | `resources/docker/ECGProcess/py313/` |
| `py314` | 3.14 | `resources/docker/ECGProcess/py314/` |

Build and push an image:

```bash
bash resources/docker/ECGProcess/py313/build.sh
docker push floriaan1/ecgprocess:py313
```
