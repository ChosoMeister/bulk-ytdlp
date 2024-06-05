# Use a suitable base image
FROM debian:stable-slim

# Set environment variables
ENV LANG=C.UTF-8 \
    PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
    GPG_KEY=E3FF2839C048B25C084DEBE9B26995E310250568 \
    PYTHON_VERSION=3.9.18 \
    PYTHON_SETUPTOOLS_VERSION=58.1.0 \
    PYTHON_PIP_VERSION=23.0.1 \
    PYTHON_GET_PIP_URL=https://github.com/pypa/get-pip/raw/9af82b715db434abb94a0a6f3569f43e72157346/public/get-pip.py \
    PYTHON_GET_PIP_SHA256=45a2bb8bf2bb5eff16fdd00faef6f29731831c7c59bd9fc2bf1f3bed511ff1fe

# Install essential packages and dependencies
RUN set -eux; \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    gnupg \
    wget \
    bzip2 \
    libfontconfig \
    libjpeg-dev \
    libpng-dev \
    libssl-dev \
    libxml2-dev \
    libxslt-dev \
    zlib1g-dev \
    libpq-dev \
    libffi-dev \
    libyaml-dev \
    make \
    gcc \
    g++ \
    libc6-dev \
    libsqlite3-dev \
    libbz2-dev \
    liblzma-dev \
    tk-dev \
    uuid-dev && \
    rm -rf /var/lib/apt/lists/*

# Install Python from source
RUN set -eux; \
    wget -O python.tar.xz "https://www.python.org/ftp/python/${PYTHON_VERSION%%[a-z]*}/Python-$PYTHON_VERSION.tar.xz"; \
    wget -O python.tar.xz.asc "https://www.python.org/ftp/python/${PYTHON_VERSION%%[a-z]*}/Python-$PYTHON_VERSION.tar.xz.asc"; \
    GNUPGHOME="$(mktemp -d)"; export GNUPGHOME; \
    gpg --batch --keyserver hkps://keys.openpgp.org --recv-keys "$GPG_KEY"; \
    gpg --batch --verify python.tar.xz.asc python.tar.xz; \
    gpgconf --kill all; \
    rm -rf "$GNUPGHOME" python.tar.xz.asc; \
    mkdir -p /usr/src/python; \
    tar --extract --directory /usr/src/python --strip-components=1 --file python.tar.xz; \
    rm python.tar.xz; \
    cd /usr/src/python; \
    gnuArch="$(dpkg-architecture --query DEB_BUILD_GNU_TYPE)"; \
    ./configure --build="$gnuArch" --enable-loadable-sqlite-extensions --enable-optimizations --enable-option-checking=fatal --enable-shared --with-system-expat --without-ensurepip; \
    nproc="$(nproc)"; \
    make -j "$nproc"; \
    make install; \
    bin="$(readlink -ve /usr/local/bin/python3)"; \
    dir="$(dirname "$bin")"; \
    mkdir -p "/usr/share/gdb/auto-load/$dir"; \
    cp -vL Tools/gdb/libpython.py "/usr/share/gdb/auto-load/$bin-gdb.py"; \
    cd /; \
    rm -rf /usr/src/python; \
    find /usr/local -depth \( \( -type d -a \( -name test -o -name tests -o -name idle_test \) \) -o \( -type f -a \( -name '*.pyc' -o -name '*.pyo' -o -name 'libpython*.a' \) \) \) -exec rm -rf '{}' +; \
    ldconfig; \
    python3 --version

# Create symlinks for Python commands
RUN set -eux; \
    for src in idle3 pydoc3 python3 python3-config; do \
        dst="$(echo "$src" | tr -d 3)"; \
        [ -s "/usr/local/bin/$src" ]; \
        [ ! -e "/usr/local/bin/$dst" ]; \
        ln -svT "$src" "/usr/local/bin/$dst"; \
    done

# Install pip
RUN set -eux; \
    wget -O get-pip.py "$PYTHON_GET_PIP_URL"; \
    echo "$PYTHON_GET_PIP_SHA256 *get-pip.py" | sha256sum -c -; \
    export PYTHONDONTWRITEBYTECODE=1; \
    python get-pip.py --disable-pip-version-check --no-cache-dir --no-compile "pip==$PYTHON_PIP_VERSION" "setuptools==$PYTHON_SETUPTOOLS_VERSION"; \
    rm -f get-pip.py; \
    pip --version

# Set the working directory inside the container
WORKDIR /app/

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Install PhantomJS
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl; \
    mkdir /tmp/phantomjs; \
    curl -L https://bitbucket.org/ariya/phantomjs/downloads/phantomjs-2.1.1-linux-x86_64.tar.bz2 | tar -xj --strip-components=1 -C /tmp/phantomjs; \
    mv /tmp/phantomjs/bin/phantomjs /usr/local/bin; \
    apt-get purge --auto-remove -y curl; \
    apt-get clean; \
    rm -rf /tmp/* /var/lib/apt/lists/*

# Install ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy the rest of the application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8910/tcp

# Define the default command to run the application
CMD ["python3", "bot.py"]
