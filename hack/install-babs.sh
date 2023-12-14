set -eu

echo "Confirm that we are in babs environment"
current_env=$(conda env list | grep '*' | awk '{print $1}')
if [ "$current_env" != "babs" ]; then
    echo "Error: This script expects to be run inside a conda env named 'babs'."
    exit 1
fi

# TODO does this even need to be configured for gh actions?
git config --global user.name "GH Action"
git config --global user.email "fake@example.com"

conda install -c conda-forge datalad git git-annex
pip install datalad_container
# pip install datalad-osf
pip install .
