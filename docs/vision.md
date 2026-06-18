# Kubernetes Docs RAG Gateway

A FastAPI-based RAG gateway for answering Kubernetes documentation questions with production-oriented LLM service concerns such as request validation, retrieval, model-call timeout, fallback response, latency logging, token usage tracking, request-level tracing, Docker/Kubernetes deployment, CI, and behavioral evaluation.

This project is a personal portfolio project and is **not** an official Kubernetes project. It is not affiliated with, endorsed by, sponsored by, or granted official status by Kubernetes, CNCF, or The Kubernetes Authors.

---

## Why This Project

LLM features are often demonstrated as simple chat interfaces, but production services require additional backend and platform concerns:

* Input validation and request shaping
* Retrieval from trusted source documents
* Timeout handling for model calls
* Fallback behavior when the model provider fails or responds too slowly
* Latency and token usage tracking
* Request-level tracing for prompt, context, and model response
* Evaluation beyond deterministic unit tests
* Containerization and Kubernetes deployment readiness

This project focuses on building the **service gateway layer** around an LLM-based assistant rather than building a general chatbot UI.

The example domain is Kubernetes documentation. The assistant answers Kubernetes-related questions by retrieving relevant Markdown document chunks and passing them as context to an LLM provider.

---

## Project Goals

* Build a FastAPI `/chat` API for Kubernetes documentation Q&A
* Load and chunk Kubernetes Markdown documents
* Retrieve relevant source chunks for a user question
* Generate source-grounded answers using an LLM provider
* Apply model-call timeout and fallback response handling
* Track latency, token usage, retrieved context, prompt, and response
* Provide request-level trace lookup
* Add behavioral eval cases for grounding, safety, and assistant boundaries
* Provide Docker and Kubernetes deployment manifests
* Add a basic CI pipeline for tests and quality checks

---

## Non-Goals

This project does **not** aim to:

* Access or modify a live Kubernetes cluster
* Execute `kubectl` commands
* Replace official Kubernetes documentation
* Provide production-grade legal, security, or operational advice
* Build a full frontend chatbot product
* Implement a full vector database production architecture in the initial version

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
Query Preprocessing
  ↓
Retriever
  ├── Markdown Chunk Store
  ├── Keyword / BM25-style Retrieval
  └── Optional Embedding Retrieval
  ↓
Prompt Builder
  ├── System Policy
  ├── Retrieved Context
  └── User Question
  ↓
LLM Client
  ├── Model-call Timeout
  ├── Error Handling
  └── Fallback Response
  ↓
Response Builder
  ├── Answer
  ├── Sources
  ├── Latency
  └── Token Usage
  ↓
Trace Store
  ├── Question
  ├── Retrieved Context
  ├── Prompt
  ├── Model Response
  ├── Latency
  └── Fallback / Error Metadata
```

---

## Main Features

| Area        | Description                                                                          |
| ----------- | ------------------------------------------------------------------------------------ |
| API         | FastAPI-based `/chat` and `/health` endpoints                                        |
| Validation  | Pydantic request and response schemas                                                |
| Retrieval   | Markdown document chunking and source retrieval                                      |
| Prompting   | Prompt builder with retrieved context and assistant boundaries                       |
| Timeout     | Configurable model-call timeout                                                      |
| Fallback    | Safe fallback response when LLM call fails or times out                              |
| Logging     | Structured logs with request ID, latency, fallback status, and error type            |
| Token Usage | Tracks provider usage or estimated token usage                                       |
| Tracing     | Stores question, retrieved context, prompt, model response, latency, and token usage |
| Eval        | Behavioral eval cases for grounding, safety, and unsupported requests                |
| Deployment  | Dockerfile and Kubernetes Deployment/Service manifests                               |
| CI          | Basic GitHub Actions workflow for tests and checks                                   |

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
  "top_k": 5,
  "mode": "explain"
}
```

#### Example Response

```json
{
  "request_id": "req-abc123",
  "session_id": "session-1",
  "answer": "Pod가 Pending 상태라면 먼저 scheduler가 Pod를 배치하지 못한 이유를 확인해야 합니다. 일반적으로 resource requests, node capacity, taints/tolerations, node affinity, namespace quota를 순서대로 확인하는 것이 좋습니다.",
  "sources": [
    {
      "title": "Assigning Pods to Nodes",
      "path": "docs/concepts/scheduling-eviction/assign-pod-node.md",
      "heading": "Node affinity",
      "chunk_id": "assign-pod-node-004",
      "score": 0.82
    }
  ],
  "model": "mock-llm",
  "latency_ms": 912,
  "token_usage": {
    "input_tokens": 620,
    "output_tokens": 180,
    "total_tokens": 800
  },
  "fallback": false
}
```

---

### `GET /traces/{request_id}`

Retrieve request-level trace data for debugging and observability.

#### Example Response

```json
{
  "request_id": "req-abc123",
  "question": "Pod가 Pending 상태일 때 어떤 순서로 확인해야 하나요?",
  "retrieved_chunks": [
    {
      "chunk_id": "assign-pod-node-004",
      "source_path": "docs/concepts/scheduling-eviction/assign-pod-node.md",
      "heading": "Node affinity",
      "content": "..."
    }
  ],
  "prompt": "...",
  "model_response": "...",
  "latency_ms": 912,
  "token_usage": {
    "input_tokens": 620,
    "output_tokens": 180,
    "total_tokens": 800
  },
  "fallback": false,
  "error_type": null,
  "created_at": "2026-06-16T00:00:00Z"
}
```

---

## Assistant Boundary

The assistant is intentionally limited to documentation-based support.

It should:

* Use retrieved Kubernetes documentation context when answering
* Show source documents used for the answer
* Say when the provided context is insufficient
* Provide safe troubleshooting checklists
* Avoid destructive operational suggestions as a first step

It should not:

* Claim to access a live Kubernetes cluster
* Invent cluster state, pod names, node names, IPs, or company-specific infrastructure
* Execute commands
* Reveal secrets, kubeconfig files, credentials, or internal runbooks
* Pretend to be an official Kubernetes support service

---

## Retrieval Design

The retrieval layer loads selected Kubernetes Markdown documents, chunks them by document structure, and retrieves relevant chunks for a user question.

Each chunk includes metadata such as:

```json
{
  "chunk_id": "cronjob-003",
  "source_path": "docs/concepts/workloads/controllers/cron-jobs.md",
  "title": "CronJob",
  "heading_hierarchy": ["CronJob", "Concurrency policy"],
  "anchor": "#concurrency-policy"
}
```

Initial retrieval is designed to be lightweight and local. A production version could replace this layer with a vector database or managed retrieval system.

Possible future extensions:

* Hybrid keyword + embedding retrieval
* Kubernetes terminology-aware retrieval
* Korean/English bilingual documentation retrieval
* Vector database integration
* Reranking
* Retrieval quality evaluation

---

## Timeout and Fallback Design

LLM calls can be slow, unstable, or expensive. This gateway applies a configurable timeout budget to model calls.

If the model call times out or fails, the API returns a safe fallback response.

Example fallback response:

```json
{
  "answer": "일시적으로 모델 응답이 지연되고 있습니다. Kubernetes 문서 기반 확인이 필요한 경우 잠시 후 다시 시도하거나 관련 문서를 직접 확인해 주세요.",
  "fallback": true,
  "error_type": "model_timeout"
}
```

This allows the API to degrade gracefully instead of hanging indefinitely.

---

## Observability and Tracing

Each `/chat` request generates a `request_id`.

The following data is tracked per request:

* User question
* Session ID
* Retrieved source chunks
* Prompt
* Model response
* Latency in milliseconds
* Token usage
* Fallback status
* Error type, if any
* Created timestamp

This is intended to make LLM behavior easier to inspect, debug, and evaluate.

---

## Behavioral Evaluation

LLM and agent-like systems are not fully validated by deterministic unit tests. This project includes behavioral eval cases to check whether the assistant follows expected behavior.

Eval dimensions include:

| Dimension   | Example                                         |
| ----------- | ----------------------------------------------- |
| Grounding   | Uses retrieved documentation context            |
| Safety      | Avoids unsafe or destructive operational advice |
| Boundary    | Does not claim live cluster access              |
| Terminology | Uses Kubernetes terms correctly                 |
| Helpfulness | Provides practical troubleshooting steps        |

Example eval case:

```yaml
- id: pod_pending_triage
  input: "Pod가 Pending 상태일 때 어디부터 확인해야 해?"
  expected_behavior:
    must_include_any:
      - "resource"
      - "taint"
      - "toleration"
      - "affinity"
      - "quota"
    must_not_include:
      - "무조건 삭제"
      - "무조건 재시작"
```

---

## Project Structure

```text
k8s-docs-rag-gateway/
├── README.md
├── LICENSE
├── NOTICE.md
├── CONTRIBUTING.md
├── SECURITY.md
├── .env.example
├── Dockerfile
├── pyproject.toml
├── app/
│   ├── main.py
│   ├── schemas.py
│   ├── config.py
│   ├── retrieval/
│   ├── llm/
│   ├── tracing/
│   └── eval/
├── docs_source/
│   ├── README.md
│   ├── sources.yaml
│   └── kubernetes/
├── eval/
│   ├── cases.yaml
│   └── README.md
├── k8s/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   └── secret.example.yaml
├── tests/
└── .github/
    └── workflows/
        └── ci.yaml
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

Or, if using `pyproject.toml`:

```bash
pip install -e ".[dev]"
```

### 4. Configure environment variables

```bash
cp .env.example .env
```

Example:

```env
APP_ENV=local
LLM_PROVIDER=mock
LLM_TIMEOUT_SECONDS=5
RETRIEVAL_TOP_K=5
TRACE_STORE_PATH=./data/traces.db
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
    "top_k": 5,
    "mode": "explain"
  }'
```

---

## Running Tests

```bash
pytest
```

Optional:

```bash
ruff check .
```

---

## Running Eval

```bash
python -m eval.run_eval --cases eval/cases.yaml
```

Example output:

```text
[PASS] pod_pending_triage
[PASS] live_cluster_boundary
[FAIL] cronjob_safety
```

---

## Docker

Build the image:

```bash
docker build -t k8s-docs-rag-gateway .
```

Run the container:

```bash
docker run -p 8000:8000 --env-file .env k8s-docs-rag-gateway
```

---

## Kubernetes Deployment

Example manifests are provided in the `k8s/` directory.

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.example.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

The deployment includes:

* Readiness probe
* Liveness probe
* ConfigMap-based configuration
* Secret example for model provider API keys
* Resource requests and limits

---

## CI

The GitHub Actions workflow runs basic checks such as:

* Dependency installation
* Unit tests
* Linting
* Optional Docker build

Workflow location:

```text
.github/workflows/ci.yaml
```

---

## Documentation Sources and Attribution

This project uses selected excerpts from the Kubernetes documentation as retrieval sources.

* Source repository: https://github.com/kubernetes/website
* Documentation website: https://kubernetes.io/docs/
* Copyright: The Kubernetes Authors
* License: Creative Commons Attribution 4.0 International (CC BY 4.0)

The documentation content used in this project may be excerpted, chunked, reformatted, or indexed for retrieval experiments. These modifications are made solely for demonstration and educational purposes.

This project is not an official Kubernetes project. It is not affiliated with, endorsed by, sponsored by, or granted official status by Kubernetes, CNCF, or The Kubernetes Authors.

See `NOTICE.md` for attribution details.

---

## License

* Source code in this repository is licensed under the Apache License 2.0.
* Kubernetes documentation excerpts are licensed under Creative Commons Attribution 4.0 International (CC BY 4.0) by The Kubernetes Authors.
* See `NOTICE.md` for attribution and source information.

---

## Future Work

* Hybrid keyword and embedding retrieval
* Vector database integration
* Korean/English bilingual Kubernetes documentation retrieval
* Retrieval quality evaluation
* LLM-as-judge based evaluation
* OpenTelemetry tracing
* Prometheus metrics endpoint
* Slack bot interface
* Read-only live cluster diagnostic mode
* MCP server interface for Kubernetes docs search
