#!/bin/bash
#
set -eux

. tests/e2e-slurm/ensure-conda.sh

# Sanity check
if [ "$MINICONDA_PATH/envs/$CONDA_DEFAULT_ENV/bin/babs-init" != "$(which babs-init)" ]; then
    echo "Error: This script expects to be run inside a conda env with 'babs-init'!" >&2
    echo "       We have not found it in conda env '$CONDA_DEFAULT_ENV' under '$MINICONDA_PATH'" >&2
    exit 1
fi
echo "Success, we are in the conda env with babs-init!"

# Install slurm commands (redirected into container)
export PATH=${PWD}/tests/e2e-slurm/bin/:${PATH}

# TODO dont do this
export TESTDATA=/home/austin/devel/babs/testdata
# TESTDATA=${TESTDATA:=/tmp/slurm-test-data}
SUBPROJECT_NAME=test_project

podman build -f tests/e2e-slurm/Containerfile . -t slurm-with-testuser

stop_container () {
	podman stop slurm || true
}

# START CONTAINER 
# TODO: 1005 is arbitrary, better one?
# TODO: explain uidmapping
# Reminder :Z for selinux
	# --uidmap=0:1000:1 \
	#
	#
# TODO: BROKEN!
# --uidmap=0:"$(id -u)":1 just dies while initializing the database
#
podman run -it \
	-e "MINICONDA_PATH=${MINICONDA_PATH}" \
	-e "CONDA_DEFAULT_ENV=${CONDA_DEFAULT_ENV:-}" \
	--uidmap=0:"$(id -u)":1 \
	--name slurm \
	--hostname slurmctl  \
	--privileged \
	-v "${PWD}:${PWD}:Z" \
	-v "${MINICONDA_PATH}:${MINICONDA_PATH}:Z" \
	slurm-with-testuser 
	# /bin/bash -c "tail -f > /dev/null"

# trap stop_container EXIT
# SINGULARITY BUILD

# mkdir -p "$TESTDATA"
# pushd "$TESTDATA"
# # TODO ----------------------------------------------------
# # this can be cut if we pull the sing container down instead of build
# # Just use datalad containers-add directly with docker://pennlinc/toy_bids_app:0.0.7
# #  datalad containers-add toy-bids-app --url docker://pennlinc/toy_bids_app:0.0.7
# singularity build -f \
#     toybidsapp-0.0.7.sif \
#     docker://pennlinc/toy_bids_app:0.0.7
# datalad create -D "toy BIDS App" toybidsapp-container
# pushd toybidsapp-container
# datalad containers-add \
#     --url "${PWD}"/../toybidsapp-0.0.7.sif \
#     toybidsapp-0-0-7
# popd
# rm -f toybidsapp-0.0.7.sif
# # end TODO ----------------------------------------------------
#
# # TODO switch back to osf project
# # Populate input data (Divergent from tuturial, bc https://github.com/datalad/datalad-osf/issues/191
# datalad install ///dbic/QA
# cp "${PWD}/tests/e2e-slurm/config_toybidsapp.yaml" "$PROJECT_ROOT"
# pushd "$PROJECT_ROOT"
#
#
# # TODO File Issue: --where_project must be abspath file issue for relative path
# babs-init \
#     --where_project "${PWD}" \
#     --project_name $SUBPROJECT_NAME \
#     --input BIDS "${PWD}"/QA \
#     --container_ds "${PWD}"/toybidsapp-container \
#     --container_name toybidsapp-0-0-7 \
#     --container_config_yaml_file "${PWD}"/config_toybidsapp.yaml \
#     --type_session multi-ses \
#     --type_system slurm
#
#
#
# # TODO: check file output of babs-init
# echo "PASSED: babs-init"
#
# echo "debug: Miniconda path == $MINICONDA_PATH"
#
# # Wait for slurm to be up
# max_retries=10
# delay=10  # seconds
#
# echo "Wait for Trying sacct until it succeeds"
# set +e # We need to check the error code and allow failures until slurm has started up
# for ((i=1; i<=max_retries; i++)); do
# 	# Check if the command was successful
# 	if sacct; then
# 		echo "Slurm is up and running!"
# 		# sacct will fail until slurm is running. Thow those errors out so they arent confusing
# 		# rm "$LOGS_DIR"/slurmcmd.log
# 		# touch "$LOGS_DIR"/slurmcmd.log
# 		break
# 	else
# 		echo "Waiting for Slurm to start... retry $i/$max_retries"
# 		sleep $delay
# 	fi
# 	# exit if max retries reached
# 	if [ $i -eq $max_retries ]; then
# 		echo "Failed to start Slurm after $max_retries attempts."
# 	exit 1
#     fi
# done
#
#
# echo "Check setup, without job"
# babs-check-setup --project_root "${PWD}"/test_project/
# echo "PASSED: Check setup, without job"
#
# babs-check-setup --project_root "${PWD}"/test_project/ --job-test
# echo "PASSED: Check setup, with job"
#
# babs-status --project_root "${PWD}"/test_project/
#
# babs-submit --project_root "${PWD}"/test_project/
#
# babs-status --project_root "${PWD}"/test_project/
# sleep 30s
# babs-status --project_root "${PWD}"/test_project/
#
# echo "Print job logs--------------------------------------------"
# find "${PWD}"/test_project/analysis/logs/* -type f -print -exec cat {} \;
# echo "end job logs--------------------------------------------"
# # TODO: babs-check-status-job
#
# # TODO babs-merge
#
# popd
