set -ex

# WIP-NOT-WORKING
# Reminder :Z for selinux

REGISTRY=docker.io
HUBUSER=giovtorres
REPO=docker-centos7-slurm
TAG=23.11.07 # TODO

FQDN_IMAGE=${REGISTRY}/${HUBUSER}/${REPO}:${TAG}

# START SLURM -------------------------------
# TODO dev artifact: rm -it
podman run -it --rm \
		# -h slurmctl  \ # TODO WHY
    # --cap-add sys_admin \ # TODO WHY
		-v ${PWD}:${PWD}:Z \
    -v ${MINICONDA_PATH}:${MINICONDA_PATH} \ # This needs to be identical, conda expects? is that true? File RFE upstream?
    # --privileged \ # TODO WHY
  # -e "PATH=${MINICONDA_PATH}:$PATH" # This wouldn't work...right? # TODO 
	# 	-e "UID=$$(id -u)" \ TODO learn wtf once and for all
	# 	-e "GID=$$(id -g)" \
	# 	-e "USER=$$USER" \
    ${FQDN_IMAGE}

export PATH=${PWD}/bin/:${PATH}

# TODO babs-init

# TODO: check file output of babs-init

# TODO: babs-check-status-nojob

# TODO: babs-check-status-job


echo "--------------------------"
echo "     HUZZZZZZAHHHHHH!!!!!!"
echo "--------------------------"

