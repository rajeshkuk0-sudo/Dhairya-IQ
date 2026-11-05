import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from main import app

EXPECTED_FIELDS = {
    "query",
    "query_id",
    "answer",
    "citation",
    "last_updated",
    "notice",
    "refused",
    "mode",
}


def main() -> int:
    client = TestClient(app)

    health = client.get("/api/health")
    print("health", health.status_code, health.json())
    assert health.status_code == 200
    assert health.json()["chunks"] == 67

    config = client.get("/api/config")
    print("config", config.status_code, len(config.json()["examples"]))
    assert config.status_code == 200
    assert config.json()["examples"]

    index = client.get("/")
    print("index", index.status_code, index.headers.get("content-type"))
    assert index.status_code == 200

    guard = client.post("/api/ask", json={"query": "Should I invest in HDFC Large Cap Fund?"})
    print("guard", guard.status_code, guard.json())
    assert guard.status_code == 200
    assert set(guard.json()) == EXPECTED_FIELDS
    assert guard.json()["refused"] is True
    assert guard.json()["mode"] == "guardrail"

    fact = client.post(
        "/api/ask",
        json={"query": "What is the expense ratio of HDFC Flexi Cap Fund Direct Growth?"},
    )
    print("fact", fact.status_code, fact.json())
    assert fact.status_code == 200
    assert set(fact.json()) == EXPECTED_FIELDS
    assert fact.json()["answer"]

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
