#!/bin/bash

set -eu

# add that outside user
groupadd --gid $GID $USER  && useradd --uid $UID --gid $GID $USER

# Install singularity inside the container
yum update -y && yum install -y epel-release &&  yum update -y &&  yum install -y singularity-runtime apptainer

git config user.name > /dev/null || git config --global user.name "e2e slurm"
git config user.email > /dev/null || git config --global user.email "fake@example.com"

# Setup env to use conda
cat > ~/.bashrc << EOF
. "\$MINICONDA_PATH/etc/profile.d/conda.sh"
conda activate \${CONDA_DEFAULT_ENV:-babs}  # TODO: remove default?
EOF
