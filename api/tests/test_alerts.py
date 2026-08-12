def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_list_alerts_returns_paginated_shape(client):
    resp = client.get("/alerts", params={"page": 1, "page_size": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"items", "total", "page", "page_size"}
    assert body["page"] == 1
    assert body["page_size"] == 5
    assert len(body["items"]) <= 5
    if body["items"]:
        item = body["items"][0]
        assert item["status"] in ("open", "closed")
        assert item["severity"] in ("low", "medium", "high", "critical")


def test_list_alerts_filters_by_severity(client):
    resp = client.get("/alerts", params={"severity": "critical", "page_size": 50})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(item["severity"] == "critical" for item in items)


def test_list_alerts_rejects_invalid_severity(client):
    resp = client.get("/alerts", params={"severity": "extreme"})
    assert resp.status_code == 422


def test_get_alert_detail_for_real_alert(client):
    listing = client.get("/alerts", params={"page_size": 1}).json()
    assert listing["items"], "expected at least one alert in the warehouse for this test"
    alert_id = listing["items"][0]["alert_id"]

    resp = client.get(f"/alerts/{alert_id}")
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["alert_id"] == alert_id
    assert "account_history" in detail
    assert "notes" in detail


def test_get_alert_detail_404_for_missing_alert(client):
    resp = client.get("/alerts/999999999")
    assert resp.status_code == 404


def test_disposition_then_duplicate_disposition_conflicts(client):
    listing = client.get("/alerts", params={"status": "open", "page_size": 1}).json()
    assert listing["items"], "expected at least one open alert for this test"
    alert_id = listing["items"][0]["alert_id"]

    first = client.post(
        f"/alerts/{alert_id}/disposition",
        json={"analyst_id": "test-analyst", "outcome": "false_positive", "rationale_notes": "unit test"},
    )
    assert first.status_code == 201
    assert first.json()["outcome"] == "false_positive"

    second = client.post(
        f"/alerts/{alert_id}/disposition",
        json={"analyst_id": "test-analyst", "outcome": "true_positive", "rationale_notes": "duplicate"},
    )
    assert second.status_code == 409

    detail = client.get(f"/alerts/{alert_id}").json()
    assert detail["status"] == "closed"
    assert detail["disposition"]["outcome"] == "false_positive"


def test_disposition_rejects_invalid_outcome(client):
    listing = client.get("/alerts", params={"page_size": 1}).json()
    alert_id = listing["items"][0]["alert_id"]
    resp = client.post(
        f"/alerts/{alert_id}/disposition",
        json={"analyst_id": "test-analyst", "outcome": "maybe", "rationale_notes": "x"},
    )
    assert resp.status_code == 422


def test_disposition_404_for_missing_alert(client):
    resp = client.post(
        "/alerts/999999999/disposition",
        json={"analyst_id": "test-analyst", "outcome": "false_positive", "rationale_notes": "x"},
    )
    assert resp.status_code == 404


def test_add_note_and_see_it_in_detail(client):
    listing = client.get("/alerts", params={"page_size": 1}).json()
    alert_id = listing["items"][0]["alert_id"]

    resp = client.post(f"/alerts/{alert_id}/notes", json={"author": "test-analyst", "note_text": "checked balances"})
    assert resp.status_code == 201

    detail = client.get(f"/alerts/{alert_id}").json()
    assert any(n["note_text"] == "checked balances" for n in detail["notes"])
