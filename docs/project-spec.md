# Project Spec: Kubernetes Docs RAG Gateway

## Project Summary

Kubernetes Docs RAG Gateway is a FastAPI-based mock RAG gateway for experimenting with documentation-grounded Kubernetes assistance. The current implementation is local and deterministic: it ingests local Markdown, chunks it by heading, retrieves chunks with simple keyword scoring, builds a structured prompt, calls a deterministic mock provider, stores an in-memory trace, and exposes the result through FastAPI.

This is a personal portfolio project. It is not an official Kubernetes project and is not affiliated with, endorsed by, or sponsored by Kubernetes, CNCF, or The Kubernetes Authors.

The assistant should answer from known documentation sources and should not imply access to an unspecified Kubernetes documentation state or a live Kubernetes cluster.

## Implemented

* Documentation/source registry foundation under `docs_source/`
* Local custom runbooks under `docs_source/custom/`
* Registry YAML loading from `docs_source/registry/documents/*.yaml`
* Local Markdown loading and YAML frontmatter stripping
* Heading-based chunking
* JSONL chunk artifact at `artifacts/chunks.jsonl`
* Simple deterministic retrieval:
  * content keyword overlap
  * heading/title boost
  * tag boost
  * deterministic `top_k`
* Prompt builder:
  * assistant boundary rules
  * context block with source metadata
  * user question block
  * no-context behavior
* Provider abstraction:
  * `LLMProvider` protocol
  * deterministic `MockLLMProvider`
  * simple estimated token usage
* FastAPI:
  * `GET /health`
  * `POST /chat`
  * `GET /traces/{request_id}`
* `/chat` mock RAG-style flow:
  * load chunks
  * retrieve chunks
  * build prompt
  * call mock provider
  * return answer, source metadata, token usage, latency, fallback/error metadata
* Fallback handling:
  * `chunks_not_found`
  * `retrieval_error`
  * `prompt_build_error`
  * `provider_error`
  * `provider_timeout`
* In-memory trace store
* Local deterministic behavioral eval:
  * `eval/cases.yaml`
  * `scripts/run_eval.py`
* Manual Promptfoo API regression checks:
  * `promptfooconfig.yaml`
  * deterministic checks against the running local `/chat` endpoint
* Dockerfile
* Kubernetes manifest examples
* GitHub Actions CI:
  * pytest
  * ruff check
  * ruff format check
  * Docker build
  * kubeconform manifest validation

## Current Limitations

* Real LLM generation is not implemented.
* No external APIs are called.
* No OpenAI, Anthropic, Gemini, or other real provider SDKs are installed.
* Embeddings, vector DB, hybrid retrieval, and reranking are not implemented.
* Kubernetes upstream docs are registered but mostly not imported yet.
* The local corpus is small and mainly custom runbooks.
* The trace store is in-memory only and does not persist across process restarts.
* Behavioral eval checks deterministic mock-flow mechanics, not real model quality.
* Promptfoo checks are manual/local API regression checks in this phase and are not a CI gate.
* Image publishing, CD, and real cluster deployment automation are not implemented.
* This is not a full Kubernetes docs Q&A assistant yet.

## Problem

LLM features are often presented as direct model calls, but service implementations need additional concerns: request validation, trusted retrieval, timeout handling, fallback responses, source metadata, observability, and behavioral evaluation.

This project uses Kubernetes documentation as a concrete domain for exploring those concerns while keeping the implementation safe, local, and inspectable.

## Goals

* Provide a read-only Kubernetes documentation assistant gateway.
* Keep retrieval sources explicit, versionable, and attributable.
* Return source metadata with chat responses.
* Keep assistant boundaries explicit in prompts.
* Use deterministic mocks for tests and CI.
* Capture trace data for debugging.
* Run local behavioral evals for safety and grounding mechanics.
* Demonstrate Docker, Kubernetes manifest, and CI hygiene.

## Non-Goals

* Replacing official Kubernetes documentation.
* Providing official Kubernetes, CNCF, or Kubernetes Authors support.
* Accessing, inspecting, or modifying a live Kubernetes cluster.
* Executing `kubectl`.
* Accepting or exposing secrets, kubeconfig files, private cluster names, internal service names, private IP addresses, or credentials.
* Importing the full Kubernetes documentation site in the current phase.
* Adding a real LLM provider in the current phase.
* Adding embeddings, vector DB, hybrid retrieval, persistent traces, or CD in the current phase.
* Building an autonomous Kubernetes operations agent.

## API Contract

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
  "mode": "mock"
}
```

Example response shape:

```json
{
  "request_id": "req-abc123",
  "answer": "Based on the retrieved documentation context, I would start with these checks:\n\n1. Review the documented diagnostic signals in the retrieved context.\n2. Check scheduling, workload, or configuration constraints mentioned in the retrieved context.\n3. Prefer safe diagnostic checks before making destructive changes.\n\nSources used:\n- Pod Pending Troubleshooting Checklist - Pod Pending Troubleshooting Checklist > Safe Triage Flow\n\nNote: this response was generated by the deterministic mock provider. Real LLM generation is not implemented yet.",
  "sources": [
    {
      "chunk_id": "custom-pod-pending-troubleshooting-0002-18c1f556476c",
      "document_id": "custom-pod-pending-troubleshooting",
      "title": "Pod Pending Troubleshooting Checklist",
      "heading": "Pod Pending Troubleshooting Checklist > Safe Triage Flow",
      "source_url": null,
      "local_path": "docs_source/custom/pod-pending-troubleshooting.md",
      "score": 20.0,
      "docs_version": "local",
      "imported_commit": null
    }
  ],
  "model": "mock",
  "latency_ms": 12.3,
  "token_usage": {
    "input_tokens": 180,
    "output_tokens": 18,
    "total_tokens": 198
  },
  "fallback": false,
  "error_type": null
}
```

The response answer currently comes from the deterministic mock provider. It is context-shaped for manual testing, but it is not real LLM generation. The useful grounding evidence is the returned source metadata and the stored trace prompt/context.

Fallback responses preserve the same response shape with `fallback=true`, `sources=[]`, and a specific `error_type`.

Current fallback `error_type` values:

* `chunks_not_found`
* `retrieval_error`
* `prompt_build_error`
* `provider_error`
* `provider_timeout`

### `GET /traces/{request_id}`

Returns an in-memory trace for a previous `/chat` request.

Trace fields include:

* `request_id`
* `question`
* `answer`
* `sources`
* `retrieved_chunks`
* `prompt`
* `model`
* `token_usage`
* `latency_ms`
* `fallback`
* `error_type`
* `created_at`

Unknown request IDs return `404`. Traces are process-local and disappear on restart.

## Documentation Source Scope

The registry defines a curated subset of Kubernetes documentation that supports workload, scheduling, configuration, autoscaling, and safe troubleshooting questions.

Registry entries may exist before the corresponding local Markdown file is imported. The ingestion script uses `local_path`, reads files that exist, skips missing files gracefully, and reports missing counts.

Current local files are mainly custom runbooks:

* `docs_source/custom/pod-pending-troubleshooting.md`
* `docs_source/custom/cronjob-backfill-checklist.md`

Registered upstream Kubernetes topics include:

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

These upstream documents are mostly not imported yet.

## Retrieval Design

The current retrieval implementation is lightweight and local. It scores chunks by:

* content keyword overlap
* heading/title boost
* tag boost

Results are sorted by score descending, with deterministic tie-breaking by `chunk_id`. Chunks with zero score are omitted.

Future improvements may include BM25, embeddings, hybrid retrieval, or reranking.

## Prompting Design

The prompt builder includes:

* assistant role and safety boundary
* instruction to use only provided context
* no live cluster access boundary
* secret handling boundary
* context block with numbered sources and metadata
* user question block
* output guidance asking for concise answers and source citations

If retrieval returns no chunks, the prompt includes a clear no-context block instructing the model not to fabricate an answer.

## Provider Design

Provider logic is separated from chat, retrieval, and prompting logic.

Current provider:

* `MockLLMProvider`
* deterministic text
* `model="mock"`
* simple `str.split()` token estimates
* no external API calls

Optional real providers may be added later behind the same interface. Real provider SDKs and API keys are not part of the current implementation.

## Timeout and Fallback

Provider generation is wrapped with a small synchronous timeout boundary. The default timeout is configured by `PROVIDER_TIMEOUT_SECONDS`.

Expected internal failures return safe fallback responses instead of crashing the API. Fallback responses include token usage, latency, `fallback=true`, and a specific `error_type`.

## Observability and Trace Design

The current trace store is an in-memory dictionary keyed by `request_id`. It is useful for local debugging and tests only. It is not persistent storage.

Each successful and fallback `/chat` response saves a trace. The same `request_id` returned by `/chat` can be passed to `GET /traces/{request_id}` while the process is running.

Future work may add persistent trace storage and richer metrics.

## Behavioral Evaluation

The local eval runner loads `eval/cases.yaml` and executes each case against the chat service without a live server.

It checks deterministic expectations against:

* chat response fields
* source presence
* fallback/error metadata
* stored trace
* prompt text and assistant boundary rules

This is not a real LLM quality benchmark. It validates the current mock-flow mechanics and safety boundaries.

## Promptfoo API Regression Checks

`promptfooconfig.yaml` defines a small manual regression suite for the running local `/chat` API. It posts representative questions to `http://127.0.0.1:8000/chat` and checks the deterministic mock-provider answer text with simple `contains` and `not-contains` assertions.

These checks cover the same broad behavioral areas as the local eval cases:

* Pending Pod triage
* CronJob backfill safety
* live cluster access boundaries
* secret handling boundaries
* unrelated/no-context questions

Promptfoo is intentionally not a CI gate in the current phase. The internal Python eval runner remains the CI gate because it can inspect response fields, traces, prompts, source metadata, fallback/error metadata, and token usage without requiring a live server or external tooling. The Promptfoo suite is useful for manual API-level smoke and regression testing before tagging or demos.

## CI and Deployment

CI currently runs:

* pytest
* ruff lint
* ruff format check
* local chunk generation with `scripts/ingest_docs.py`
* behavioral eval with `scripts/run_eval.py`
* Docker image build
* kubeconform validation for `k8s/*.yaml`

The repository includes a Dockerfile and Kubernetes manifest examples. CI does not run Promptfoo, publish images, or deploy to a real cluster.

## Roadmap

Suggested next milestones:

1. Import selected Kubernetes upstream docs from the existing registry.
2. Expand chunking and retrieval tests against imported upstream docs.
3. Improve retrieval quality while keeping deterministic evaluation.
4. Optionally add BM25, vector, or hybrid retrieval.
5. Optionally add a real LLM provider behind the provider interface.
6. Optionally add persistent trace storage.
7. Optionally add image publishing and deployment/CD workflow.

## Security and Safety

The repository must not include company-internal runbooks, credentials, kubeconfig files, private cluster names, private IP addresses, API keys, or real Secret values.

The assistant should be read-only and should not imply that it can inspect, modify, or repair a real cluster.

## Interview Talking Points

* Why LLM features need a gateway layer.
* Why curated retrieval sources can be better than mirroring everything early.
* How source metadata supports trust and debugging.
* How timeout and fallback improve reliability.
* Why prompt and response traces matter.
* Why deterministic behavioral evals are useful before real model integration.
* How licensing and attribution affect documentation-based RAG projects.
