#!/bin/bash

set -eu

# add that outside user (TODO: check if still needed)
groupadd --gid $(id -u) $USER  && useradd --uid $(id -u) --gid $(id -u) $USER 

# Install singularity inside the container
yum update -y && yum install -y epel-release &&  yum update -y &&  yum install -y singularity-runtime apptainer


