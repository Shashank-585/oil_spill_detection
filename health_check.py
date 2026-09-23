"""Root entrypoint for SIH26143 health check."""
import sys
from src.health_check import run_health_check

if __name__ == "__main__":
    passed, _ = run_health_check()
    sys.exit(0 if passed else 1)
