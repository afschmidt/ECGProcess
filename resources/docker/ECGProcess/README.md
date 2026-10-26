# `docker` directory

This contains build files to build the docker images used for gitlab CI/CD
for this repo. These images are not docker images containing the actual
python package; they only provide the build/runtime dependencies needed to
install and test it.

One image exists per supported Python version, since `pyproject.toml`
declares `requires-python = ">=3.11, <3.15"` and the test stage runs the
suite against all supported versions:

| Tag | Python | Dockerfile |
|---|---|---|
| `py311` | 3.11 | `py311/Dockerfile` |
| `py312` | 3.12 | `py312/Dockerfile` |
| `py313` | 3.13 | `py313/Dockerfile` |
| `py314` | 3.14 | `py314/Dockerfile` |

`py314` also doubles as the default image used by the documentation deploy
job in `.gitlab-ci.yml`.

To build an image from scratch:

```sh
resources/docker/ECGProcess/py311/build.sh
```

Once built, an image can be pushed to docker hub as follows:

```sh
docker image list
docker push docker.io/floriaan1/ecgprocess:py311
```

Docker can be removed using `docker image prune -a`, where an existing image
can be pulled from docker hub by running

```sh
docker pull floriaan1/ecgprocess:py311
```
