#!/bin/bash

# each simlink to this file in this dir will be added to the local path but executed inside the running slurm container
set -eu
set -o pipefail

RUNNING_SLURM_CONTAINER_NAME=${RUNNING_SLURM_CONTAINER_NAME:=slurm}

#set -x
cmd="${0##*/}"

# This doesn't work because BABs squeue output parsing will fail TODO  file issue
# topd=$(readlink -f "$0"  | xargs dirname | xargs dirname)
# echo "Delegating inside: topd=$topd cmd=$cmd"

# testuser maps to the user running the container
podman exec --user "testuser" "$RUNNING_SLURM_CONTAINER_NAME" "$cmd" "$@"
# podman exec --user "$(id -u)" "$RUNNING_SLURM_CONTAINER_NAME" "$cmd" "$@" 2>&1 | tee --append "${LOGS_DIR:-/tmp/}/slurmcmd.log"
