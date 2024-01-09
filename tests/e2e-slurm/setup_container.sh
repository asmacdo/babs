#!/bin/bash -i

set -eu

# add that outside user
groupadd --gid "$GID" "$USER"  && useradd --uid $UID --gid "$GID" "$USER"

# Install singularity inside the container
yum update -y && yum install -y epel-release &&  yum update -y &&  yum install -y singularity-runtime apptainer

git version
git config user.name > /dev/null || git config --system user.name "e2e slurm"
git config user.email > /dev/null || git config --system user.email "fake@example.com"
git config --system --add safe.directory '*'

# Setup env to use conda
cat > /home/"$USER"/.bashrc << EOF
export MINICONDA_PATH=$MINICONDA_PATH
echo "HELLO ~/.bashrc is SOURCED"
echo $MINICONDA_PATH
EOF
chmod a+x /home/"$USER"/.bashrc
mkdir -p /home/"$USER"/.cache

chown -R "$USER":"$GID" /home/"$USER"/.cache

# so poor thing could write into bind mounted devel/babs/.testdata/
usermod -a -G root "$USER"

