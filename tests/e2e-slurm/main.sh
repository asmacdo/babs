#!/bin/bash
#
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

BABS_PROJECT=babs_test_project

cleanup () {
	echo "Shutting down slurm"
	podman stop slurm
	rm -rf $BABS_PROJECT
}

# TODO Can we autodetect this?
MINICONDA_PATH=${MINICONDA_PATH:=/usr/share/miniconda}

# START SLURM -------------------------------
	    # -e "PATH=${MINICONDA_PATH}:$PATH" # This wouldn't work...right? # TODO
	    # MINICONDA_PATH needs to be identical in and out?, conda expects? is that true? File RFE upstream?
podman run -d --rm \
	--name slurm \
	--hostname slurmctl  \
	--privileged \
	-v ${PWD}:${PWD}:Z \
	-v ${MINICONDA_PATH}:${MINICONDA_PATH}:Z \
	${FQDN_IMAGE} \
	tail -f /dev/null # hack to keep it running TODO file issue

trap cleanup EXIT

# Wait for slurm to be up
# Number of retries
max_retries=10
# Delay in seconds
delay=10

echo "Wait for Trying sacct until it succeeds"
set +e # We need to check the error code and allow failures until slurm has started up
export PATH=${PWD}/tests/e2e-slurm/bin/:${PATH}
for ((i=1; i<=max_retries; i++)); do
	# Don't print confusing error messages, this is expected to fail a time or a few
	sacct > /dev/null 2>&1

	# Check if the command was successful
	if [ $? -eq 0 ]; then
		echo "Slurm is up and running!"
		break
	else
		echo "Waiting for Slurm to start... retry $i/$max_retries"
		sleep $delay
	fi
	# exit if max retries reached
	if [ $i -eq $max_retries ]; then
		echo "Failed to start Slurm after $max_retries attempts."
	exit 1
    fi
done
set -e


pwd
mkdir $BABS_PROJECT
pushd $BABS_PROJECT
# TODO --where_project must be abspath file issue for relative path
babs-init \
    --where_project ${PWD} \
    --project_name test_project \
    --input BIDS https://osf.io/w2nu3/ \
    --container_ds ${PWD}/toybidsapp-container \
    --container_name toybidsapp-0-0-7 \
    --container_config_yaml_file ${PWD}/config_toybidsapp.yaml \
    --type_session multi-ses \
    --type_system slurm


# TODO: check file output of babs-init

# TODO: babs-check-status-nojob

# TODO: babs-check-status-job

popd
# /tests/e2e-slurm/babs-tests.sh
# podman exec  \
# 	-e MINICONDA_PATH=${MINICONDA_PATH} \
# 	slurm \
# 	${PWD}/tests/e2e-slurm/babs-tests.sh 
#


echo "--------------------------"
echo "     HUZZZZZZAHHHHHH!!!!!!"
echo "--------------------------"

