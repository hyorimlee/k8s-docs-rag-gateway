# Kubernetes Docs RAG Gateway

Kubernetes Docs RAG Gateway is a planned FastAPI-based, versioned documentation assistant gateway for experimenting with retrieval-augmented generation over selected Kubernetes documentation.

This is a personal portfolio project. It is not an official Kubernetes project and is not affiliated with, endorsed by, or sponsored by Kubernetes, CNCF, or The Kubernetes Authors.

## Current Status

This repository currently has the documentation/source-registry foundation, local Markdown ingestion with heading-aware chunking to a JSONL artifact, simple local chunk retrieval using keyword overlap and metadata boosts, an internal prompt builder that formats retrieved chunks with assistant boundary rules, an LLM provider interface with a deterministic mock provider, a FastAPI app with `GET /health`, a mock RAG-style `POST /chat`, and in-memory `GET /traces/{request_id}`, Docker build support for the current app, Kubernetes manifest examples for the current app, and a GitHub Actions CI workflow for pytest, ruff checks, Docker image build verification, and Kubernetes manifest validation.

The `POST /chat` endpoint now loads generated local chunks, retrieves relevant chunks, builds a structured prompt, calls the deterministic mock provider, returns source metadata when local chunks match, and stores an in-memory execution trace. It includes safe fallback responses for missing chunks and expected internal mock-flow failures, including a simple provider timeout boundary. Real LLM generation, embeddings, a vector database, persistent trace storage, image publishing, deployment workflow, and eval runner have not been implemented yet.

## Planned Project

The intended project is a read-only gateway service that answers Kubernetes documentation questions by:

* receiving a user question through a future FastAPI `/chat` API
* retrieving relevant chunks from a curated, versioned subset of Kubernetes documentation
* building a source-grounded prompt
* using a mock LLM provider for local development and an optional real provider later
* returning an answer with source metadata
* tracking latency, token usage, fallback status, and request traces
* supporting behavioral evaluation for grounding and assistant boundaries

The goal is to demonstrate backend and platform concerns around LLM features, not to replace official Kubernetes documentation or provide official support. Answers should be based on a specific Kubernetes documentation version or pinned upstream commit, not on an unspecified documentation state or a live Kubernetes cluster.

## Documentation

* [Vision](docs/vision.md)
* [Project Spec](docs/project-spec.md)
* [Documentation Source Registry](docs_source/README.md)
* [Attribution Notice](NOTICE.md)

## Roadmap

### Phase 1: Documentation Foundation

* [x] Project README
* [x] Long-term vision document
* [x] Project specification
* [x] Documentation source registry structure
* [x] Kubernetes documentation attribution notice
* [x] Apache License 2.0 for project source code

### Phase 2: FastAPI Skeleton

* [x] FastAPI application package
* [x] `GET /health`
* [x] basic configuration
* [x] test and lint setup

### Phase 3: Chat Contract

* [x] `POST /chat`
* [x] request and response schemas
* [x] request ID generation
* [x] mock response
* [x] latency and token usage fields

### Phase 4: Documentation Retrieval

* [ ] import selected Kubernetes documentation from the registered upstream
* [x] Markdown document loading
* [x] heading-aware chunking
* [x] lightweight local retrieval
* [x] source metadata in responses

### Phase 5: Gateway Reliability

* [x] prompt builder
* [x] mock LLM provider abstraction
* [ ] optional real LLM provider
* [x] model-call timeout
* [x] safe fallback response
* [x] structured error metadata

### Phase 6: Observability and Evaluation

* [x] in-memory trace store
* [x] `GET /traces/{request_id}`
* [ ] latency and token usage tracking
* [ ] behavioral eval cases
* [ ] eval runner

### Phase 7: Deployment and CI

* [x] GitHub Actions workflow for pytest and ruff checks
* [x] Dockerfile for the minimal FastAPI app
* [x] Docker build check in CI
* [x] Kubernetes Deployment and Service manifests
* [x] ConfigMap and secret example
* [x] Kubernetes manifest validation in CI
* [ ] optional image publishing workflow

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

The ingestion script reads local Markdown files referenced by the source registry and writes heading-based chunk metadata to:

```text
artifacts/chunks.jsonl
```

Many registered upstream Kubernetes documentation files are placeholders and have not been downloaded yet, so the ingestion summary may report missing local documents. Run ingestion before testing `/chat` locally if you want source metadata in chat responses.

Run simple local chunk retrieval after ingestion:

```bash
python scripts/retrieve_chunks.py "pod pending scheduling"
```

Retrieval loads `artifacts/chunks.jsonl`, scores chunks with lowercase keyword overlap, and applies simple boosts for heading/title and tag matches. It does not use embeddings or a vector database.

Build a structured prompt manually after ingestion:

```bash
python scripts/build_prompt.py "pod pending scheduling"
```

The prompt builder formats retrieved chunk metadata and content with assistant boundary rules. It does not call a real LLM.

Run the deterministic mock provider manually:

```bash
python scripts/mock_generate.py "example prompt"
```

The provider interface accepts a prompt and returns a model-like response with simple estimated token usage. The mock provider does not call an external API, and no real LLM provider SDK or API key is configured.

Run the FastAPI server locally:

```bash
uvicorn app.main:app --reload
```

Check the health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

Call the mock chat endpoint:

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"How do I check pod status?"}'
```

The response is generated by the local mock RAG-style flow: load generated chunks, retrieve relevant chunks, build a prompt, call the deterministic mock provider, and return source metadata. If chunks are missing or an expected internal step fails, `/chat` returns a safe fallback response with `fallback=true` and a specific `error_type`. It does not call an external LLM, use embeddings or a vector database, inspect clusters, persist traces, run evaluation, or provide full Kubernetes documentation Q&A.

Retrieve an in-memory trace for a chat response:

```bash
curl http://127.0.0.1:8000/traces/<request_id>
```

Traces include the question, final answer, returned sources, retrieved chunk metadata and content, built prompt, model, token usage, latency, fallback status, error type, and creation time. They are stored only in process memory and disappear when the process restarts.

Build and run the Docker image for the current minimal FastAPI app:

```bash
docker build -t k8s-docs-rag-gateway:local .
docker run --rm -p 8000:8000 k8s-docs-rag-gateway:local
```

Then check the health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

## Kubernetes Manifests

The `k8s/` directory contains deployment-ready example manifests for running the current minimal FastAPI app and its `GET /health` endpoint. CI validates these manifests with kubeconform, but does not apply them to a cluster.

Apply the non-secret manifests with:

```bash
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/deployment.yaml
kubectl apply -f k8s/service.yaml
```

`k8s/secret.example.yaml` is an example only. Do not put real secrets in that file or commit real secrets to the repository.

## Documentation Sources and Attribution

This project plans to use selected excerpts from the Kubernetes documentation as retrieval sources.

* Source repository: https://github.com/kubernetes/website
* Documentation website: https://kubernetes.io/docs/
* Copyright: The Kubernetes Authors
* License: Creative Commons Attribution 4.0 International (CC BY 4.0)

Kubernetes documentation excerpts are not licensed under this project's Apache License 2.0. They remain under CC BY 4.0 and are attributed in [NOTICE.md](NOTICE.md).

## Safety Boundary

The planned assistant is read-only and documentation-grounded. It must not claim to inspect live clusters, execute `kubectl`, access kubeconfig files, reveal secrets, invent private infrastructure details, or present itself as an official Kubernetes service.

## License

Source code created for this project is licensed under the Apache License 2.0. Kubernetes documentation excerpts follow CC BY 4.0 and are attributed separately in [NOTICE.md](NOTICE.md).
