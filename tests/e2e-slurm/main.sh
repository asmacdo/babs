#!/bin/bash
#
set -eux

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
THIS_DIR="$(readlink -f "$0" | xargs dirname )"
TESTDATA=/opt/testdata

. tests/e2e-slurm/container/ensure-env.sh

stop_container () {
	podman stop slurm || true
}

 # Because babs is dev-installed from here. TODO: we can remove if we remove -e from pip install
podman run -it --rm \
	--name slurm \
	--hostname slurmctl  \
	-e "MINICONDA_PATH=${MINICONDA_PATH}" \
	--privileged \
	-v "${PWD}:${PWD}:ro,Z" \
	-v "${MINICONDA_PATH}:${MINICONDA_PATH}:Z" \
	-v "${THIS_DIR}/container:/opt/outer:ro,Z" \
	"${FQDN_IMAGE}" \
	/bin/bash -c ". /opt/outer/walkthrough-tests.sh"

	#/bin/bash -c ". /opt/outer/walkthrough-tests.sh && bash" # TODO remove, for debug only
# trap stop_container EXIT
