#!/usr/bin/env bash

# Copyright (c) 2026 A.I. Hero, Inc.
# All Rights Reserved.

# Runs the compliance engine's Python tables so they gate with the shell
# suites: both runners glob scripts/*.test.sh and neither knows about .py.
# pyyaml is the engine's one dependency; a machine without it must fail
# loudly here, not report the engine as passing because nothing ran.

set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
python3 -c 'import yaml' 2>/dev/null || { echo "audit.test.sh: pyyaml missing (pip install pyyaml)"; exit 1; }
python3 -m unittest scripts/audit_test.py
