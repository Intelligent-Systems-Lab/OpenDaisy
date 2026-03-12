#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

TARGET_DIR=${1:-src/py/daisyfl}

echo "Format code and run all test scripts"

./dev/format.sh $TARGET_DIR

./dev/test.sh $TARGET_DIR
