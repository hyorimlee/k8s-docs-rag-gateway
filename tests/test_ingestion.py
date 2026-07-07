from pathlib import Path

from app.ingestion.chunker import chunk_markdown, split_by_headings
from app.ingestion.markdown import read_markdown, strip_yaml_frontmatter
from app.ingestion.registry import (
    RegistryDocument,
    existing_registry_documents,
    load_registry_documents,
)

IMPORTED_K8S_COMMIT = "fe4bd876c5335ba137b1b564d93258c446b4b0ee"
IMPORTED_K8S_DOCUMENT_IDS = {
    "k8s-assign-pods-to-nodes",
    "k8s-configmaps",
    "k8s-cronjobs",
    "k8s-deployments",
    "k8s-horizontal-pod-autoscaling",
    "k8s-jobs",
    "k8s-pod-lifecycle",
    "k8s-pods",
    "k8s-resource-management",
    "k8s-secrets",
    "k8s-taints-and-tolerations",
}


def test_heading_chunking_creates_expected_heading_paths() -> None:
    documents = load_registry_documents()
    document = next(
        doc
        for doc in documents
        if doc.document_id == "custom-pod-pending-troubleshooting"
    )

    chunks = chunk_markdown(
        document,
        "# Title\nIntro\n\n## Purpose\nPurpose text\n\n### Detail\nMore text\n",
    )

    assert [chunk.heading for chunk in chunks] == [
        "Title",
        "Title > Purpose",
        "Title > Purpose > Detail",
    ]
    assert chunks[0].content == "# Title\nIntro"
    assert chunks[0].document_id == document.document_id
    assert chunks[0].local_path == "docs_source/custom/pod-pending-troubleshooting.md"
    assert chunks[0].collection_ids == ["pod-pending-troubleshooting"]
    assert "pod-pending" in chunks[0].tags


def test_empty_sections_are_ignored() -> None:
    sections = split_by_headings("# Title\n\n## Empty\n\n## Filled\nBody\n")

    assert [(section.heading, section.content) for section in sections] == [
        ("Title > Filled", "## Filled\nBody")
    ]


def test_frontmatter_stripping_removes_yaml_header() -> None:
    content = "---\ntitle: Example\n---\n# Heading\nBody\n"

    assert strip_yaml_frontmatter(content) == "# Heading\nBody\n"


def test_registry_identifies_existing_documents() -> None:
    documents = load_registry_documents()
    existing_documents, missing_documents = existing_registry_documents(
        documents,
        root_dir=Path("."),
    )

    existing_ids = {document.document_id for document in existing_documents}

    assert "custom-pod-pending-troubleshooting" in existing_ids
    assert "custom-cronjob-backfill-checklist" in existing_ids
    assert IMPORTED_K8S_DOCUMENT_IDS.issubset(existing_ids)
    assert missing_documents == []


def test_registry_document_ids_are_unique() -> None:
    documents = load_registry_documents()
    document_ids = [document.document_id for document in documents]

    assert len(document_ids) == len(set(document_ids))


def test_imported_upstream_registry_entries_resolve_to_local_markdown() -> None:
    documents = imported_upstream_documents()

    assert {document.document_id for document in documents} == IMPORTED_K8S_DOCUMENT_IDS

    for document in documents:
        assert document.document_id
        assert document.title
        assert document.source_url
        assert document.docs_version
        assert document.local_path.suffix == ".md"
        assert document.local_path.exists()


def test_missing_registry_documents_are_reported_without_blocking_existing_docs(
    tmp_path: Path,
) -> None:
    existing_path = tmp_path / "existing.md"
    existing_path.write_text("# Existing\nBody\n", encoding="utf-8")
    existing_document = RegistryDocument(
        document_id="existing-doc",
        title="Existing Doc",
        source_url="https://example.com/existing",
        local_path=Path("existing.md"),
        docs_version="test",
        imported_commit=None,
    )
    missing_document = RegistryDocument(
        document_id="missing-doc",
        title="Missing Doc",
        source_url="https://example.com/missing",
        local_path=Path("missing.md"),
        docs_version="test",
        imported_commit=None,
    )

    existing_documents, missing_documents = existing_registry_documents(
        [existing_document, missing_document],
        root_dir=tmp_path,
    )
    chunks = chunk_markdown(
        existing_documents[0],
        read_markdown(tmp_path / existing_documents[0].local_path),
    )

    assert existing_documents == [existing_document]
    assert missing_documents == [missing_document]
    assert chunks


def test_imported_upstream_docs_preserve_metadata_in_chunks() -> None:
    hpa_document = next(
        document
        for document in imported_upstream_documents()
        if document.document_id == "k8s-horizontal-pod-autoscaling"
    )

    content = read_markdown(hpa_document.local_path)
    chunks = chunk_markdown(hpa_document, content)

    assert chunks
    assert chunks[0].document_id == "k8s-horizontal-pod-autoscaling"
    assert chunks[0].source_url == (
        "https://kubernetes.io/docs/tasks/run-application/"
        "horizontal-pod-autoscale-walkthrough/"
    )
    assert chunks[0].docs_version == "main@2026-07-02"
    assert chunks[0].imported_commit == IMPORTED_K8S_COMMIT
    assert chunks[0].local_path == (
        "docs_source/kubernetes/tasks/run-application/horizontal-pod-autoscale.md"
    )
    assert chunks[0].collection_ids == ["autoscaling-basics"]
    assert "hpa" in chunks[0].tags


def test_ingestion_chunks_include_custom_and_imported_upstream_docs() -> None:
    documents = load_registry_documents()
    chunks = [
        chunk
        for document in documents
        if document.local_path.exists()
        for chunk in chunk_markdown(document, read_markdown(document.local_path))
    ]
    chunk_document_ids = {chunk.document_id for chunk in chunks}

    assert "custom-pod-pending-troubleshooting" in chunk_document_ids
    assert "custom-cronjob-backfill-checklist" in chunk_document_ids
    assert IMPORTED_K8S_DOCUMENT_IDS.issubset(chunk_document_ids)


def test_imported_upstream_chunk_metadata_has_required_fields() -> None:
    documents = imported_upstream_documents()
    chunks = [
        chunk
        for document in documents
        for chunk in chunk_markdown(document, read_markdown(document.local_path))
    ]

    assert chunks
    for chunk in chunks:
        assert chunk.chunk_id
        assert chunk.document_id in IMPORTED_K8S_DOCUMENT_IDS
        assert chunk.title
        assert chunk.heading
        assert chunk.source_url
        assert chunk.docs_version
        assert chunk.local_path.startswith("docs_source/kubernetes/")


def imported_upstream_documents() -> list[RegistryDocument]:
    return [
        document
        for document in load_registry_documents()
        if document.document_id in IMPORTED_K8S_DOCUMENT_IDS
    ]
