"""
Unit test asserting that Phase 0 Case 001 Data Feasibility Validation passes completely.
"""

import os
import pytest
from src.validation.validate_case_data import CaseDataValidator


def test_case_001_data_feasibility():
    config_path = "data/cases/case_001.yaml"
    assert os.path.exists(config_path), f"Config file {config_path} missing"

    validator = CaseDataValidator(config_path)
    passed, results = validator.run_all()

    failed_tests = [r for r in results if not r["passed"]]
    failure_details = "\n".join([f"[{r['category']}] {r['test']}: {r['message']}" for r in failed_tests])

    assert passed, f"Case 001 validation failed on {len(failed_tests)} tests:\n{failure_details}"
