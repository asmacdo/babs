#!/bin/bash

if [ -z "${MINICONDA_PATH:-}" ]; then
    if hash conda; then
        export MINICONDA_PATH=$(/bin/which conda | xargs dirname | xargs dirname)
        echo "Conda installed to $MINICONDA_PATH"
    else
        echo "ERROR: must have MINICONDA_PATH set or have 'conda' available"
        exit 1
    fi
fi
