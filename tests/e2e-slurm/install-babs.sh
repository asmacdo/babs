#!/bin/bash

set -eu

tests/e2e-slurm/ensure-env.sh

conda install -c conda-forge datalad git git-annex -y

# Optional dependencies, required for e2e-slurm
pip install datalad_container
pip install datalad-osf

# TODO non-dynamic for prod
# pip install .
pip install -e .
