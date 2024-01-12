#!/bin/bash

set -eu

conda install -c conda-forge datalad git git-annex -y

# Optional dependencies, required for e2e-slurm
pip install datalad_container
pip install datalad-osf

pip install .
