# Kubernetes Docs RAG Gateway

A FastAPI-based experimental gateway for building a Kubernetes documentation assistant with RAG-like retrieval and production-oriented LLM service concerns.

This project is a personal portfolio project and is **not** an official Kubernetes project. It is not affiliated with, endorsed by, sponsored by, or granted official status by Kubernetes, CNCF, or The Kubernetes Authors.

---

## Overview

This project explores how an LLM-based documentation assistant can be wrapped with a backend/service gateway layer.

The initial goal is to build a small but practical Kubernetes documentation assistant that can:

* Receive Kubernetes-related questions through a FastAPI `/chat` API
* Retrieve relevant Markdown document chunks from selected Kubernetes documentation
* Pass retrieved context to an LLM or mock LLM provider
* Return an answer with source references
* Track basic request metadata such as latency and token usage
* Provide a foundation for timeout handling, fallback response, tracing, Docker/Kubernetes deployment, CI, and behavioral evaluation

The project focuses less on building a general chatbot UI and more on understanding the backend/platform layer required to operate LLM features reliably.

---

## Why This Project

LLM features often start as simple API calls, but production services need additional concerns around reliability, cost, observability, and evaluation.

This project is designed to study those concerns in a concrete domain: Kubernetes documentation.

Key questions this project explores:

* How should a backend API validate and shape LLM requests?
* How can retrieved documentation context be attached to a user question?
* How should a service handle slow or failed model calls?
* What metadata should be logged for debugging and evaluation?
* How can prompt, context, response, latency, and token usage be traced per request?
* Why do LLM/agent-like features need behavioral evaluation beyond deterministic unit tests?

---

## Current Scope

The current version focuses on a small MVP.

### Implemented / Initial Target

* FastAPI application structure
* `GET /health` endpoint
* `POST /chat` endpoint
* Pydantic request/response schema
* Local Markdown document loading
* Basic document chunking
* Lightweight retrieval over selected Kubernetes docs
* Mock LLM provider for local development
* Basic latency measurement
* Basic token usage estimation
* Source metadata returned with answers

### Planned Next

* Model-call timeout
* Fallback response on timeout or provider error
* Request-level tracing
* Prompt/context/model response storage
* `GET /traces/{request_id}`
* Dockerfile
* Kubernetes Deployment/Service manifests
* GitHub Actions CI
* Behavioral eval cases
* Eval runner
* Optional real LLM provider integration

---

## Non-Goals

This project does **not** aim to:

* Access a live Kubernetes cluster
* Execute `kubectl` commands
* Modify cluster resources
* Replace official Kubernetes documentation
* Provide official Kubernetes support
* Build a full production chatbot product
* Use private company runbooks or internal infrastructure information

The assistant is designed as a **read-only documentation assistant**.

---

## Architecture

```text
Client
  ↓
FastAPI /chat
  ↓
Request Validation
  ↓
Retriever
  ├── Markdown Documents
  └── Document Chunks
  ↓
Prompt Builder
  ├── Retrieved Context
  └── User Question
  ↓
LLM Provider
  ├── Mock Provider
  └── Real Provider planned
  ↓
Response Builder
  ├── Answer
  ├── Sources
  ├── Latency
  └── Token Usage
```

Planned production-oriented extensions:

```text
LLM Provider
  ↓
Timeout / Fallback Handler
  ↓
Trace Store
  ├── Question
  ├── Retrieved Context
  ├── Prompt
  ├── Model Response
  ├── Latency
  └── Token Usage
  ↓
Behavioral Eval
```

---

## API

### `GET /health`

Health check endpoint.

#### Example Response

```json
{
  "status": "ok",
  "service": "k8s-docs-rag-gateway"
}
```

---

### `POST /chat`

Ask a Kubernetes documentation question.

#### Example Request

```json
{
  "user_id": "user-1",
  "session_id": "session-1",
  "message": "Pod가 Pending 상태일 때 어떤 순서로 확인해야 하나요?",
  "top_k": 3
}
```

#### Example Response

```json
{
  "request_id": "req-abc123",
  "session_id": "session-1",
  "answer": "Pod가 Pending 상태라면 먼저 scheduler가 Pod를 배치하지 못한 이유를 확인해야 합니다. 일반적으로 resource requests, node capacity, taints/tolerations, node affinity, namespace quota 등을 순서대로 확인할 수 있습니다.",
  "sources": [
    {
      "title": "Assigning Pods to Nodes",
      "path": "docs/concepts/scheduling-eviction/assign-pod-node.md",
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
  "fallback": false
}
```

---

## Assistant Boundary

The assistant should:

* Answer using retrieved Kubernetes documentation context
* Return source metadata when possible
* Say when retrieved context is insufficient
* Provide safe troubleshooting checklists
* Avoid pretending to inspect a real cluster

The assistant should not:

* Claim to access a live Kubernetes cluster
* Invent pod names, node names, IPs, or company-specific infrastructure
* Execute or imply execution of commands
* Recommend destructive actions as a first step
* Present itself as an official Kubernetes service

---

## Retrieval Design

The retrieval layer uses selected Kubernetes Markdown documents as source material.

The initial version uses lightweight local retrieval. Each document is split into chunks with metadata such as:

```json
{
  "chunk_id": "cronjob-003",
  "source_path": "docs/concepts/workloads/controllers/cron-jobs.md",
  "title": "CronJob",
  "heading": "Concurrency policy"
}
```

Future versions may add:

* BM25-style retrieval
* Embedding-based retrieval
* Hybrid keyword + embedding retrieval
* Reranking
* Korean/English bilingual retrieval

## Design Vision

This project starts with a small MVP and is intended to evolve into a more complete production-oriented RAG gateway.

See [`docs/vision.md`](docs/vision.md) for the long-term design vision, including tracing, behavioral evaluation, Kubernetes deployment, CI, and future extensions.
---

## Project Structure

```text
k8s-docs-rag-gateway/
├── README.md
├── LICENSE
├── NOTICE.md
├── .env.example
├── requirements.txt
├── app/
│   ├── main.py
│   ├── schemas.py
│   ├── config.py
│   ├── retrieval/
│   ├── llm/
│   └── utils/
├── docs_source/
│   ├── README.md
│   ├── sources.yaml
│   └── kubernetes/
├── tests/
└── k8s/
    └── README.md
```

Planned structure:

```text
├── tracing/
├── eval/
├── Dockerfile
├── .github/workflows/ci.yaml
└── k8s/
    ├── deployment.yaml
    ├── service.yaml
    ├── configmap.yaml
    └── secret.example.yaml
```

---

## Local Development

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/k8s-docs-rag-gateway.git
cd k8s-docs-rag-gateway
```

### 2. Create a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Example:

```env
APP_ENV=local
LLM_PROVIDER=mock
RETRIEVAL_TOP_K=3
```

### 5. Run the server

```bash
uvicorn app.main:app --reload
```

### 6. Test the API

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user-1",
    "session_id": "session-1",
    "message": "Pod가 Pending 상태일 때 어떤 순서로 확인해야 하나요?",
    "top_k": 3
  }'
```

---

## Testing

```bash
pytest
```

Planned checks:

```bash
ruff check .
```

---

## Roadmap

### Phase 1: MVP

* [ ] FastAPI `/health`
* [ ] FastAPI `/chat`
* [ ] Request validation
* [ ] Markdown docs loader
* [ ] Basic chunking
* [ ] Simple retrieval
* [ ] Mock LLM provider
* [ ] Source metadata in response

### Phase 2: Gateway Reliability

* [ ] Model-call timeout
* [ ] Fallback response
* [ ] Structured logging
* [ ] Latency tracking
* [ ] Token usage tracking
* [ ] Error type tracking

### Phase 3: Observability

* [ ] Request ID
* [ ] Trace store
* [ ] Prompt/context/response storage
* [ ] `GET /traces/{request_id}`

### Phase 4: Deployment

* [ ] Dockerfile
* [ ] Kubernetes Deployment
* [ ] Kubernetes Service
* [ ] ConfigMap
* [ ] Secret example
* [ ] Readiness/liveness probes

### Phase 5: Evaluation

* [ ] Behavioral eval cases
* [ ] Eval runner
* [ ] Grounding checks
* [ ] Boundary checks
* [ ] Safety checks

### Phase 6: CI

* [ ] GitHub Actions workflow
* [ ] Unit tests
* [ ] Linting
* [ ] Optional Docker build check

---

## Documentation Sources and Attribution

This project uses selected excerpts from the Kubernetes documentation as retrieval sources.

* Source repository: https://github.com/kubernetes/website
* Documentation website: https://kubernetes.io/docs/
* Copyright: The Kubernetes Authors
* License: Creative Commons Attribution 4.0 International (CC BY 4.0)

The documentation content used in this project may be excerpted, chunked, reformatted, or indexed for retrieval experiments. These modifications are made for demonstration and educational purposes.

This project is not an official Kubernetes project. It is not affiliated with, endorsed by, sponsored by, or granted official status by Kubernetes, CNCF, or The Kubernetes Authors.

See `NOTICE.md` for attribution details.

---

## License

* Source code in this repository is licensed under the Apache License 2.0.
* Kubernetes documentation excerpts are licensed under Creative Commons Attribution 4.0 International (CC BY 4.0) by The Kubernetes Authors.
* See `NOTICE.md` for attribution and source information.
