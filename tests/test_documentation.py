from pathlib import Path


def test_readme_describes_current_retrieval_limitations() -> None:
    readme = Path("README.md").read_text(encoding="utf-8").lower()

    assert "curated subset of kubernetes upstream docs" in readme
    assert "not the full kubernetes docs corpus" in readme
    assert "simple keyword retrieval" in readme
    assert "vector db" in readme
    assert "not implemented" in readme
