#!/bin/bash

set -eu

# add that outside user
groupadd --gid $GID $USER  && useradd --uid $UID --gid $GID $USER

# Install singularity inside the container
yum update -y && yum install -y epel-release &&  yum update -y &&  yum install -y singularity-runtime apptainer

# TODO delete, we are binding in git config
# git config user.name "e2e slurm"
# git config user.email "fake@example.com"
