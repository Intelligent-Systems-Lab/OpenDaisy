#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

TARGET_DIR=${1:-src/py/daisyfl}

# Python
python -m isort "$TARGET_DIR"
python -m black -q "$TARGET_DIR"
python -m docformatter -i -r "$TARGET_DIR"
python -m ruff check --fix "$TARGET_DIR"
