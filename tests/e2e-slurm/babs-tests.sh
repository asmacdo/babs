#!/bin/bash

set +e
conda info
echo "CONDA prior to activate $?"
./${MINICONDA_PATH}/bin/activate babs
echo "CONDA post activate $?"
set -e
# TODO babs-init

# TODO: check file output of babs-init

# TODO: babs-check-status-nojob

# TODO: babs-check-status-job


