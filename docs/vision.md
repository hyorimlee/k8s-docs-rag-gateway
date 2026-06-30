# Vision

Kubernetes Docs RAG Gateway is intended to become a small, production-minded FastAPI service for answering Kubernetes documentation questions with retrieval-augmented generation.

This is a personal portfolio project, not an official Kubernetes project. It is not affiliated with, endorsed by, or sponsored by Kubernetes, CNCF, or The Kubernetes Authors.

This document describes the long-term direction. It also calls out what exists today so future goals do not sound already implemented.

## Current Implementation

The repository currently includes a local deterministic mock RAG-style flow:

* local Markdown ingestion and heading-based chunking
* JSONL chunk artifact generation
* simple keyword retrieval with metadata boosts
* prompt builder with assistant boundary rules
* provider interface and deterministic mock provider
* FastAPI `GET /health`, `POST /chat`, and `GET /traces/{request_id}`
* safe fallback/error metadata for expected internal failures
* in-memory trace storage
* local deterministic behavioral eval
* Dockerfile, Kubernetes manifest examples, and CI validation

The current system does not use a real LLM provider, embeddings, a vector database, persistent trace storage, full Kubernetes upstream documentation, or deployment/CD automation.

## Design Intent

The project is meant to show how an LLM feature can be wrapped in a service layer that handles reliability, observability, evaluation, and source attribution. Kubernetes documentation is the example domain because it has clear concepts, common troubleshooting questions, and strong attribution requirements.

The assistant should remain read-only, versioned, and documentation-grounded. It should answer from selected Kubernetes documentation sources while making clear that it cannot inspect or modify a real cluster.

## Intended Architecture

```text
Client
  |
  v
FastAPI /chat
  |
  v
Request validation
  |
  v
Documentation chunk loader
  |
  v
Retriever
  |
  v
Prompt builder
  |
  v
LLM provider interface
  |-- deterministic mock provider today
  |-- optional real provider later
  |
  v
Timeout and fallback handler
  |
  v
Response builder
  |
  v
Trace store and eval feedback
```

## Long-Term Components

### Versioned Kubernetes Docs Retrieval

The retrieval layer should use a curated subset of Kubernetes documentation before expanding. Each imported document should be traceable to a documentation version, upstream commit, import timestamp, upstream path, source URL, and local path.

The current retrieval implementation is simple keyword scoring. Later versions may add BM25, embeddings, hybrid retrieval, or reranking after deterministic baseline tests exist.

### Prompt Builder

The prompt builder should combine assistant boundaries, retrieved context, source-grounding rules, and the user question. It should instruct the assistant to say when retrieved context is insufficient and avoid inventing live cluster state.

This component is implemented today, but it is still paired with a deterministic mock provider.

### Mock and Optional Real LLM Provider

The mock provider supports deterministic local development and CI. A real provider may be added later as an optional integration, with secrets kept out of the repository.

Real provider integration is not implemented today.

### Timeout and Fallback

The service should return safe fallback responses instead of hanging or crashing when expected internal failures occur. The current implementation includes fallback/error metadata and a simple provider timeout boundary.

### Tracing and Observability

Trace records should help debug what context was retrieved, what prompt was built, what response was returned, and whether fallback behavior occurred.

The current trace store is in-memory only. Future versions may add persistent traces and richer metrics.

### Behavioral Evaluation

Behavioral evals should check grounding mechanics, source presence, live-cluster boundaries, secret handling, safe troubleshooting guidance, and insufficient-context behavior.

The current eval runner is deterministic and local. It validates response fields and trace/prompt content, not real LLM answer quality.

### Docker, Kubernetes, and CI

The project includes Docker and Kubernetes manifest examples plus CI checks. Future work may add image publishing and deployment/CD, but those are not implemented today.

## Long-Term Outcome

The finished project should demonstrate how to build a small LLM gateway service with explicit boundaries:

* source-grounded retrieval
* predictable API contracts
* timeout and fallback behavior
* request tracing
* cost and latency awareness
* behavioral evaluation
* clear license and attribution handling

The project should remain clearly separated from official Kubernetes projects and documentation ownership.
