#!/bin/bash
set -euo pipefail
if [ -z "${BDMSYS:-}" ]; then
  echo "ERROR: BioDynaMo not sourced. Run: source <path>/bin/thisbdm.sh"
  exit 1
fi
cd "$(dirname "$0")/.."

PY=${PYTHON:-/usr/bin/python3}
"$PY" -c 'import sys; assert sys.version_info >= (3, 11), "Analysis tests require Python 3.11+; set PYTHON before sourcing BioDynaMo"'
export PYTHONPATH="$(pwd):${PYTHONPATH:-}"
export LD_LIBRARY_PATH="$(pwd)/build:$("$BDMSYS/third_party/root/bin/root-config" --libdir):$BDMSYS/lib:${LD_LIBRARY_PATH:-}"
export OMP_NUM_THREADS=1 OMP_DYNAMIC=FALSE

echo "=== Reference data quality ==="
"$PY" literature/check_data_quality.py

echo "=== literature/lib.py unit tests ==="
"$PY" literature/test_lib.py

echo "=== literature/check_data_quality.py self-tests ==="
"$PY" literature/test_check_data_quality.py

echo "=== C++ test suite ==="
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --parallel 2
./build/skibidy-test

echo "=== Workflow regression tests ==="
SKIBIDY_RUNTIME_TEST=1 "$PY" -m unittest discover -s tests -p 'test_*.py'

echo "=== Exact checkpoint runtime regression ==="
"$PY" scripts/validation/checkpoint_regression.py

echo "=== Scheduled treatment runtime regression ==="
"$PY" scripts/validation/treatment_regression.py
