set -ex

# Expects: Conda env to be activated
# Expects: Babs to be installed
#
# WIP-NOT-WORKING
# Reminder :Z for selinux

# TODO switch back to upstream after build
# Currently using asmacdo, OpenSSL bump upstream, but no new docker build
# https://github.com/giovtorres/docker-centos7-slurm/pull/49
REGISTRY=docker.io
HUBUSER=asmacdo
# HUBUSER=giovtorres
REPO=centos7-slurm
# REPO=docker-centos7-slurm
TAG=23.11.07 # TODO

FQDN_IMAGE=${REGISTRY}/${HUBUSER}/${REPO}:${TAG}

# START SLURM -------------------------------
	    # -h slurmctl  \ # TODO WHY
	    # --cap-add sys_admin \ # TODO WHY
	    # --privileged \ # TODO WHY
	    # -e "PATH=${MINICONDA_PATH}:$PATH" # This wouldn't work...right? # TODO
	    # -e "UID=$$(id -u)" \ TODO learn wtf once and for all
	    # -e "GID=$$(id -g)" \
	    # -e "USER=$$USER" \
	    # MINICONDA_PATH needs to be identical in and out?, conda expects? is that true? File RFE upstream?
podman run --rm \
	    -v ${PWD}:${PWD}:Z \
	    -v ${MINICONDA_PATH}:${MINICONDA_PATH}:Z \
	    ${FQDN_IMAGE}

export PATH=${PWD}/bin/:${PATH}

sacct

# TODO babs-init

# TODO: check file output of babs-init

# TODO: babs-check-status-nojob

# TODO: babs-check-status-job


echo "--------------------------"
echo "     HUZZZZZZAHHHHHH!!!!!!"
echo "--------------------------"

