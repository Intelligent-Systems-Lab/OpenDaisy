#!/bin/bash
set -e
cd "$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"/../

TARGET_DIR=${1:-src/py/daisyfl}

echo "=== test.sh ==="

echo "- Start Python checks"

echo "- isort: start"
python -m isort --check-only "$TARGET_DIR"
echo "- isort: done"

echo "- black: start"
python -m black --check "$TARGET_DIR"
echo "- black: done"

echo "- docformatter: start"
python -m docformatter -c -r "$TARGET_DIR"
echo "- docformatter:  done"

echo "- ruff: start"
python -m ruff check "$TARGET_DIR"
echo "- ruff: done"

echo "- mypy: start"
python -m mypy "$TARGET_DIR"
echo "- mypy: done"

echo "- pylint: start"
python -m pylint --max-line-length=120 --ignore-patterns=".*_test\.py$" "$TARGET_DIR"
echo "- pylint: done"

echo "- flake8: start"
python -m flake8 "$TARGET_DIR"
echo "- flake8: done"

echo "- pytest: start"
python -m pytest "$TARGET_DIR" --cov="$TARGET_DIR" --disable-warnings
echo "- pytest: done"

echo "- All Python checks passed"
