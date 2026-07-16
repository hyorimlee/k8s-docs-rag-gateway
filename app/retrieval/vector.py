from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

import chromadb

from app.retrieval.loader import ChunkRecord
from app.retrieval.simple import RetrievalResult

DEFAULT_COLLECTION_NAME = "k8s_docs_chunks"
DEFAULT_PERSIST_DIRECTORY = Path("artifacts/chroma")
DEFAULT_EMBEDDING_PROVIDER = "hash"
DEFAULT_SEMANTIC_EMBEDDING_PROVIDER = "sentence-transformers"
DEFAULT_SEMANTIC_MODEL_NAME = "sentence-transformers/multi-qa-MiniLM-L6-cos-v1"
INDEX_FORMAT_VERSION = "v1"
DEFAULT_EMBEDDING_DIMENSION = 32
DEFAULT_DISTANCE_METRIC = "cosine"
DEFAULT_NORMALIZE_EMBEDDINGS = True
DEFAULT_HASH_DIMENSION = 32


class VectorRetrievalError(RuntimeError):
    def __init__(self, message: str, *, error_type: str) -> None:
        super().__init__(message)
        self.error_type = error_type


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


class HashEmbeddingProvider:
    def __init__(self, *, dimensions: int = DEFAULT_EMBEDDING_DIMENSION) -> None:
        self.dimensions = dimensions

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        return [self._embed_text(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed_text(text)

    def _embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in self._tokenize(text):
            bucket = self._token_bucket(token)
            vector[bucket] += 1.0
        return vector

    def _tokenize(self, text: str) -> list[str]:
        return [token for token in TOKEN_PATTERN.findall(text.lower()) if token]

    def _token_bucket(self, token: str) -> int:
        total = 0
        for char in token:
            total += ord(char)
        return total % self.dimensions


class SentenceTransformerEmbeddingProvider:
    def __init__(
        self,
        *,
        model_name: str = DEFAULT_SEMANTIC_MODEL_NAME,
        normalize_embeddings: bool = DEFAULT_NORMALIZE_EMBEDDINGS,
    ) -> None:
        self.model_name = model_name
        self.normalize_embeddings = normalize_embeddings
        self.model = None
        self.dimensions: int | None = None

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        self._ensure_model_loaded()
        text_list = list(texts)
        if hasattr(self.model, "encode_documents"):
            vectors = self.model.encode_documents(text_list)
            return [_normalize_embedding_vector(vector) for vector in vectors]
        if hasattr(self.model, "encode"):
            vectors = self.model.encode(text_list)
            return [_normalize_embedding_vector(vector) for vector in vectors]
        return [self._encode_text(text, is_query=False) for text in text_list]

    def embed_query(self, text: str) -> list[float]:
        self._ensure_model_loaded()
        return self._encode_text(text, is_query=True)

    def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        return self.embed_documents(texts)

    def _ensure_model_loaded(self) -> None:
        if self.model is not None:
            return
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise VectorRetrievalError(
                "Optional dependency missing for semantic embeddings",
                error_type="semantic_embedding_dependency_missing",
            ) from exc
        self.model = SentenceTransformer(self.model_name)

    def _encode_text(self, text: str, *, is_query: bool) -> list[float]:
        if self.model is None:
            self._ensure_model_loaded()
        if is_query and hasattr(self.model, "encode_query"):
            vector = self.model.encode_query(text)
        elif not is_query and hasattr(self.model, "encode_document"):
            vector = self.model.encode_document(text)
        elif hasattr(self.model, "encode"):
            vector = self.model.encode(text)
        else:
            raise VectorRetrievalError(
                "SentenceTransformer model does not expose a usable encoding method",
                error_type="vector_retrieval_error",
            )
        normalized = _normalize_embedding_vector(vector)
        if not self.normalize_embeddings:
            normalized = _coerce_embedding(vector)
        if self.dimensions is None:
            self.dimensions = len(normalized)
        return normalized


class LocalChromaStore:
    def __init__(self, persist_directory: Path, collection_name: str) -> None:
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(self.persist_directory))
        self.collection = self.client.get_or_create_collection(name=collection_name)
        self.metadata = self.collection.metadata or {}

    def reset(
        self,
        *,
        embedding_provider: str,
        model_name: str | None = None,
        embedding_dimension: int | None = None,
        normalize_embeddings: bool = DEFAULT_NORMALIZE_EMBEDDINGS,
        distance_metric: str = DEFAULT_DISTANCE_METRIC,
    ) -> None:
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
        configuration = None
        if embedding_provider == DEFAULT_SEMANTIC_EMBEDDING_PROVIDER:
            configuration = {"hnsw": {"space": distance_metric}}
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            configuration=configuration,
        )
        self.collection.modify(
            metadata={
                "embedding_provider": embedding_provider,
                "embedding_model": model_name or "",
                "embedding_dimension": (
                    embedding_dimension or DEFAULT_EMBEDDING_DIMENSION
                ),
                "normalize_embeddings": str(normalize_embeddings).lower(),
                "distance_metric": distance_metric,
                "collection_name": self.collection_name,
                "index_format_version": INDEX_FORMAT_VERSION,
            }
        )

    def add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
        embeddings: list[list[float]],
    ) -> None:
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def query(
        self,
        query_embedding: list[float],
        *,
        top_k: int,
    ) -> list[dict[str, Any]]:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["metadatas", "documents", "embeddings", "distances"],
        )
        matches: list[dict[str, Any]] = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        embeddings = results.get("embeddings", [[]])[0]
        for index in range(len(ids)):
            embedding_value = (
                embeddings[index] if index < len(embeddings) else query_embedding
            )
            entry = {
                "id": ids[index],
                "document": documents[index],
                "metadata": metadatas[index],
                "embedding": _coerce_embedding(embedding_value),
            }
            matches.append(entry)
        return matches

    def exists(self) -> bool:
        try:
            return self.collection.count() > 0
        except Exception:
            return False


class ChromaVectorRetriever:
    def __init__(
        self,
        *,
        persist_directory: Path | None = None,
        embedding_provider: str | None = None,
        collection_name: str = DEFAULT_COLLECTION_NAME,
        model_name: str | None = None,
    ) -> None:
        self.persist_directory = persist_directory or DEFAULT_PERSIST_DIRECTORY
        self.embedding_provider = embedding_provider
        self.collection_name = collection_name
        self.model_name = model_name
        self._provider: (
            HashEmbeddingProvider | SentenceTransformerEmbeddingProvider | None
        ) = None
        self._store = LocalChromaStore(self.persist_directory, collection_name)

    def retrieve(
        self,
        query: str,
        chunks: list[ChunkRecord],
        *,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        if top_k <= 0:
            return []
        if not self._store.exists():
            raise VectorRetrievalError(
                f"Chroma index not found at {self.persist_directory}",
                error_type="vector_index_not_found",
            )

        self._validate_index_compatibility()
        provider = self._get_provider()
        query_embedding = provider.embed_query(query)
        self._validate_query_embedding(query_embedding)
        matches = self._store.query(query_embedding, top_k=top_k)
        results: list[RetrievalResult] = []
        for entry in matches:
            metadata = entry["metadata"]
            try:
                chunk = _chunk_from_metadata(metadata)
            except KeyError as exc:
                raise VectorRetrievalError(
                    f"Invalid vector metadata in Chroma index: {exc}",
                    error_type="vector_retrieval_error",
                ) from exc
            distance = _cosine_distance(query_embedding, entry["embedding"])
            score = max(0.0, 1.0 - distance)
            results.append(
                RetrievalResult(
                    chunk_id=chunk.chunk_id,
                    document_id=chunk.document_id,
                    title=chunk.title,
                    heading=chunk.heading,
                    source_url=chunk.source_url,
                    local_path=chunk.local_path,
                    score=score,
                    content=chunk.content,
                    docs_version=chunk.docs_version,
                    imported_commit=chunk.imported_commit,
                    collection_ids=chunk.collection_ids,
                    tags=chunk.tags,
                    category=chunk.category,
                    priority=chunk.priority,
                    language=chunk.language,
                    retrieval_mode="vector",
                )
            )
        return results

    def _get_provider(
        self,
    ) -> HashEmbeddingProvider | SentenceTransformerEmbeddingProvider:
        if self._provider is not None:
            return self._provider
        metadata = self._store.collection.metadata or {}
        provider_name = self.embedding_provider or str(
            metadata.get("embedding_provider") or DEFAULT_EMBEDDING_PROVIDER
        )
        model_name = (
            self.model_name or str(metadata.get("embedding_model") or "") or None
        )
        provider = _build_embedding_provider(provider_name, model_name=model_name)
        self._provider = provider
        return provider

    def _validate_index_compatibility(self) -> None:
        metadata = self._store.collection.metadata or {}
        expected_provider = str(metadata.get("embedding_provider") or "")
        expected_model = str(metadata.get("embedding_model") or "")
        expected_dimension = metadata.get("embedding_dimension")
        expected_format = metadata.get("index_format_version")
        expected_metric = metadata.get("distance_metric")
        if self.embedding_provider is not None:
            if expected_provider != self.embedding_provider:
                raise VectorRetrievalError(
                    "Chroma index embedding provider is incompatible",
                    error_type="embedding_provider_mismatch",
                )
        elif expected_provider not in {
            DEFAULT_EMBEDDING_PROVIDER,
            DEFAULT_SEMANTIC_EMBEDDING_PROVIDER,
        }:
            raise VectorRetrievalError(
                "Chroma index embedding provider is incompatible",
                error_type="embedding_provider_mismatch",
            )
        if expected_provider == DEFAULT_SEMANTIC_EMBEDDING_PROVIDER:
            if (
                self.model_name is not None
                and expected_model
                and self.model_name != expected_model
            ):
                raise VectorRetrievalError(
                    "Chroma index embedding model is incompatible",
                    error_type="vector_index_incompatible",
                )
            if expected_metric not in {DEFAULT_DISTANCE_METRIC, None}:
                raise VectorRetrievalError(
                    "Chroma index distance metric is incompatible",
                    error_type="vector_index_incompatible",
                )
        if expected_dimension is not None:
            expected_dimension_value = int(expected_dimension)
            if (
                expected_provider == DEFAULT_EMBEDDING_PROVIDER
                and expected_dimension_value != DEFAULT_HASH_DIMENSION
            ):
                raise VectorRetrievalError(
                    "Chroma index embedding dimension is incompatible",
                    error_type="vector_index_incompatible",
                )
            if (
                expected_provider == DEFAULT_SEMANTIC_EMBEDDING_PROVIDER
                and expected_dimension_value <= 0
            ):
                raise VectorRetrievalError(
                    "Chroma index embedding dimension is incompatible",
                    error_type="vector_index_incompatible",
                )
        if expected_format != INDEX_FORMAT_VERSION:
            raise VectorRetrievalError(
                "Chroma index format version is incompatible",
                error_type="vector_index_incompatible",
            )

    def _validate_query_embedding(self, query_embedding: list[float]) -> None:
        expected_dimension = DEFAULT_EMBEDDING_DIMENSION
        provider = self._get_provider()
        provider_dimension = getattr(provider, "dimensions", None)
        if provider_dimension is not None:
            expected_dimension = provider_dimension
        if len(query_embedding) != expected_dimension:
            raise VectorRetrievalError(
                "Chroma index embedding dimension is incompatible",
                error_type="vector_index_incompatible",
            )


def build_vector_index(
    chunks: Iterable[ChunkRecord | Mapping[str, Any]],
    *,
    persist_directory: Path | None = None,
    embedding_provider: str = DEFAULT_EMBEDDING_PROVIDER,
    collection_name: str = DEFAULT_COLLECTION_NAME,
    model_name: str | None = None,
) -> dict[str, Any]:
    chunk_records = [_normalize_chunk(chunk) for chunk in chunks]
    persist_path = persist_directory or DEFAULT_PERSIST_DIRECTORY
    provider = _build_embedding_provider(embedding_provider, model_name=model_name)
    store = LocalChromaStore(persist_path, collection_name)
    embedding_dimension = getattr(provider, "dimensions", None)
    if embedding_dimension is None:
        embedding_dimension = DEFAULT_HASH_DIMENSION
    if embedding_provider == DEFAULT_SEMANTIC_EMBEDDING_PROVIDER:
        embedding_dimension = getattr(provider, "dimensions", None) or 384
    store.reset(
        embedding_provider=embedding_provider,
        model_name=model_name,
        embedding_dimension=embedding_dimension,
        normalize_embeddings=DEFAULT_NORMALIZE_EMBEDDINGS,
    )

    ids = [chunk.chunk_id for chunk in chunk_records]
    if embedding_provider == DEFAULT_SEMANTIC_EMBEDDING_PROVIDER:
        documents = [_build_embedding_text(chunk) for chunk in chunk_records]
    else:
        documents = [chunk.content for chunk in chunk_records]
    metadatas = [_chunk_metadata(chunk) for chunk in chunk_records]
    embeddings = provider.embed_texts(documents)
    store.add(ids, documents, metadatas, embeddings)
    embedding_dimension = getattr(provider, "dimensions", None)
    if embedding_dimension is None:
        embedding_dimension = (
            384
            if embedding_provider == DEFAULT_SEMANTIC_EMBEDDING_PROVIDER
            else DEFAULT_HASH_DIMENSION
        )

    return {
        "chunks_read": len(chunk_records),
        "vectors_indexed": len(chunk_records),
        "collection": collection_name,
        "persist_directory": str(persist_path),
        "embedding_provider": embedding_provider,
        "embedding_model": model_name
        or (
            DEFAULT_SEMANTIC_MODEL_NAME
            if embedding_provider == DEFAULT_SEMANTIC_EMBEDDING_PROVIDER
            else None
        ),
        "embedding_dimension": embedding_dimension,
        "distance_metric": DEFAULT_DISTANCE_METRIC,
    }


def _normalize_chunk(chunk: ChunkRecord | Mapping[str, Any]) -> ChunkRecord:
    if isinstance(chunk, ChunkRecord):
        return chunk
    payload = dict(chunk)
    return ChunkRecord(
        chunk_id=str(payload["chunk_id"]),
        document_id=str(payload["document_id"]),
        title=str(payload["title"]),
        heading=payload.get("heading"),
        source_url=payload.get("source_url"),
        local_path=str(payload["local_path"]),
        content=str(payload["content"]),
        docs_version=payload.get("docs_version"),
        imported_commit=payload.get("imported_commit"),
        collection_ids=list(payload.get("collection_ids") or []),
        tags=list(payload.get("tags") or []),
        category=payload.get("category"),
        priority=payload.get("priority"),
        language=payload.get("language"),
    )


def _chunk_metadata(chunk: ChunkRecord) -> dict[str, Any]:
    return {
        "chunk_id": _metadata_value(chunk.chunk_id),
        "document_id": _metadata_value(chunk.document_id),
        "title": _metadata_value(chunk.title),
        "heading": _metadata_value(chunk.heading),
        "source_url": _metadata_value(chunk.source_url),
        "local_path": _metadata_value(chunk.local_path),
        "content": _metadata_value(chunk.content),
        "docs_version": _metadata_value(chunk.docs_version),
        "imported_commit": _metadata_value(chunk.imported_commit),
        "collection_ids": _serialize_metadata_value(chunk.collection_ids),
        "tags": _serialize_metadata_value(chunk.tags),
        "category": _metadata_value(chunk.category),
        "priority": _metadata_value(chunk.priority),
        "language": _metadata_value(chunk.language),
    }


def _chunk_from_metadata(metadata: Mapping[str, Any]) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=str(metadata["chunk_id"]),
        document_id=str(metadata["document_id"]),
        title=str(metadata["title"]),
        heading=metadata.get("heading"),
        source_url=metadata.get("source_url"),
        local_path=str(metadata["local_path"]),
        content=str(metadata["content"]),
        docs_version=metadata.get("docs_version"),
        imported_commit=metadata.get("imported_commit"),
        collection_ids=_deserialize_metadata_list(metadata.get("collection_ids")),
        tags=_deserialize_metadata_list(metadata.get("tags")),
        category=metadata.get("category"),
        priority=metadata.get("priority"),
        language=metadata.get("language"),
    )


def _build_embedding_provider(
    embedding_provider: str,
    *,
    model_name: str | None = None,
) -> HashEmbeddingProvider | SentenceTransformerEmbeddingProvider:
    if embedding_provider == "hash":
        return HashEmbeddingProvider()
    if embedding_provider == DEFAULT_SEMANTIC_EMBEDDING_PROVIDER:
        return SentenceTransformerEmbeddingProvider(
            model_name=model_name or DEFAULT_SEMANTIC_MODEL_NAME
        )
    raise ValueError(f"Unsupported embedding provider: {embedding_provider}")


def _metadata_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _serialize_metadata_value(value: list[str] | None) -> str:
    if value is None:
        return "[]"
    if not value:
        return "[]"
    return json.dumps(value)


def _deserialize_metadata_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [value]
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
        return [str(parsed)]
    return [str(value)]


def _normalize_embedding_vector(vector: Any) -> list[float]:
    values = _coerce_embedding(vector)
    magnitude = math.sqrt(sum(value * value for value in values))
    if magnitude == 0:
        return values
    return [value / magnitude for value in values]


def _coerce_embedding(value: Any) -> list[float]:
    if isinstance(value, list):
        return [float(item) for item in value]
    if hasattr(value, "tolist"):
        return [float(item) for item in value.tolist()]
    return [float(value)]


def _build_embedding_text(chunk: ChunkRecord) -> str:
    title = chunk.title.strip() if chunk.title else ""
    heading = chunk.heading.strip() if chunk.heading else ""
    content = _strip_retrieval_notes(chunk.content)
    parts: list[str] = []
    if title:
        parts.append(f"Title: {title}")
    if heading:
        parts.append(f"Section: {heading}")
    if content:
        parts.append(content)
    return "\n\n".join(part for part in parts if part)


def _strip_retrieval_notes(text: str) -> str:
    lines = [
        line for line in text.splitlines() if "retrieval notes" not in line.lower()
    ]
    return "\n".join(line for line in lines if line.strip()).strip()


def _cosine_distance(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 1.0
    length = min(len(left), len(right))
    dot_product = sum(left[index] * right[index] for index in range(length))
    magnitude_left = sum(value * value for value in left) ** 0.5
    magnitude_right = sum(value * value for value in right) ** 0.5
    if magnitude_left == 0 or magnitude_right == 0:
        return 1.0
    similarity = dot_product / (magnitude_left * magnitude_right)
    return max(0.0, 1.0 - similarity)
