#!/usr/bin/env bash
set -euo pipefail
export EMBEDDER=${EMBEDDER:-random}
python etl/load_from_json.py --text-file examples/sample_decision.txt --extraction-json examples/sample_extraction.json
