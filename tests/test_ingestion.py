from pathlib import Path

from app.ingestion.chunker import chunk_markdown, split_by_headings
from app.ingestion.markdown import strip_yaml_frontmatter
from app.ingestion.registry import existing_registry_documents, load_registry_documents


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


def test_registry_identifies_existing_custom_runbook_documents() -> None:
    documents = load_registry_documents()
    existing_documents, missing_documents = existing_registry_documents(
        documents,
        root_dir=Path("."),
    )

    existing_ids = {document.document_id for document in existing_documents}

    assert "custom-pod-pending-troubleshooting" in existing_ids
    assert "custom-cronjob-backfill-checklist" in existing_ids
    assert len(missing_documents) > 0
