#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

version=${1:-3.10}
venv_dir=${2:-.venv}

# verify Python version
python_bin=$(command -v python$version || true)
if [[ -z "$python_bin" ]]; then
    echo "Python $version not found. Please install it first."
    exit 1
fi

$python_bin -m venv "$venv_dir"

echo "Virtual environment created at $venv_dir using $python_bin"
