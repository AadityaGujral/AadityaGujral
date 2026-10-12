"""Run independent checks and contract tests, then write a compact receipt."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from validate_outputs import validate

ROOT = Path(__file__).resolve().parent


def main() -> None:
    validation = validate()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    notebook = json.loads((ROOT / "outputs" / "notebook_validation.json").read_text())
    pipeline = json.loads((ROOT / "outputs" / "pipeline_execution.json").read_text())
    receipt = {
        "status": "passed" if result.wasSuccessful() and validation["status"].upper() == "PASS" else "failed",
        "independent_reconciliations_passed": validation["passed_checks"],
        "contract_tests_run": result.testsRun,
        "contract_test_failures": len(result.failures),
        "contract_test_errors": len(result.errors),
        "notebook_code_cells_executed": notebook["executed_code_cells"],
        "notebook_execution_errors": notebook["errors"],
        "spark_version": pipeline["spark_version"],
        "spark_master": pipeline["spark_master"],
        "python_version": pipeline["python_version"],
    }
    (ROOT / "outputs" / "execution_receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    if receipt["status"] != "passed":
        raise SystemExit(1)
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
