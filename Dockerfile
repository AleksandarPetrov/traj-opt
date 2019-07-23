FROM ubuntu:18.04

MAINTAINER Aleksandar Petrov <aleksandar@p-petrov.com>

# Install dependencies
RUN apt-get update && apt-get install -y \
    git \
    cmake \
    python3.7 \
    python3.7-dev \
    python3-pip \
    libboost-all-dev \
 && rm -rf /var/lib/apt/lists/*

RUN python3.7 -m pip install numpy scipy pygmo matplotlib pathos pyYAML

# Install pykep
RUN mkdir /pykep \
 && cd /pykep \
 && git init \
 && git remote add origin https://github.com/esa/pykep.git \
 && git fetch origin +refs/tags/v2.3\
 && git reset --hard FETCH_HEAD \
 && mkdir build \
 && cd build \
 && cmake ../ -DBUILD_PYKEP="ON"  -DPYTHON_EXECUTABLE="/usr/bin/python3.7m" \
 && make \
 && make install \
 && cd / \
 && rm -r pykep

RUN mkdir /files
COPY *py /files/
