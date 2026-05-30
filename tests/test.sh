#!/bin/bash
if [ -z "$BDMSYS" ]; then
  echo "ERROR: BioDynaMo not sourced. Run: source <path>/bin/thisbdm.sh"
  exit 1
fi
cd "$(dirname "$0")/.."
rm -rf output/N3bdm*

PY=${PYTHON:-python}
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"

echo "=== Reference data quality ==="
$PY literature/check_data_quality.py || exit 1

echo "=== literature/lib.py unit tests ==="
$PY literature/test_lib.py || exit 1

echo "=== literature/check_data_quality.py self-tests ==="
$PY literature/test_check_data_quality.py || exit 1

echo "=== C++ test suite ==="
biodynamo build && ./build/skibidy-test
