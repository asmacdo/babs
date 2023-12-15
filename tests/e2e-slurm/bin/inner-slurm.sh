#!/bin/sh

# each simlink to this file in this dir will be added to the local path but executed inside the running slurm container
set -eu

RUNNING_SLURM_CONTAINER_NAME=${RUNNING_SLURM_CONTAINER_NAME:=slurm}

#set -x
cmd="${0##*/}"
topd=$(readlink -f "$0"  | xargs dirname | xargs dirname)

# This doesn't work because BABs squeue output parsing will fail TODO  file issue
# echo "Delegating inside: topd=$topd cmd=$cmd"

# --user $USER 
echo "$cmd $@" | tee slurmcmd.log
podman exec -it  $RUNNING_SLURM_CONTAINER_NAME "$cmd" "$@" 2>&1 | tee slurmcmd.log

