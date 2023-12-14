echo "HAVENT IMPLEMENTED YET but are we in the conda env?"
conda info


git config --global user.name "GH Action"
git config --global user.email "fake@example.com"

conda install -c conda-forge datalad git git-annex

pip install datalad_container
pip install datalad-osf
pip install .


# TODO How can this be done non-interactively?
# datalad osf-credentials

pip show babs
