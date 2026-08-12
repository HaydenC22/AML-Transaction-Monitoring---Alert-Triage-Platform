def test_overview_returns_expected_shape(client):
    resp = client.get("/metrics/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {
        "alert_volume_by_day", "fp_rate_trend", "severity_breakdown",
        "analyst_throughput_by_day", "latest_pipeline_run",
    }
    assert isinstance(body["alert_volume_by_day"], list)
    assert isinstance(body["severity_breakdown"], list)
    if body["latest_pipeline_run"]:
        assert "rows_processed" in body["latest_pipeline_run"]


def test_case_timeline_for_real_alert(client):
    listing = client.get("/alerts", params={"page_size": 1}).json()
    alert_id = listing["items"][0]["alert_id"]

    resp = client.get(f"/metrics/cases/{alert_id}/timeline")
    assert resp.status_code == 200
    points = resp.json()
    assert isinstance(points, list)
    if points:
        assert {"day_offset", "transaction_count", "total_amount"} <= points[0].keys()


def test_case_timeline_404_for_missing_alert(client):
    resp = client.get("/metrics/cases/999999999/timeline")
    assert resp.status_code == 404
