# Project Spec: Kubernetes Docs RAG Gateway

## Project Summary

Kubernetes Docs RAG Gateway is a planned FastAPI-based gateway for answering Kubernetes documentation questions using selected, versioned documentation sources and a retrieval-augmented generation workflow.

This is a personal portfolio project. It is not an official Kubernetes project and is not affiliated with, endorsed by, or sponsored by Kubernetes, CNCF, or The Kubernetes Authors.

The repository currently has the documentation/source-registry foundation and a minimal FastAPI skeleton with `GET /health`. Chat, retrieval, provider, tracing, evaluation, deployment, and CI work remain planned.

The assistant should answer from a known Kubernetes documentation version or pinned upstream `kubernetes/website` commit. It should not answer as if it has access to an unspecified documentation state or a live Kubernetes cluster.

## Problem

LLM features are often presented as direct model calls, but production services need additional concerns: request validation, trusted retrieval, timeout handling, fallback responses, source metadata, observability, and behavioral evaluation.

This project uses Kubernetes documentation as a concrete domain for exploring those concerns.

## Goals

* Design a read-only Kubernetes documentation assistant.
* Build a future FastAPI `/chat` API with a clear request and response contract.
* Retrieve context from a curated, versioned subset of Kubernetes documentation.
* Generate source-grounded answers through a mock or optional real LLM provider.
* Track latency, token usage, fallback status, and trace data.
* Evaluate grounding, safety, and assistant boundaries.
* Provide a deployment and CI plan suitable for a portfolio project.

## Non-Goals

* Implementing application code during the documentation foundation step.
* Importing the full Kubernetes documentation site.
* Accessing or modifying a live Kubernetes cluster.
* Executing `kubectl`.
* Using private runbooks, kubeconfig files, credentials, internal cluster names, or private IP addresses.
* Replacing official Kubernetes documentation.
* Providing official Kubernetes, CNCF, or Kubernetes Authors support.
* Building an autonomous Kubernetes operations agent.

## MVP Scope

The MVP should be developed in phases:

1. Documentation foundation and source registry.
2. FastAPI skeleton with `GET /health`.
3. `POST /chat` request and response contract.
4. Local Markdown loading, heading-aware chunking, and simple retrieval.
5. Prompt builder and mock LLM provider.
6. Timeout, fallback, trace storage, and behavioral evals.
7. Docker, Kubernetes manifests, and CI.

## API Contract

Only `GET /health` is currently implemented. The chat API is planned and not yet implemented.

### `GET /health`

Example response:

```json
{
  "status": "ok",
  "service": "k8s-docs-rag-gateway",
  "environment": "local",
  "version": "0.1.0"
}
```

### `POST /chat`

Example request:

```json
{
  "user_id": "user-1",
  "session_id": "session-1",
  "message": "Why is my Pod stuck in Pending?",
  "top_k": 5,
  "mode": "troubleshooting"
}
```

Example response:

```json
{
  "request_id": "req-abc123",
  "session_id": "session-1",
  "answer": "The retrieved context suggests checking scheduling constraints such as resource requests, node selectors, affinity, taints, and tolerations.",
  "sources": [
    {
      "title": "Assigning Pods to Nodes",
      "path": "docs_source/kubernetes/concepts/scheduling-eviction/assign-pod-node.md",
      "heading": "Node affinity",
      "chunk_id": "assign-pod-node-004",
      "score": 0.82
    }
  ],
  "model": "mock-llm",
  "latency_ms": 120,
  "token_usage": {
    "input_tokens": 180,
    "output_tokens": 70,
    "total_tokens": 250
  },
  "fallback": false,
  "error_type": null
}
```

## Documentation Source Scope

The initial source scope is a curated subset of Kubernetes documentation that supports workload, scheduling, configuration, autoscaling, and safe troubleshooting questions.

The initial version does not import all of `content/en/docs` because full English docs ingestion would make early retrieval quality control harder. A curated subset keeps the corpus small enough to inspect manually, validates chunking behavior against known documents, makes traces easier to understand, and gives each source a clear relationship to behavioral eval coverage.

Each official Kubernetes document registry entry should include:

* `docs_version`
* `imported_commit`
* `imported_at`
* `source_url`
* `upstream_repo_path`
* `local_path`

These fields allow the project to answer based on a specific documentation snapshot and make retrieval traces reproducible.

Initial official Kubernetes document topics:

* Pods
* Pod Lifecycle
* Jobs
* CronJobs
* Deployments
* Assigning Pods to Nodes
* Taints and Tolerations
* Resource Management for Pods and Containers
* ConfigMaps
* Secrets
* Horizontal Pod Autoscaling

Initial custom runbooks:

* Pod Pending Troubleshooting Checklist
* CronJob Backfill Safety Checklist

### Source Expansion Plan

#### v0.1 Curated Subset

Use a curated workload, scheduling, configuration, autoscaling, and custom runbook subset for MVP quality control, chunking validation, retrieval evaluation, traceability, and behavioral eval coverage.

#### v0.2 Topic Expansion

Expand by topic after eval coverage exists for the new area. Candidate topics include Services, networking basics, storage basics, rollout troubleshooting, security context basics, and additional controller behavior.

#### v1.0 Full English Docs Ingestion

Ingest the full upstream `content/en/docs` tree from a pinned `kubernetes/website` commit. Registry metadata may be generated automatically, but each imported document should remain traceable to its documentation version, commit, import timestamp, source URL, upstream path, and local path.

## Chunking Design

Markdown should be chunked by heading structure. Each chunk should preserve title, heading hierarchy, source URL, upstream repository path, local path, tags, docs version, imported commit, import timestamp, and license metadata.

Long sections may be split further, but arbitrary splitting should not remove the context provided by headings.

## Retrieval Design

The first retrieval implementation should be lightweight and local. Ranking can consider keyword overlap, title matches, heading matches, Kubernetes terminology, and topic tags.

Future improvements may include BM25, embeddings, hybrid retrieval, or reranking.

If no useful source context is found, the assistant should say that the retrieved documentation context is insufficient.

## Prompting Design

The prompt builder should include:

* assistant role and safety boundary
* retrieved context
* source-grounding instruction
* user question
* instruction to avoid inventing cluster state
* instruction to answer from the selected documentation snapshot
* instruction to cite source metadata when possible

The assistant should not claim live cluster access or present itself as official Kubernetes support.

## LLM Provider Design

Provider logic should be separated from API and retrieval logic.

Planned providers:

* `MockProvider` for local development, tests, and CI
* optional real provider for experiments

The provider result should include model name, answer text, raw response if useful, token usage, and error information.

## Timeout and Fallback Design

Model calls should use a configurable timeout. When retrieval is empty, the provider fails, or the provider times out, the service should return a safe fallback response with an error type.

Potential error types:

* `retrieval_empty`
* `model_timeout`
* `provider_error`
* `validation_error`
* `unknown_error`

## Observability and Trace Design

Each future `/chat` request should have a request ID. Trace records should include:

* request ID
* user ID
* session ID
* question
* retrieved chunks
* prompt
* model response
* final answer
* source metadata
* docs version and imported commit
* latency
* token usage
* fallback status
* error type
* created timestamp

Local JSONL or SQLite storage is sufficient for early development.

## Behavioral Evaluation

Behavioral evals should test:

* grounding in retrieved documentation
* refusal to claim live cluster access
* safe handling of Secret-related questions
* safe Pod Pending troubleshooting guidance
* safe CronJob backfill guidance
* behavior when context is insufficient

## CI and Deployment Plan

CI is planned for a later phase. It should eventually run tests, linting, formatting checks, and optional Docker build or Kubernetes manifest validation.

Deployment artifacts are also planned for a later phase:

* Dockerfile
* Kubernetes Deployment
* Kubernetes Service
* ConfigMap
* example Secret manifest without real secrets

## Security and Safety

The repository must not include company-internal runbooks, credentials, kubeconfig files, private cluster names, private IP addresses, API keys, or real Secret values.

The assistant should be read-only and should not imply that it can inspect, modify, or repair a real cluster.

## Milestones

1. Documentation foundation and source registry.
2. FastAPI skeleton and health check.
3. Chat API contract and mock response.
4. Documentation import, chunking, and retrieval.
5. Prompt builder and provider abstraction.
6. Timeout, fallback, tracing, and behavioral eval.
7. Docker, Kubernetes manifests, and CI.

## Completion Criteria

The portfolio project is complete when:

* README reflects the actual implementation state.
* `/health` and `/chat` are implemented and tested.
* selected Kubernetes docs are imported with attribution.
* retrieval returns source metadata.
* timeout and fallback behavior works.
* traces capture prompt, context, answer, latency, and token usage.
* behavioral evals cover grounding and safety boundaries.
* Docker, Kubernetes manifests, and CI are present.

## Interview Talking Points

* Why LLM features need a gateway layer.
* Why curated retrieval sources can be better than mirroring everything.
* How source metadata supports trust and debugging.
* How timeout and fallback improve reliability.
* Why prompt and response traces matter.
* Why behavioral evals are needed for LLM systems.
* How licensing and attribution affect documentation-based RAG projects.
