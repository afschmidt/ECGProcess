# Use a minimal Debian image with Pandoc
FROM pandoc/minimal:latest-static AS init
FROM python:3.13-slim-bookworm AS build

# Define build dependencies
ENV BUILD_DEPS="build-essential \
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
    git"

WORKDIR /data
COPY requirements.txt ./
COPY requirements-dev.txt ./

# Install build dependencies and Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends $BUILD_DEPS && \
    pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install -r requirements-dev.txt && \
    apt-get purge -y --auto-remove $BUILD_DEPS && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Use a lightweight final image
FROM python:3.13-slim-bookworm AS final

# Define persistent dependencies
ENV PERSISTENT_DEPS="libdeflate0 \
    libopenblas0 \
    libffi8 \
    libssl3 \
    libcurl4 \
    git \
    sed"

WORKDIR /data

# Copy necessary files from the build stage
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=build /usr/local/share/jupyter /usr/local/share/jupyter
COPY --from=init /usr/local/bin/pandoc /usr/local/bin/

# Install persistent dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends $PERSISTENT_DEPS && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# running in sh
CMD ["sh"]
