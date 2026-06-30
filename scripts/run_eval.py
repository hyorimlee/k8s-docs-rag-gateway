from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# ruff: noqa: E402, I001
from app.evaluation.runner import DEFAULT_CASES_PATH, load_eval_cases, run_eval_cases
from app.retrieval.loader import DEFAULT_CHUNKS_PATH
from app.tracing.store import clear_traces


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run local deterministic behavioral eval cases."
    )
    parser.add_argument("--cases", type=Path, default=ROOT_DIR / DEFAULT_CASES_PATH)
    parser.add_argument("--chunks", type=Path, default=ROOT_DIR / DEFAULT_CHUNKS_PATH)
    args = parser.parse_args()

    if not args.chunks.exists():
        print(f"Chunks file not found: {args.chunks}")
        print("Run `python scripts/ingest_docs.py` before running eval.")
        return 2

    clear_traces()
    cases = load_eval_cases(args.cases)
    results = run_eval_cases(cases, chunks_path=args.chunks)

    passed_count = sum(result.passed for result in results)
    failed_count = len(results) - passed_count

    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{status} {result.case_id}")
        for failure in result.failures:
            print(f"  - {failure}")

    print(f"\nSummary: {passed_count} passed, {failed_count} failed")
    return 1 if failed_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
