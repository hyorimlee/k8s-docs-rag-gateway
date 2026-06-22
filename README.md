# Kubernetes Docs RAG Gateway

Kubernetes Docs RAG Gateway is a planned FastAPI-based, versioned documentation assistant gateway for experimenting with retrieval-augmented generation over selected Kubernetes documentation.

This is a personal portfolio project. It is not an official Kubernetes project and is not affiliated with, endorsed by, or sponsored by Kubernetes, CNCF, or The Kubernetes Authors.

## Current Status

This repository currently has the documentation/source-registry foundation, a minimal FastAPI skeleton with `GET /health`, Docker build support for the current app, and a GitHub Actions CI workflow for pytest, ruff checks, and Docker image build verification.

No `/chat` endpoint, retrieval pipeline, LLM provider, Kubernetes manifests, image publishing, deployment workflow, tracing, or eval runner has been implemented yet.

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

* [ ] `POST /chat`
* [ ] request and response schemas
* [ ] request ID generation
* [ ] mock response
* [ ] latency and token usage fields

### Phase 4: Documentation Retrieval

* [ ] import selected Kubernetes documentation from the registered upstream
* [ ] Markdown document loading
* [ ] heading-aware chunking
* [ ] lightweight local retrieval
* [ ] source metadata in responses

### Phase 5: Gateway Reliability

* [ ] prompt builder
* [ ] mock LLM provider abstraction
* [ ] optional real LLM provider
* [ ] model-call timeout
* [ ] safe fallback response
* [ ] structured error metadata

### Phase 6: Observability and Evaluation

* [ ] trace store
* [ ] `GET /traces/{request_id}`
* [ ] latency and token usage tracking
* [ ] behavioral eval cases
* [ ] eval runner

### Phase 7: Deployment and CI

* [x] GitHub Actions workflow for pytest and ruff checks
* [x] Dockerfile for the minimal FastAPI app
* [x] Docker build check in CI
* [ ] Kubernetes Deployment and Service manifests
* [ ] ConfigMap and secret example
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

Run the FastAPI server locally:

```bash
uvicorn app.main:app --reload
```

Check the health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

Build and run the Docker image for the current minimal FastAPI app:

```bash
docker build -t k8s-docs-rag-gateway:local .
docker run --rm -p 8000:8000 k8s-docs-rag-gateway:local
```

Then check the health endpoint:

```bash
curl http://127.0.0.1:8000/health
```

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
