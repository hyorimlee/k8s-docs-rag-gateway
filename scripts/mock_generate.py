from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

# ruff: noqa: E402, I001
from app.providers.mock import MockLLMProvider  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic mock provider.")
    parser.add_argument("prompt", nargs="?")
    args = parser.parse_args()

    prompt = args.prompt if args.prompt is not None else sys.stdin.read()
    response = MockLLMProvider().generate(prompt)

    print(response.text)
    print(f"model: {response.model}")
    print(f"input_tokens: {response.input_tokens}")
    print(f"output_tokens: {response.output_tokens}")
    print(f"total_tokens: {response.total_tokens}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
