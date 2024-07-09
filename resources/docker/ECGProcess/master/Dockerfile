FROM pandoc/minimal:latest-static AS init
FROM python:3.12.4-alpine3.19 AS build

ENV BUILD_DEPS="build-base \
    bzip2-dev \
    zlib-dev \
    xz-dev \
    openssl-dev \
    curl-dev \
    gfortran \
    openblas-dev \
    linux-headers \
    openssh \
    libffi-dev \
    libdeflate-dev \
    cmake \
    pkgconf \
    gcc \
    musl-dev \
    git"

WORKDIR /data
COPY requirements.txt ./
COPY sphinx.txt ./

# Used for llvmlist and numba install
# ENV LLVM_CONFIG=/usr/bin/llvm11-config
RUN apk upgrade --update && \
    apk add --no-cache --virtual .build-deps $BUILD_DEPS && \
    pip install --upgrade pip && \
    pip install --upgrade pip setuptools && \
    pip install "setuptools_scm[toml]" && \
    pip install "pandas>=2.1.1" && \
    pip install "numpy>=1.26" && \
    pip install "scipy>=1.7" && \
    pip install -r requirements.txt && \
    pip install -r sphinx.txt && \
    apk del .build-deps

FROM python:3.12.4-alpine3.19 AS final
ENV PERSISTENT_DEPS="libdeflate \
    openblas \
    curl \
    git \
    sed"
# Used for llvmlist and numba install
# ENV LLVM_CONFIG=/usr/bin/llvm11-config

WORKDIR /data
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/share/jupyter /usr/local/share/jupyter
COPY --from=init /pandoc /usr/local/bin/

RUN apk upgrade --update && \
    apk add --virtual .persistent-deps $PERSISTENT_DEPS
