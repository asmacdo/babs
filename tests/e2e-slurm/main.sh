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

# TODO: shellcheck check/proof this script
THIS_DIR="$(readlink -f "$0" | xargs dirname )"
ROOT_DIR="$(echo "$THIS_DIR" | xargs dirname | xargs dirname)"
TESTDATA=$ROOT_DIR/.testdata
export LOGS_DIR=$TESTDATA/ci-logs

PROJECT_NAME=test_project
# TODO babs project vs test project name?
BABS_PROJECT_DIR=$TESTDATA/babs_test_project

# exported for use in inner-slurm.sh
# exported for use in config_toybidsapp.yaml TODO doesnt work, hardcoded there!
export MINICONDA_PATH=${MINICONDA_PATH:=/usr/share/miniconda}

source ./tests/e2e-slurm/ensure-env.sh

cleanup () {
	set +e
	echo "fake cleanup"
	# echo "Shutting down slurm"
	# podman stop slurm
	# echo "Slurm shim output --------------------------------------"
	# cat $LOGS_DIR/*
	# # DANGER set -u NECESSARY
	# set -u
	# echo "project logs: -----------------------"
	# cat $LOGS_DIR/*
	# TODO necessary to rerun locally
}

trap cleanup EXIT
mkdir -p $LOGS_DIR

# START SLURM -------------------------------
	    # -e "PATH=${MINICONDA_PATH}:$PATH" # This wouldn't work...right? # TODO
	    # MINICONDA_PATH needs to be identical in and out?, conda expects? is that true? File RFE upstream?
podman run --rm -d \
	-e "UID=$(id -u)" \
	-e "GID=$(id -g)" \
	-e "USER=$USER" \
	-e "MINICONDA_PATH=${MINICONDA_PATH}" \
	--name slurm \
	--hostname slurmctl  \
	--privileged \
    -v "$HOME/.gitconfig:/root/.gitconfig:ro,Z" \
    -v "$HOME/.gitconfig:/home/$USER/.gitconfig:ro,Z" \
	-v "${PWD}:${PWD}:Z" \
	-v "${MINICONDA_PATH}:${MINICONDA_PATH}:Z" \
    -v "${THIS_DIR}/setup_container.sh:/usr/local/sbin/setup_container.sh:ro,Z" \
	"${FQDN_IMAGE}" \
	/bin/bash -c "/usr/local/sbin/setup_container.sh && tail -f > /dev/null" # TODO keep these logs?

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
	echo "$PATH"
	sacct
	# sacct > /dev/null 2>&1

	# Check if the command was successful
	if [ $? -eq 0 ]; then
		echo "Slurm is up and running!"
		# TODO Error: executable file `git config --global user.name 'e2e slurm' &&  git config --global user.email 'fake@example.com'` not found in $PATH: No such file or directory: OCI runtime attempted to invoke a command that was not found
		# podman exec -it  slurm "git config --global user.name 'e2e slurm' &&  git config --global user.email 'fake@example.com'"
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

mkdir $BABS_PROJECT_DIR
cp ${PWD}/tests/e2e-slurm/config_toybidsapp.yaml $BABS_PROJECT_DIR
pushd $BABS_PROJECT_DIR

# TODO switch back to osf project
# Populate input data (Divergent from tuturial, bc https://github.com/datalad/datalad-osf/issues/191
datalad install ///dbic/QA

# TODO ----------------------------------------------------
# this can be cut if we pull the sing container down instead of build
# Just use datalad containers-add directly with docker://pennlinc/toy_bids_app:0.0.7
#  datalad containers-add toy-bids-app --url docker://pennlinc/toy_bids_app:0.0.7
singularity build -f \
    toybidsapp-0.0.7.sif \
    docker://pennlinc/toy_bids_app:0.0.7
datalad create -D "toy BIDS App" toybidsapp-container
pushd toybidsapp-container
datalad containers-add \
    --url ${PWD}/../toybidsapp-0.0.7.sif \
    toybidsapp-0-0-7
popd
rm -f toybidsapp-0.0.7.sif
# end TODO ----------------------------------------------------
#



# TODO --where_project must be abspath file issue for relative path
babs-init \
    --where_project ${PWD} \
    --project_name $PROJECT_NAME \
    --input BIDS ${PWD}/QA \
    --container_ds ${PWD}/toybidsapp-container \
    --container_name toybidsapp-0-0-7 \
    --container_config_yaml_file ${PWD}/config_toybidsapp.yaml \
    --type_session multi-ses \
    --type_system slurm

# TODO: check file output of babs-init
echo "PASSED: babs-init"

echo "debug: Miniconda path == $MINICONDA_PATH"

echo "Check setup, without job"
babs-check-setup --project_root ${PWD}/test_project/
echo "PASSED: Check setup, without job"

babs-check-setup --project_root ${PWD}/test_project/ --job-test
echo "PASSED: Check setup, with job"

babs-status --project_root ${PWD}/test_project/

babs-submit --project_root ${PWD}/test_project/

babs-status --project_root ${PWD}/test_project/
sleep 30s
babs-status --project_root ${PWD}/test_project/

echo "Print job logs--------------------------------------------"
find ${PWD}/test_project/analysis/logs/* -type f -print -exec cat {} \;
echo "end job logs--------------------------------------------"
# TODO: babs-check-status-job

# TODO babs-merge

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

