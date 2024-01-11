#!/bin/bash
#
# exported for use in inner-slurm.sh
if [ -z "${MINICONDA_PATH:-}" ]; then
    if hash conda; then
        export MINICONDA_PATH=$(/bin/which conda | xargs dirname | xargs dirname)
    else
        echo "ERROR: must have MINICONDA_PATH set or have 'conda' available"
        exit 1
    fi
fi

if [ "$MINICONDA_PATH/envs/$CONDA_DEFAULT_ENV/bin/babs-init" != "$(which babs-init)" ]; then
    echo "Error: This script expects to be run inside a conda env with 'babs-init'!" >&2
    echo "       We have not found it in conda env '$CONDA_DEFAULT_ENV' under '$MINICONDA_PATH'" >&2
    exit 1
fi
echo "Success, we are in the conda env with babs-init!"
