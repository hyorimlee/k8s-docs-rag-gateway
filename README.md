# Kubernetes Docs RAG Gateway

Kubernetes Docs RAG Gateway is a FastAPI-based mock RAG service gateway over versioned Kubernetes documentation sources. It is currently deterministic and local: it uses generated JSONL chunks, simple keyword retrieval, a prompt builder, and a `MockLLMProvider` instead of real LLM generation.

This is a personal portfolio project. It is not an official Kubernetes project and is not affiliated with, endorsed by, or sponsored by Kubernetes, CNCF, or The Kubernetes Authors.

## Current Status

Implemented:

* documentation/source-registry foundation
* local Markdown ingestion and heading-based chunking to `artifacts/chunks.jsonl`
* simple keyword retrieval with heading/title and tag boosts
* deterministic prompt builder with assistant boundary rules
* provider interface and deterministic `MockLLMProvider`
* `GET /health`
* `POST /chat` using the local mock RAG-style flow
* fallback handling for missing chunks, retrieval errors, prompt errors, provider errors, and provider timeout
* in-memory trace store and `GET /traces/{request_id}`
* local deterministic behavioral eval with `eval/cases.yaml` and `scripts/run_eval.py`
* pytest and ruff setup
* Dockerfile
* Kubernetes manifest examples
* GitHub Actions CI for tests, ruff, Docker build, and kubeconform manifest validation

Current limitations:

* Real LLM generation is not implemented.
* No external LLM APIs or provider SDKs are used.
* Embeddings, vector DB, hybrid retrieval, and reranking are not implemented.
* Kubernetes upstream docs are registered but mostly not imported yet.
* The current local corpus is intentionally small and mainly custom runbooks.
* The trace store is in-memory only and disappears on process restart.
* Behavioral eval checks deterministic mock-flow fields, traces, prompts, sources, and fallback metadata; it is not a real LLM quality benchmark.
* Image publishing, CD, and real Kubernetes deployment automation are not implemented.
* This is not a full Kubernetes documentation Q&A assistant yet.

## Current Architecture

```text
POST /chat
  |
  v
load artifacts/chunks.jsonl
  |
  v
simple keyword retrieval
  |
  v
prompt builder
  |
  v
MockLLMProvider
  |
  v
response with answer, sources, token usage, latency, fallback/error metadata
  |
  v
in-memory trace store -> GET /traces/{request_id}
```

The mock provider returns deterministic context-shaped text for local testing. The useful grounding signal today is in the returned source metadata and the saved trace prompt/context, not in real natural-language model quality.

## Documentation

* [Vision](docs/vision.md)
* [Project Spec](docs/project-spec.md)
* [Documentation Source Registry](docs_source/README.md)
* [Attribution Notice](NOTICE.md)

## Local Development

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install runtime and development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run tests:

```bash
pytest
```

Run lint and format checks:

```bash
ruff check .
ruff format --check .
```

Run local documentation ingestion:

```bash
python scripts/ingest_docs.py
```

The ingestion script reads local Markdown files referenced by the registry, skips missing local files gracefully, and writes heading-based chunk metadata to:

```text
artifacts/chunks.jsonl
```

Many registered upstream Kubernetes docs are placeholders until the upstream import step is implemented, so missing local docs are expected.

Run simple local chunk retrieval:

```bash
python scripts/retrieve_chunks.py "pod pending scheduling"
```

Build a structured prompt:

```bash
python scripts/build_prompt.py "pod pending scheduling"
```

Run the deterministic mock provider:

```bash
python scripts/mock_generate.py "example prompt"
```

Run local behavioral eval:

```bash
python scripts/run_eval.py
```

The eval runner loads [eval/cases.yaml](eval/cases.yaml), calls the local chat service without a live server, and checks deterministic expectations against response fields and in-memory traces.

Run the FastAPI app:

```bash
uvicorn app.main:app --reload
```

Check health:

```bash
curl http://127.0.0.1:8000/health
```

Call chat:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"What should I check for a Pending Pod?","top_k":3}'
```

If `artifacts/chunks.jsonl` exists and matching chunks are found, `/chat` returns source metadata. If chunks are missing, it returns a safe fallback with `fallback=true` and `error_type="chunks_not_found"`.

Retrieve an in-memory trace:

```bash
curl http://127.0.0.1:8000/traces/<request_id>
```

Traces include the question, final answer, returned sources, retrieved chunk metadata and content, built prompt, model, token usage, latency, fallback status, error type, and creation time. They are process-local only.

Build and run the Docker image:

```bash
docker build -t k8s-docs-rag-gateway:local .
docker run --rm -p 8000:8000 k8s-docs-rag-gateway:local
```

Validate Kubernetes manifests if `kubeconform` is installed:

```bash
kubeconform -strict -summary k8s/*.yaml
```

## API Summary

### `GET /health`

Returns service metadata:

```json
{
  "status": "ok",
  "service": "k8s-docs-rag-gateway",
  "environment": "local",
  "version": "0.1.0"
}
```

### `POST /chat`

Request:

```json
{
  "user_id": "user-1",
  "session_id": "session-1",
  "message": "What should I check for a Pending Pod?",
  "top_k": 3,
  "mode": "mock"
}
```

Response fields:

* `request_id`
* `answer`
* `sources`
* `model`
* `latency_ms`
* `token_usage`
* `fallback`
* `error_type`

The answer is generated by the deterministic mock provider. The endpoint does not call an external LLM.

### `GET /traces/{request_id}`

Returns the in-memory trace for a previous `/chat` request, or `404` if the request ID is unknown or the process restarted.

## Roadmap

Next likely milestones:

* import selected Kubernetes upstream docs from the registry
* expand chunk and retrieval tests against imported upstream docs
* improve retrieval quality while keeping deterministic test coverage
* optionally add BM25, vector, or hybrid retrieval
* optionally add a real LLM provider behind the existing provider interface
* optionally add persistent trace storage
* optionally add image publishing and deployment/CD workflow

## Kubernetes Manifests

The `k8s/` directory contains example manifests for running the current FastAPI app. CI validates these manifests with kubeconform, but does not apply them to a cluster.

Apply the non-secret manifests with:

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

`k8s/secret.example.yaml` is an example only. Do not put real secrets in that file or commit real secrets to the repository.

## Documentation Sources and Attribution

This project plans to use selected excerpts from Kubernetes documentation as retrieval sources.

* Source repository: https://github.com/kubernetes/website
* Documentation website: https://kubernetes.io/docs/
* Copyright: The Kubernetes Authors
* License: Creative Commons Attribution 4.0 International (CC BY 4.0)

Kubernetes documentation excerpts are not licensed under this project's Apache License 2.0. They remain under CC BY 4.0 and are attributed in [NOTICE.md](NOTICE.md).

## Safety Boundary

The assistant is intended to be read-only and documentation-grounded. It must not claim to inspect live clusters, execute `kubectl`, access kubeconfig files, reveal secrets, invent private infrastructure details, or present itself as an official Kubernetes service.

## License

Source code created for this project is licensed under the Apache License 2.0. Kubernetes documentation excerpts follow CC BY 4.0 and are attributed separately in [NOTICE.md](NOTICE.md).
