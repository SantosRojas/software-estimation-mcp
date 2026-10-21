"""Entry point opcional para iniciar en STDIO o HTTP mediante variables de entorno."""
from __future__ import annotations
import os
from estimation_mcp.server import mcp


def main() -> None:
    transport = os.environ.get("ESTIMATOR_TRANSPORT", "stdio").strip().lower()
    if transport == "stdio":
        mcp.run()
    elif transport in {"http", "streamable-http"}:
        mcp.run(
            transport="http",
            host=os.environ.get("ESTIMATOR_HTTP_HOST", "127.0.0.1").strip(),
            port=int(os.environ.get("ESTIMATOR_HTTP_PORT", "8000")),
        )
    else:
        raise SystemExit("ESTIMATOR_TRANSPORT debe ser stdio o http.")
