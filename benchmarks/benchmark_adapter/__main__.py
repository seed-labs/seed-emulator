"""Run the Adapter service."""

import argparse
import os

import uvicorn
from benchmark_adapter.app import _build_app
from benchmark_adapter.grants import load_grant_spec


def main() -> int:
    parser = argparse.ArgumentParser(description="SEEDemu benchmark evaluation adapter")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8101)
    parser.add_argument(
        "--grant-spec",
        help="Grant spec JSON path (default: $BENCHMARK_GRANT_SPEC)",
    )
    args = parser.parse_args()
    path = args.grant_spec or os.environ["BENCHMARK_GRANT_SPEC"]
    uvicorn.run(_build_app(load_grant_spec(path)), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
