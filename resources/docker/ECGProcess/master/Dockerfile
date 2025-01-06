# Use a minimal Debian image with Pandoc
FROM pandoc/minimal:latest-static AS init
FROM python:3.12.8-bullseye AS build

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
    git \
    llvm-11-dev \
    python3-dev"

WORKDIR /data
COPY requirements.txt ./
COPY sphinx.txt ./

# Used for llvmlite and numba installation
ENV LLVM_CONFIG=/usr/bin/llvm-config-11

# Install build dependencies and Python packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends $BUILD_DEPS && \
    pip install --upgrade pip setuptools wheel && \
    # Install packages required by numba and statsmodels
    pip install "setuptools_scm[toml]" && \
    pip install "pandas>=2.1.1" && \
    pip install "numpy>=1.26" && \
    pip install "scipy>=1.7" && \
    pip install -r requirements.txt && \
    pip install -r sphinx.txt && \
    # Clean up
    apt-get purge -y --auto-remove $BUILD_DEPS && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Use a lightweight final image
FROM python:3.12.8-bullseye AS final

# Define persistent dependencies
ENV PERSISTENT_DEPS="libdeflate0 \
    libopenblas0 \
    libcurl4 \
    git \
    llvm-11 \
    sed"

# Set the LLVM config environment for numba
ENV LLVM_CONFIG=/usr/bin/llvm-config-11

WORKDIR /data

# Copy necessary files from the build stage
COPY --from=build /usr/local/bin /usr/local/bin
COPY --from=build /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=build /usr/local/share/jupyter /usr/local/share/jupyter
COPY --from=init /usr/local/bin/pandoc /usr/local/bin/

# Install persistent dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends $PERSISTENT_DEPS && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# running in sh
CMD ["sh"]

