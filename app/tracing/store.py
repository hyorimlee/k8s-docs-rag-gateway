from __future__ import annotations

from threading import Lock

from app.schemas import TraceResponse

_TRACES: dict[str, TraceResponse] = {}
_LOCK = Lock()


def save_trace(trace: TraceResponse) -> None:
    with _LOCK:
        _TRACES[trace.request_id] = trace


def get_trace(request_id: str) -> TraceResponse | None:
    with _LOCK:
        return _TRACES.get(request_id)


def clear_traces() -> None:
    with _LOCK:
        _TRACES.clear()
