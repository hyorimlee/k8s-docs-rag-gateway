# Vision

Kubernetes Docs RAG Gateway is intended to become a small, production-minded FastAPI service for answering Kubernetes documentation questions with retrieval-augmented generation.

This is a personal portfolio project, not an official Kubernetes project. It is not affiliated with, endorsed by, or sponsored by Kubernetes, CNCF, or The Kubernetes Authors.

This document describes the long-term design target. It is not a statement that these components already exist. The repository is currently in the documentation and source-registry foundation stage.

## Design Intent

The project is meant to show how an LLM feature can be wrapped in a service layer that handles reliability, observability, evaluation, and source attribution. Kubernetes documentation is the example domain because it has clear concepts, common troubleshooting questions, and strong attribution requirements.

The assistant should remain read-only, versioned, and documentation-grounded. It should answer from a selected Kubernetes documentation version or pinned upstream `kubernetes/website` commit, while making clear that it cannot inspect or modify a real cluster.

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
Kubernetes docs retriever
  |
  v
Prompt builder
  |
  v
LLM provider
  |-- mock provider for local development and CI
  |-- optional real provider for experiments
  |
  v
Timeout and fallback handler
  |
  v
Response builder
  |
  v
Trace store and metrics
```

## Planned Components

### FastAPI `/chat`

The future `/chat` endpoint should accept a user question, validate request fields, retrieve relevant documentation chunks, call a provider, and return an answer with source metadata.

### Versioned Kubernetes Docs Retrieval

The retrieval layer should use a curated subset of Kubernetes documentation rather than mirroring the entire upstream site at first. Each imported document should be traceable to a documentation version, upstream commit, import timestamp, upstream path, source URL, and local path.

The first retrieval implementation can be local and lightweight, then evolve toward BM25, embeddings, or hybrid retrieval. Later versions can expand from curated sources to topic-based source sets and eventually full English `content/en/docs` ingestion.

### Prompt Builder

The prompt builder should combine assistant boundaries, retrieved context, source-grounding rules, and the user question. It should instruct the assistant to say when retrieved context is insufficient.

### Mock and Optional Real LLM Provider

A mock provider should support deterministic local development and CI. A real provider may be added later as an optional integration, with secrets kept out of the repository.

### Timeout and Fallback

Model calls should have a timeout budget. If retrieval is empty, the provider fails, or the provider times out, the service should return a safe fallback instead of hanging or hallucinating.

### Latency and Token Usage Tracking

Responses should include latency and token usage metadata when available. Mock providers may estimate token usage, while real providers may return provider-reported usage.

### Trace Store

The trace store should record request ID, question, retrieved chunks, prompt, model response, final answer, sources, latency, token usage, fallback status, and error type. A local JSONL or SQLite store is enough for early versions.

### Behavioral Evaluation

Behavioral evals should check whether answers are grounded, cite sources, avoid claiming live cluster access, avoid leaking or inventing secrets, and give safe troubleshooting guidance.

### Docker and Kubernetes Deployment

Later milestones should add a Dockerfile and Kubernetes manifests for a Deployment, Service, ConfigMap, and example Secret. These are deployment demonstrations for the portfolio project, not official Kubernetes artifacts.

### CI

CI should eventually run tests, linting, formatting checks, and optional Docker build or manifest validation checks. CI should use the mock provider only.

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
