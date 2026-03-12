#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

version=${1:-3.10}
venv_dir=${2:-.venv}

# Delete caches, venv, and lock file
./dev/rm-caches.sh
./dev/venv-delete.sh $venv_dir
[ ! -e poetry.lock ] || rm poetry.lock

# Recreate
./dev/venv-create.sh $version $venv_dir
