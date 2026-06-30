# Documentation Source Registry

This directory defines documentation sources for Kubernetes Docs RAG Gateway.

The project treats documentation sources as versioned, attributable retrieval inputs. Answers should be grounded in registered local chunks from a known source, not in an unspecified documentation state and not in a live Kubernetes cluster.

## Current Status

Implemented today:

* registry YAML files under `docs_source/registry/`
* local custom runbooks under `docs_source/custom/`
* ingestion script that reads registry entries and local Markdown files
* YAML frontmatter stripping
* heading-based chunking
* JSONL artifact generation at `artifacts/chunks.jsonl`
* graceful skipping of missing local documents

Current local Markdown files:

* `docs_source/custom/pod-pending-troubleshooting.md`
* `docs_source/custom/cronjob-backfill-checklist.md`

Many official Kubernetes registry entries already exist, but their upstream Markdown files have not been imported yet. A registry entry is therefore a planned/declared source unless its `local_path` exists in the working tree.

## Registry Entries vs Imported Files

Registry files under `docs_source/registry/documents/*.yaml` can reference local paths before those files exist. This lets the project plan a curated source set before downloading upstream Kubernetes docs.

The ingestion script:

```bash
python scripts/ingest_docs.py
```

loads all registry entries, reads local Markdown files that exist, skips missing files, writes chunks to:

```text
artifacts/chunks.jsonl
```

and prints counts for:

* registry documents found
* local documents read
* chunks written
* missing documents

Missing upstream docs are expected until the Kubernetes documentation import milestone is implemented.

## Source Selection Strategy

Sources are selected based on target questions and eval cases. The first source set supports questions such as:

* Why is a Pod stuck in Pending?
* What should I check before running a CronJob backfill?
* What is the difference between a Job and a CronJob?
* How do resource requests affect scheduling?
* How do taints and tolerations affect placement?
* How are ConfigMaps and Secrets different?
* What can the assistant answer without live cluster access?

Documents should be added when they support a specific question, collection, or behavioral eval. They should not be added only because they are generally useful.

Every imported Kubernetes document should be traceable to:

* `docs_version`, such as a Kubernetes documentation version label
* `imported_commit`, the upstream `kubernetes/website` commit used for import
* `imported_at`, the import timestamp
* `upstream_repo_path`, the path under the upstream repository
* `source_url`, the canonical documentation URL
* `local_path`, the imported local Markdown path

These fields make answers reproducible and help explain which documentation snapshot supported a response.

## Why Not Import All English Docs First?

The initial version does not import all of `content/en/docs` because full-site ingestion would make early retrieval quality harder to evaluate. Large source sets can hide basic issues in chunking, ranking, source attribution, prompt construction, trace review, and fallback behavior.

For the MVP, curated source selection helps the project:

* keep the retrieval corpus small enough to inspect manually
* verify that each document supports a known target question
* validate chunk boundaries against a manageable set of Markdown structures
* connect each source to one or more behavioral eval cases
* produce traces that are easy to review during debugging
* avoid measuring retrieval quality against an uncontrolled document set too early
* keep attribution and source metadata visible in every registry entry

This does not mean the project should remain small forever. The curated subset is the starting point for quality control, not a permanent limitation.

## Future Full English Docs Ingestion

The registry structure is intentionally expandable so it can later support full ingestion of the upstream `content/en/docs` directory from `https://github.com/kubernetes/website`.

To support full ingestion later, future registry entries should preserve:

* documentation version
* upstream source repository and commit
* import timestamp
* upstream repository path
* canonical documentation URL
* local imported path
* language
* topic or collection membership
* license and attribution metadata
* chunking and trace metadata needed by the retrieval pipeline

For curated MVP sources, these fields are written manually. For full ingestion, the same registry shape can be generated or enriched automatically from the upstream docs tree. Full ingestion should still pin the upstream commit so retrieval, traces, and eval results can be reproduced later.

## Source Expansion Plan

### v0.1 Current Curated Local Corpus

Use local custom runbooks plus registered upstream placeholders to validate ingestion, retrieval, prompt construction, traces, and eval mechanics.

### v0.2 Import Selected Upstream Docs

Import the registered Kubernetes workload, scheduling, configuration, and autoscaling Markdown files from a pinned upstream commit. Keep the corpus small enough to inspect manually.

### v0.3 Topic-Based Expansion

Add more topic groups as eval coverage grows. Candidate areas include Services, networking basics, storage basics, rollout troubleshooting, security context basics, and additional controller behavior.

### v1.0 Full `content/en/docs` Ingestion

Ingest the full English Kubernetes documentation tree from upstream `content/en/docs`. At this stage, registry entries may be generated from upstream metadata, and retrieval evaluation should include broad corpus tests, topic filtering, source attribution checks, and trace sampling across the full imported set.

## Registry Structure

```text
docs_source/
├── README.md
├── registry/
│   ├── upstreams.yaml
│   ├── collections.yaml
│   └── documents/
│       ├── kubernetes-workloads.yaml
│       ├── kubernetes-scheduling.yaml
│       ├── kubernetes-configuration.yaml
│       ├── kubernetes-autoscaling.yaml
│       └── custom-runbooks.yaml
├── kubernetes/
│   └── ...
└── custom/
    ├── pod-pending-troubleshooting.md
    └── cronjob-backfill-checklist.md
```

`registry/upstreams.yaml` defines upstream source projects. `registry/collections.yaml` defines logical retrieval collections. `registry/documents/*.yaml` defines individual source documents grouped by topic.

## Attribution and Non-Affiliation

Kubernetes documentation is authored by The Kubernetes Authors and licensed under Creative Commons Attribution 4.0 International (CC BY 4.0).

This project may later excerpt, chunk, reformat, or index selected Kubernetes documentation for retrieval experiments. Those documentation excerpts remain under CC BY 4.0 and are attributed in the repository `NOTICE.md`.

This project is a personal portfolio project. It is not affiliated with, endorsed by, or sponsored by Kubernetes, CNCF, or The Kubernetes Authors.

## Custom Runbook Rules

Custom runbooks in `docs_source/custom/` must be generic and portfolio-safe.

They must not include:

* company-internal procedures
* customer data
* private cluster names
* private IP addresses
* kubeconfig files
* credentials
* real Secret values
* internal service names

Custom runbooks should connect public Kubernetes concepts into safe troubleshooting checklists without implying access to a real cluster.
