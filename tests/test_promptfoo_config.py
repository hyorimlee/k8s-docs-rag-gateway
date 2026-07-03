from pathlib import Path

import yaml


def test_promptfoo_config_disables_cache() -> None:
    config = load_promptfoo_config()

    assert config["evaluateOptions"] == {"cache": False}


def test_promptfoo_config_targets_chat_api() -> None:
    config = load_promptfoo_config()

    provider = config["providers"][0]

    assert provider["id"] == "http"
    assert provider["config"]["url"] == "http://127.0.0.1:8000/chat"
    assert provider["config"]["method"] == "POST"
    assert provider["config"]["body"] == {
        "message": "{{prompt}}",
        "top_k": 2,
    }
    assert provider["config"]["transformResponse"] == "json.answer"


def test_promptfoo_config_includes_representative_cases() -> None:
    config = load_promptfoo_config()
    descriptions = {test["description"] for test in config["tests"]}
    prompts = {test["vars"]["prompt"] for test in config["tests"]}

    assert descriptions == {
        "pod_pending_triage",
        "cronjob_backfill_safety",
        "live_cluster_boundary",
        "secret_handling",
        "unknown_context",
    }
    assert "A Pod is stuck in Pending. What should I check first?" in prompts
    assert "How should I safely rerun a missed CronJob backfill?" in prompts
    assert "How do I improve my sourdough bread starter?" in prompts


def test_promptfoo_config_uses_deterministic_assertions_only() -> None:
    config = load_promptfoo_config()
    allowed_assertion_types = {"contains", "not-contains"}

    for test in config["tests"]:
        assert test["assert"]
        for assertion in test["assert"]:
            assert assertion["type"] in allowed_assertion_types


def load_promptfoo_config() -> dict:
    return yaml.safe_load(Path("promptfooconfig.yaml").read_text(encoding="utf-8"))
