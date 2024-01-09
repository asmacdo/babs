#!/bin/bash -i

set -eu

# add that outside user
groupadd --gid "$GID" "$USER"  && useradd --uid $UID --gid "$GID" "$USER"

# Install singularity inside the container
yum update -y && yum install -y epel-release &&  yum update -y &&  yum install -y singularity-runtime apptainer

git config user.name > /dev/null || git config --global user.name "e2e slurm"
git config user.email > /dev/null || git config --global user.email "fake@example.com"

# Setup env to use conda
cat > /home/"$USER"/.bashrc << EOF
export MINICONDA_PATH=$MINICONDA_PATH
echo "HELLO IM SOURCED"
echo $MINICONDA_PATH
EOF
chmod a+x /home/"$USER"/.bashrc
mkdir -p /home/"$USER"/.cache

chown -R "$USER":"$GID" /home/"$USER"/.cache
