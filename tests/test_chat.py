from fastapi.testclient import TestClient

from app.main import MOCK_CHAT_ANSWER, app

client = TestClient(app)


def test_chat_returns_mock_response() -> None:
    response = client.post(
        "/chat",
        json={
            "user_id": "user-1",
            "session_id": "session-1",
            "message": "How do I check pod status?",
            "top_k": 3,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["request_id"]
    assert body["answer"] == MOCK_CHAT_ANSWER
    assert body["sources"] == []
    assert body["model"] == "mock"
    assert body["fallback"] is False
    assert body["error_type"] is None
    assert body["latency_ms"] >= 0
    assert body["token_usage"] == {
        "input_tokens": 6,
        "output_tokens": 13,
        "total_tokens": 19,
    }


def test_chat_rejects_empty_message() -> None:
    response = client.post("/chat", json={"message": ""})

    assert response.status_code == 422


def test_chat_rejects_missing_message() -> None:
    response = client.post("/chat", json={})

    assert response.status_code == 422
