from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from app.config import CHUNKS_PATH, PROVIDER_TIMEOUT_SECONDS
from app.prompting.builder import build_prompt
from app.providers.base import LLMProvider, ProviderResponse, estimate_tokens
from app.providers.mock import MockLLMProvider
from app.retrieval.loader import ChunkRecord, load_chunks
from app.retrieval.simple import RetrievalResult, retrieve
from app.schemas import ChatRequest, ChatResponse, Source, TokenUsage

CHUNKS_NOT_FOUND_TEXT = (
    "The local documentation chunks artifact was not found. Run "
    "`python scripts/ingest_docs.py` before using chat with local sources."
)
FALLBACK_TEXT_BY_ERROR_TYPE = {
    "chunks_not_found": CHUNKS_NOT_FOUND_TEXT,
    "retrieval_error": "The local retrieval step failed. Please try again later.",
    "prompt_build_error": "The prompt builder failed. Please try again later.",
    "provider_error": "The mock provider failed. Please try again later.",
    "provider_timeout": "The mock provider timed out. Please try again later.",
}


def handle_chat(
    request: ChatRequest,
    *,
    chunks_path: Path | None = None,
    chunk_loader: Callable[[Path], list[ChunkRecord]] = load_chunks,
    retriever: Callable[[str, list[ChunkRecord]], list[RetrievalResult]] | None = None,
    prompt_builder: Callable[[str, list[RetrievalResult]], str] = build_prompt,
    provider: LLMProvider | None = None,
    provider_timeout_seconds: float | None = None,
) -> ChatResponse:
    request_id = str(uuid4())
    started_at = perf_counter()
    resolved_chunks_path = chunks_path or CHUNKS_PATH
    resolved_provider = provider or MockLLMProvider()
    resolved_timeout = (
        provider_timeout_seconds
        if provider_timeout_seconds is not None
        else PROVIDER_TIMEOUT_SECONDS
    )

    try:
        chunks = chunk_loader(resolved_chunks_path)
    except FileNotFoundError:
        return _fallback_response(
            request_id=request_id,
            question=request.message,
            latency_ms=_elapsed_ms(started_at),
            error_type="chunks_not_found",
        )
    except Exception:
        return _fallback_response(
            request_id=request_id,
            question=request.message,
            latency_ms=_elapsed_ms(started_at),
            error_type="retrieval_error",
        )

    try:
        if retriever is None:
            retrieved_chunks = retrieve(request.message, chunks, top_k=request.top_k)
        else:
            retrieved_chunks = retriever(request.message, chunks)
    except Exception:
        return _fallback_response(
            request_id=request_id,
            question=request.message,
            latency_ms=_elapsed_ms(started_at),
            error_type="retrieval_error",
        )

    try:
        prompt = prompt_builder(request.message, retrieved_chunks)
    except Exception:
        return _fallback_response(
            request_id=request_id,
            question=request.message,
            latency_ms=_elapsed_ms(started_at),
            error_type="prompt_build_error",
        )

    try:
        provider_response = _generate_with_timeout(
            resolved_provider,
            prompt,
            timeout_seconds=resolved_timeout,
        )
    except FutureTimeoutError:
        return _fallback_response(
            request_id=request_id,
            question=request.message,
            latency_ms=_elapsed_ms(started_at),
            error_type="provider_timeout",
        )
    except Exception:
        return _fallback_response(
            request_id=request_id,
            question=request.message,
            latency_ms=_elapsed_ms(started_at),
            error_type="provider_error",
        )

    return ChatResponse(
        request_id=request_id,
        answer=provider_response.text,
        sources=[_to_source(result) for result in retrieved_chunks],
        model=provider_response.model,
        latency_ms=_elapsed_ms(started_at),
        token_usage=TokenUsage(
            input_tokens=provider_response.input_tokens,
            output_tokens=provider_response.output_tokens,
            total_tokens=provider_response.total_tokens,
        ),
        fallback=False,
        error_type=None,
    )


def _fallback_response(
    *,
    request_id: str,
    question: str,
    latency_ms: float,
    error_type: str,
) -> ChatResponse:
    answer = FALLBACK_TEXT_BY_ERROR_TYPE[error_type]
    input_tokens = estimate_tokens(question)
    output_tokens = estimate_tokens(answer)

    return ChatResponse(
        request_id=request_id,
        answer=answer,
        sources=[],
        model="mock",
        latency_ms=latency_ms,
        token_usage=TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        ),
        fallback=True,
        error_type=error_type,
    )


def _to_source(result: RetrievalResult) -> Source:
    return Source(
        chunk_id=result.chunk_id,
        document_id=result.document_id,
        title=result.title,
        heading=result.heading,
        source_url=result.source_url,
        local_path=result.local_path,
        score=result.score,
        docs_version=result.docs_version,
        imported_commit=result.imported_commit,
    )


def _elapsed_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1000


def _generate_with_timeout(
    provider: LLMProvider,
    prompt: str,
    *,
    timeout_seconds: float,
) -> ProviderResponse:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(provider.generate, prompt)
    try:
        return future.result(timeout=timeout_seconds)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
