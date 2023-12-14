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

cleanup () {
	echo "Shutting down slurm"
	podman stop slurm
}

# TODO Can we autodetect this?
MINICONDA_PATH=/usr/share/miniconda
# MINICONDA_PATH=/home/austin/miniconda

# START SLURM -------------------------------
	    # -e "PATH=${MINICONDA_PATH}:$PATH" # This wouldn't work...right? # TODO
	    # -e "UID=$$(id -u)" \ TODO learn wtf once and for all
	    # -e "GID=$$(id -g)" \
	    # -e "USER=$$USER" \
	    # MINICONDA_PATH needs to be identical in and out?, conda expects? is that true? File RFE upstream?
	# --cap-add sys_admin \
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
set +e # We need to check the error code and allow failurs until slurm has started up
export PATH=${PWD}/tests/e2e-slurm/bin/:${PATH}
for ((i=1; i<=max_retries; i++)); do
	sacct

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
#
echo "Where are we"
echo $(pwd)
echo "ls"
ls
podman exec slurm ${PWD}/tests/e2e-slurm/babs-tests.sh

echo "--------------------------"
echo "     HUZZZZZZAHHHHHH!!!!!!"
echo "--------------------------"

