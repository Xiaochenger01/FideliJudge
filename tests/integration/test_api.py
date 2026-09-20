from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_evaluation_api():
    r = client.post(
        "/api/v1/evaluations",
        json={
            "before_text": "项目于2025年6月11日完成验收，项目金额为1850万元。",
            "after_text": "项目于2025年完成验收，项目金额为1800万元。",
        },
    )
    assert r.status_code == 200
    meta = r.json()
    task_id = meta["task_id"]
    assert meta["status"] == "COMPLETED"

    status = client.get(f"/api/v1/evaluations/{task_id}")
    assert status.status_code == 200

    result = client.get(f"/api/v1/evaluations/{task_id}/result")
    assert result.status_code == 200
    body = result.json()
    assert body["route"] in {"REVIEW", "REJECT"}

    issues = client.get(f"/api/v1/evaluations/{task_id}/issues")
    assert issues.status_code == 200
    assert "issues" in issues.json()

    trace = client.get(f"/api/v1/evaluations/{task_id}/trace")
    assert trace.status_code == 200
    assert trace.json()["task_id"] == task_id
