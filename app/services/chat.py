from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from app.config import CHROMA_PERSIST_DIRECTORY, CHUNKS_PATH, PROVIDER_TIMEOUT_SECONDS
from app.prompting.builder import build_prompt
from app.providers.base import LLMProvider, ProviderResponse, estimate_tokens
from app.providers.mock import MockLLMProvider
from app.retrieval.loader import ChunkRecord, load_chunks
from app.retrieval.simple import RetrievalResult, retrieve
from app.retrieval.vector import ChromaVectorRetriever, VectorRetrievalError
from app.schemas import (
    ChatRequest,
    ChatResponse,
    RetrievedChunkTrace,
    Source,
    TokenUsage,
    TraceResponse,
)
from app.tracing.store import save_trace

CHUNKS_NOT_FOUND_TEXT = (
    "The local documentation chunks artifact was not found. Run "
    "`python scripts/ingest_docs.py` before using chat with local sources."
)
FALLBACK_TEXT_BY_ERROR_TYPE = {
    "chunks_not_found": CHUNKS_NOT_FOUND_TEXT,
    "retrieval_error": "The local retrieval step failed. Please try again later.",
    "vector_index_not_found": (
        "The local vector index was not found. Build it with "
        "scripts/build_vector_index.py first."
    ),
    "vector_retrieval_error": (
        "The local vector retrieval step failed. Please try again later."
    ),
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
        if request.retrieval_mode == "vector":
            vector_retriever = ChromaVectorRetriever(
                persist_directory=CHROMA_PERSIST_DIRECTORY,
            )
            retrieved_chunks = vector_retriever.retrieve(
                request.message,
                chunks,
                top_k=request.top_k,
            )
        elif retriever is None:
            retrieved_chunks = retrieve(request.message, chunks, top_k=request.top_k)
        else:
            retrieved_chunks = retriever(request.message, chunks)
    except VectorRetrievalError as exc:
        return _fallback_response(
            request_id=request_id,
            question=request.message,
            latency_ms=_elapsed_ms(started_at),
            error_type=exc.error_type,
            retrieved_chunks=[],
        )
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
            retrieved_chunks=retrieved_chunks,
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
            retrieved_chunks=retrieved_chunks,
            prompt=prompt,
        )
    except Exception:
        return _fallback_response(
            request_id=request_id,
            question=request.message,
            latency_ms=_elapsed_ms(started_at),
            error_type="provider_error",
            retrieved_chunks=retrieved_chunks,
            prompt=prompt,
        )

    latency_ms = _elapsed_ms(started_at)
    token_usage = TokenUsage(
        input_tokens=provider_response.input_tokens,
        output_tokens=provider_response.output_tokens,
        total_tokens=provider_response.total_tokens,
    )
    sources = [_to_source(result) for result in retrieved_chunks]
    response = ChatResponse(
        request_id=request_id,
        answer=provider_response.text,
        sources=sources,
        model=provider_response.model,
        latency_ms=latency_ms,
        token_usage=token_usage,
        fallback=False,
        error_type=None,
    )
    embedding_provider = None
    embedding_model = None
    if request.retrieval_mode == "vector":
        vector_retriever = ChromaVectorRetriever(
            persist_directory=CHROMA_PERSIST_DIRECTORY,
        )
        metadata = vector_retriever._store.collection.metadata or {}
        embedding_provider = str(metadata.get("embedding_provider") or "") or None
        embedding_model = str(metadata.get("embedding_model") or "") or None

    _save_trace(
        response=response,
        question=request.message,
        retrieved_chunks=retrieved_chunks,
        prompt=prompt,
        retrieval_mode=request.retrieval_mode,
        retriever_name=(
            "vector_retriever"
            if request.retrieval_mode == "vector"
            else "keyword_retriever"
        ),
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
    )
    return response


def _fallback_response(
    *,
    request_id: str,
    question: str,
    latency_ms: float,
    error_type: str,
    retrieved_chunks: list[RetrievalResult] | None = None,
    prompt: str = "",
) -> ChatResponse:
    answer = FALLBACK_TEXT_BY_ERROR_TYPE[error_type]
    input_tokens = estimate_tokens(question)
    output_tokens = estimate_tokens(answer)

    response = ChatResponse(
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
    _save_trace(
        response=response,
        question=question,
        retrieved_chunks=retrieved_chunks or [],
        prompt=prompt,
        retrieval_mode="keyword",
        retriever_name="keyword_retriever",
        embedding_provider=None,
        embedding_model=None,
    )
    return response


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


def _to_trace_chunk(result: RetrievalResult) -> RetrievedChunkTrace:
    return RetrievedChunkTrace(
        chunk_id=result.chunk_id,
        document_id=result.document_id,
        title=result.title,
        heading=result.heading,
        source_url=result.source_url,
        local_path=result.local_path,
        score=result.score,
        content=result.content,
        docs_version=result.docs_version,
        imported_commit=result.imported_commit,
        retrieval_mode=result.retrieval_mode,
    )


def _save_trace(
    *,
    response: ChatResponse,
    question: str,
    retrieved_chunks: list[RetrievalResult],
    prompt: str,
    retrieval_mode: str,
    retriever_name: str,
    embedding_provider: str | None,
    embedding_model: str | None,
) -> None:
    save_trace(
        TraceResponse(
            request_id=response.request_id,
            question=question,
            answer=response.answer,
            sources=response.sources,
            retrieved_chunks=[_to_trace_chunk(result) for result in retrieved_chunks],
            prompt=prompt,
            model=response.model,
            token_usage=response.token_usage,
            latency_ms=response.latency_ms,
            fallback=response.fallback,
            error_type=response.error_type,
            retrieval_mode=retrieval_mode,
            retriever_name=retriever_name,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
            created_at=datetime.now(timezone.utc),
        )
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
