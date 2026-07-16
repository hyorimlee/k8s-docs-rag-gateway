# Technical Decisions

This document records the major technical decisions made while building `k8s-docs-rag-gateway`.

The goal of this project is not only to implement a RAG-style API, but also to show how AI-backed service gateways can be designed with production-oriented boundaries such as traceability, fallback handling, evaluation, regression testing, and future extensibility.

---

## 1. Project Scope: Local Deterministic Mock RAG Gateway First

### Decision

Start with a local deterministic mock RAG gateway instead of a real LLM-backed assistant.

### Why

The initial goal was to validate the backend architecture and service boundaries before introducing external model dependencies.

The first milestone focuses on:

* FastAPI API structure
* documentation ingestion
* chunking
* retrieval
* prompt construction
* provider abstraction
* timeout/fallback behavior
* traceability
* behavioral eval
* CI validation

Using a deterministic mock provider makes tests stable and repeatable.

### Alternatives Considered

#### Real LLM provider first

Rejected for the initial milestone because it would introduce:

* API keys and secret handling
* external network dependency
* cost
* rate limits
* non-deterministic outputs
* flaky tests
* CI complexity

Real LLM integration remains a future extension behind the provider interface.

#### Hardcoded Q&A or FAQ bot

Rejected because the goal is to build a RAG service gateway, not a static answer system. The architecture should retrieve source chunks and assemble prompts dynamically.

---

## 2. Documentation Source Strategy: Registry-Driven Sources

### Decision

Use a source registry under `docs_source/registry/` as the source of truth for documentation inputs.

### Why

The registry makes document ingestion explicit and traceable. It separates "what documents should be part of the corpus" from "which files have already been imported locally."

This supports:

* versioned documentation
* upstream source metadata
* local custom runbooks
* future Kubernetes upstream docs import
* missing document handling
* attribution

### Alternatives Considered

#### Scan every Markdown file automatically

Rejected for the foundation stage because it would make the corpus implicit and harder to audit.

#### Import the full Kubernetes docs immediately

Rejected initially because the project needed a small, reviewable corpus while the gateway architecture was still being built.

The roadmap keeps full or broader upstream docs import as a later corpus-expansion milestone.

---

## 3. Chunking Strategy: Markdown Heading-Based Chunking First

### Decision

Use Markdown heading-based chunking as the initial chunking strategy.

### Why

Kubernetes documentation is written in Markdown and has meaningful heading structure. Headings often represent natural conceptual boundaries such as:

* Pod lifecycle
* Taints and tolerations
* Resource requests and limits
* CronJob behavior
* ConfigMap usage
* Secrets

Heading-based chunking preserves document structure and produces chunks that are easier to trace back to source sections.

### Alternatives Considered

#### Fixed-size chunking

Rejected as the first strategy because fixed-size splitting can cut through semantic boundaries and make chunks harder to explain.

#### Semantic chunking

Deferred. Semantic chunking may be useful later, but it adds complexity and is not necessary before importing a larger corpus.

#### Token-based recursive splitting

Deferred as an enhancement. The planned direction is:

```text
Markdown heading-based chunking
-> split oversized sections by max token/character size
-> add overlap between sub-chunks
```

### Future Direction

For larger Kubernetes docs, improve chunking with:

* max token or character size
* overlap for oversized sections
* richer heading path metadata
* optional semantic chunking only if retrieval quality requires it

---

## 4. Metadata Strategy: Metadata Is Not Semantic Chunking

### Decision

Attach metadata to each chunk regardless of chunking method.

### Why

Metadata is required for traceability, filtering, source display, and future retrieval improvements.

Important metadata includes:

* `chunk_id`
* `document_id`
* `title`
* `heading`
* `source_url`
* `local_path`
* `docs_version`
* `imported_commit`
* `tags`

### Clarification

Adding metadata does not mean the system is doing semantic chunking.

```text
metadata = source/version/section information attached to a chunk
semantic chunking = splitting content based on semantic meaning changes
```

The current strategy is heading-based chunking with metadata.

---

## 5. Retrieval Strategy: Simple Deterministic Keyword Retrieval First

### Decision

Start with simple deterministic keyword retrieval over local chunks.

### Why

At the initial corpus size, a linear keyword scan is sufficient and easy to test.

The current retriever supports:

* lowercase word overlap
* heading/title boost
* tag boost
* deterministic sorting
* top-k retrieval
* traceable retrieval scores

This makes behavior transparent and suitable for CI.

### Alternatives Considered

#### Vector retrieval first

Deferred because the initial corpus is small. Vector retrieval becomes more meaningful after importing a larger Kubernetes upstream docs subset.

#### BM25 / inverted index

Deferred. BM25 would be a reasonable next improvement for lexical retrieval, especially as the corpus grows.

#### Hybrid retrieval

Deferred until both keyword and vector retrievers exist.

### Future Direction

The planned retrieval roadmap is:

```text
simple keyword retrieval
-> upstream docs corpus expansion
-> local semantic embedding + vector retrieval
-> retrieval eval
-> hybrid retrieval
-> optional reranking
```

---

## 6. Vector Retrieval Plan: Embedding as an Indexing Pipeline

### Decision

For v0.5.0, use a local Chroma-backed vector store instead of a raw FAISS index because the project goal is a production-oriented RAG service gateway rather than vector search internals. Chroma provides local persistence, collection management, document storage, metadata storage, and vector search behavior that fit the service architecture. The existing deterministic keyword retriever remains the baseline for comparison and regression testing.

### Why

Vector retrieval only becomes meaningful when there are enough chunks to compare semantic retrieval against keyword retrieval.

The v0.5.0 pipeline looks like:

```text
chunks.jsonl
-> hash embedding provider (deterministic, local, no downloads)
-> local Chroma collection
-> query embedding
-> top-k vector retrieval
-> prompt builder
```

### Limitations

* vector retrieval is local-only
* Chroma server mode is not used
* keyword retrieval remains the default
* deterministic hash embeddings are still used for tests and CI stability
* the optional semantic path uses a local Sentence Transformers model and requires an explicit install/download step
* no external embedding API
* no real LLM provider
* no hybrid retrieval yet
* no reranking yet

### Alternatives Considered

#### External embedding API first

Deferred because it introduces API keys, cost, network dependency, and CI complexity.

#### Managed vector DB first

Deferred because local Chroma is sufficient to validate the retrieval architecture before adding infrastructure complexity.

```text
chunks.jsonl
-> embedding model
-> vector index / vector DB
-> query embedding
-> top-k semantic retrieval
-> prompt builder
```

### Initial Technology Direction

Recommended first implementation:

```text
sentence-transformers + Chroma
```

Why:

* local execution
* no API key
* no external dependency
* good fit for this repository's local Chroma-backed retrieval architecture

Later options:

* Qdrant
* Pinecone
* hybrid BM25 + vector retrieval

### Alternatives Considered

#### External embedding API first

Deferred because it introduces API keys, cost, network dependency, and CI complexity.

#### Managed vector DB first

Deferred because local Chroma is sufficient to validate the retrieval architecture before adding infrastructure complexity.

#### Multilingual semantic model first

Deferred because this milestone is focused on English semantic search over the current Kubernetes documentation corpus and English-only queries.

---

## 7. Prompt Builder Role: Assemble Context, Rules, and User Question

### Decision

Keep prompt construction as a separate component.

### Why

The prompt builder is responsible for assembling:

* system boundary instructions
* retrieved documentation context
* source metadata
* user question
* output guidance
* no-context behavior

This separation makes it possible to inspect the exact prompt through traces and evals.

### Important Boundary Rules

The assistant should:

* answer from retrieved documentation context
* avoid fabricating unsupported information
* not claim live Kubernetes cluster access
* not ask users to paste raw secrets
* prefer safe diagnostic steps before destructive action
* acknowledge insufficient context when sources are missing

### Alternatives Considered

#### Build prompts directly inside `/chat`

Rejected because it would make the service harder to test, trace, and evolve.

#### Let provider construct the prompt

Rejected because provider should act as an adapter to a model interface, not own retrieval or prompt policy.

---

## 8. Provider Strategy: Provider Abstraction Before Real LLM

### Decision

Create an `LLMProvider` abstraction and implement a deterministic `MockLLMProvider`.

### Why

This makes the `/chat` service independent from any specific model vendor.

The current mock provider is intentionally deterministic and context-shaped for local testing.

It allows testing:

* provider interface
* token usage estimates
* provider timeout handling
* provider error fallback
* trace recording
* eval behavior

### Alternatives Considered

#### Add OpenAI/Gemini/Anthropic provider immediately

Deferred because real providers introduce secrets, cost, rate limits, and non-deterministic outputs.

#### Hardcode the answer inside `/chat`

Rejected because it would bypass the provider boundary and make future real provider integration harder.

### Future Direction

Potential provider implementations:

```text
MockLLMProvider
OpenAIProvider
GeminiProvider
AnthropicProvider
LocalLLMProvider
```

The `/chat` flow should not need to change significantly when swapping providers.

---

## 9. Fallback and Timeout Strategy

### Decision

Add schema-consistent fallback handling around the chat flow.

### Why

AI service gateways need predictable behavior under internal failures.

The service handles:

* `chunks_not_found`
* `retrieval_error`
* `prompt_build_error`
* `provider_error`
* `provider_timeout`

Fallback responses preserve the public response shape:

* `request_id`
* `answer`
* `sources`
* `model`
* `latency_ms`
* `token_usage`
* `fallback`
* `error_type`

### Alternatives Considered

#### Let exceptions propagate

Rejected because API users should receive safe, predictable responses instead of internal stack traces.

#### Handle only provider errors

Rejected because RAG pipelines can fail before provider invocation, including chunk loading, retrieval, and prompt construction.

---

## 10. Trace Strategy: In-Memory Trace Store First

### Decision

Add an in-memory trace store and expose `GET /traces/{request_id}`.

### Why

Traceability is central to debugging RAG behavior.

Traces include:

* original question
* retrieved chunks
* prompt
* returned sources
* provider response
* token usage
* latency
* fallback flag
* error type

This helps explain why an answer was produced.

### Alternatives Considered

#### Persistent database

Deferred. A database is unnecessary for the local foundation and would add infrastructure complexity.

#### No trace API

Rejected because prompt/retrieval observability is one of the main production-oriented learning goals of the project.

### Future Direction

Potential improvements:

* persistent trace store
* per-stage latency breakdown
* retrieval scores
* provider latency
* token/cost metrics
* tool-call traces
* agent state traces

---

## 11. Internal Eval Runner: Deterministic Behavioral Regression

### Decision

Create a custom deterministic eval runner using `eval/cases.yaml`.

### Why

Regular unit tests verify code-level correctness, but RAG systems need scenario-based behavior checks.

The internal eval validates:

* source grounding
* no-context behavior
* live-cluster boundary
* secret handling
* destructive-action boundary
* trace existence
* prompt content
* retrieved chunks
* fallback behavior
* token usage consistency

### Difference from Unit Tests

Unit tests answer:

```text
Does this function/class/API endpoint behave correctly?
```

Internal eval answers:

```text
Given a representative user scenario, does the full RAG gateway behave as expected?
```

### CI Gate

In `v0.2.0`, the internal eval runner became part of GitHub Actions CI.

CI now runs ingestion before eval so generated chunks exist.

### Alternatives Considered

#### Only use pytest

Rejected because pytest alone does not clearly express user-facing behavioral scenarios.

#### Use external eval tools only

Rejected because external tools cannot inspect internal prompt, trace, retrieved chunks, or fallback metadata as directly.

---

## 12. Promptfoo Strategy: Manual API-Level Regression Layer

### Decision

Add Promptfoo as a local/manual `/chat` API regression layer, separate from the internal eval runner.

### Why

Promptfoo tests the running FastAPI API from an external client perspective.

It checks that the HTTP `/chat` API response shows expected high-level behavior.

This complements the internal eval runner:

```text
Internal eval runner:
checks service internals such as prompt, trace, retrieved chunks, fallback, and token usage

Promptfoo:
checks black-box API response behavior over HTTP
```

### Why Promptfoo Is Not the CI Gate Yet

Promptfoo remains manual/local in `v0.3.0` because:

* internal eval is already the deterministic CI gate
* Promptfoo requires a running local server
* HTTP/server startup in CI adds complexity
* Promptfoo cache behavior can affect local regression results
* the project is still using a deterministic mock provider

### Promptfoo Cache Decision

Promptfoo can return cached HTTP responses from previous runs. During local testing, this caused stale old mock responses to be reused even though the current `/chat` API was working correctly. The verbose logs showed cached responses being returned for `http://127.0.0.1:8000/chat`, including the older generic mock answer.

Therefore, Promptfoo should be run with cache disabled:

```bash
npx promptfoo@latest eval -c promptfooconfig.yaml --no-cache
```

### Alternatives Considered

#### Make Promptfoo a required CI gate immediately

Deferred because the internal eval runner already provides deterministic CI coverage, and adding Promptfoo to CI would require server lifecycle management.

#### Remove Promptfoo

Not chosen because it provides useful experience with API-level regression tools and gives a black-box perspective distinct from internal evals.

---

## 13. CI Strategy

### Decision

Use GitHub Actions for tests, linting, formatting, Docker build, Kubernetes manifest validation, ingestion, and internal eval.

### Why

The goal is to keep the project continuously verifiable.

Current CI validates:

* pytest
* ruff lint
* ruff format
* Docker image build
* Kubernetes manifest validation
* documentation ingestion
* internal behavioral eval

### Trigger Decision

CI is configured for:

```yaml
on:
  push:
    branches:
      - main
  pull_request:
    branches:
      - main
```

This avoids unnecessary CI runs on every feature branch push while still validating PRs targeting main and direct pushes to main.

### CI Portability Decision

A failing CI test revealed that one subprocess test used `.venv/bin/python`, which exists locally but not in GitHub Actions.

The fix was to use:

```python
sys.executable
```

This ensures subprocess tests use the same Python interpreter that is running pytest.

---

## 14. Kubernetes Docs Import Strategy

### Decision

Import a curated Kubernetes upstream docs subset before adding vector retrieval.

### Why

Vector retrieval over only two custom runbooks would not provide meaningful comparison.

The corpus should first expand to include official Kubernetes docs for topics such as:

* Pods
* Pod lifecycle
* resource requests and limits
* scheduling
* taints and tolerations
* CronJobs
* ConfigMaps
* Secrets
* Deployments
* Horizontal Pod Autoscaling

### Alternatives Considered

#### Add vector retrieval immediately

Deferred because semantic retrieval is more meaningful with a larger corpus.

#### Import the full Kubernetes documentation immediately

Deferred because a curated subset is easier to review, test, and evaluate.

---

## 15. Roadmap Decisions

### Current Roadmap

```text
v0.1.0  Foundation
v0.2.0  Eval strengthening + CI gate
v0.3.0  Promptfoo /chat API regression
v0.4.0  Kubernetes upstream docs subset import
v0.5.0  Embedding + vector retrieval
v0.6.0  Retrieval eval + latency/token/cost metrics
v0.7.0  Tool-call mock + OpenAPI-style tool schema + tool trace
v0.8.0  LangGraph or ADK-style minimal agent workflow
v0.9.0  MCP-style mock server or MCP integration experiment
v1.0.0  Portfolio release + architecture doc + demo
```

### Why This Order

The sequence is designed to grow from a deterministic service gateway into a more realistic GenAI FDE-style system:

```text
gateway foundation
-> behavioral eval
-> API regression
-> real corpus expansion
-> vector retrieval
-> retrieval and LLM-native metrics
-> tool-calling
-> agent workflow
-> MCP experiment
-> portfolio release
```

This order avoids adding advanced AI features before the core service boundaries and evaluation structure are stable.
