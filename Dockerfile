# Toolchain image for the packetClassifier pipeline. Contains everything
# needed to build/run ClassBench-ng (Ruby + original ClassBench C++ tools),
# the C++ classifiers (CMake), and the Python pipeline -- nothing else.
#
# The repo is bind-mounted in at run time (see docker-compose.yml), not
# copied into the image, so editing source on the host is picked up
# immediately without an image rebuild. Compiled binaries land on the bind
# mount too, so they persist across `docker compose run` invocations.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    cmake \
    ruby \
    ruby-dev \
    rubygems \
    git \
    python3 \
    python3-pip \
    python3-numpy \
    && rm -rf /var/lib/apt/lists/*

RUN gem install open4 ruby-ip docopt ipaddress

WORKDIR /workspace
CMD ["bash"]
