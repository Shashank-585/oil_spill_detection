"""Tests asserting that the infrastructure health check passes."""
import pytest
from src.health_check import run_health_check


def test_health_check_passes():
    passed, failures = run_health_check()
    assert passed is True, f"Health check failed with issues: {failures}"
    assert len(failures) == 0
