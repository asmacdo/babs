#!/bin/bash

set -eu

current_env=$(conda env list | grep '*' | awk '{print $1}')
if [ "$current_env" != "babs" ]; then
    echo "Error: This script expects to be run inside a conda env named 'babs'."
    exit 1
fi
echo "Success, we are in the babs conda env"
