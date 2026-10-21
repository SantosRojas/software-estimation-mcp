"""Observabilidad ligera: logs estructurados en JSON por stderr.

Razones de diseño:

- stderr, nunca stdout: en transporte STDIO, stdout transporta el protocolo MCP
  y escribir ahí lo corrompe la sesión con el cliente.
- Un correlation_id por invocación de herramienta permite seguir una llamada
  de extremo a extremo en los logs del host.
- Se registran duración y resultado (ok/error) para calcular latencia y
  contadores de éxito/fallo sin depender de un backend externo.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

_CONFIGURED = False


def _effective_level() -> str:
    return os.environ.get("ESTIMATOR_LOG_LEVEL", "INFO").strip().upper() or "INFO"


def _configure(logger: logging.Logger) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    logger.propagate = False
    _CONFIGURED = True


def get_logger(name: str = "estimation_mcp") -> logging.Logger:
    logger = logging.getLogger(name)
    _configure(logger)
    try:
        logger.setLevel(_effective_level())
    except ValueError:
        logger.setLevel(logging.INFO)
    return logger


def _log(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    payload: dict[str, Any] = {"event": event, **fields}
    logger.log(level, json.dumps(payload, ensure_ascii=False, default=str))


def new_correlation_id() -> str:
    return uuid.uuid4().hex[:16]


def instrument(tool_name: str) -> Callable[[F], F]:
    """Registra inicio, duración y resultado de una herramienta MCP."""

    def decorator(func: F) -> F:
        logger = get_logger()

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            cid = new_correlation_id()
            started = time.perf_counter()
            _log(logger, logging.INFO, "tool_started", tool=tool_name, correlation_id=cid)
            try:
                result = func(*args, **kwargs)
            except Exception as exc:
                duration_ms = round((time.perf_counter() - started) * 1000, 2)
                _log(
                    logger,
                    logging.ERROR,
                    "tool_failed",
                    tool=tool_name,
                    correlation_id=cid,
                    duration_ms=duration_ms,
                    error_type=type(exc).__name__,
                    error=str(exc),
                )
                raise
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            _log(logger, logging.INFO, "tool_completed", tool=tool_name, correlation_id=cid, duration_ms=duration_ms)
            return result

        return wrapper  # type: ignore[return-value]

    return decorator
