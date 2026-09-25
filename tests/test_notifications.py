"""
tests/test_notifications.py

Automated test suite for Phase 24 Authority Notification & Alert Workflow.
Validates:
1. Case 001 Negative Result (No vessel attribution supported / Negative control)
2. Case 002 AIS Limitation (AIS data unavailable / Attribution suppressed)
3. Case 003 Positive Ranking (Strongly supported hypothesis: Golden Ray Rank #1)
4. Non-prejudicial forensic language compliance
5. API endpoints (/api/cases/{case_id}/notifications, /api/notifications, /api/notifications/{id})
"""

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.notification_builder import build_authority_notifications

client = TestClient(app)


def test_case_001_negative_control_notification():
    """Verify Case 001 emits INSUFFICIENT_EVIDENCE with non-prejudicial negative-control phrasing."""
    feed = build_authority_notifications("case_001")
    assert feed.case_id == "case_001"
    assert feed.total_alerts >= 3
    assert feed.latest_attribution_alert is not None

    latest = feed.latest_attribution_alert
    assert latest.alert_type == "INSUFFICIENT_EVIDENCE"
    assert latest.attribution_status == "NEGATIVE_CONTROL"
    assert latest.top_supported_hypothesis == "No vessel attribution is currently supported."
    assert "No vessel attribution is currently supported." in latest.body_markdown

    # Assert non-prejudicial language
    body_lower = latest.body_markdown.lower()
    assert "caused the spill" not in body_lower
    assert "culprit" not in body_lower
    assert "guilty" not in body_lower
    assert "legal proof" not in body_lower
    assert "high risk" not in body_lower

    # Verify pipeline infrastructure mention
    assert "Pipeline 001" in latest.body_markdown


def test_case_002_ais_unavailable_notification():
    """Verify Case 002 emits AIS_DATA_UNAVAILABLE with attribution suppression explanation."""
    feed = build_authority_notifications("case_002_wakashio")
    assert feed.case_id == "case_002_wakashio"
    assert feed.latest_attribution_alert is not None

    latest = feed.latest_attribution_alert
    assert latest.alert_type == "AIS_DATA_UNAVAILABLE"
    assert latest.attribution_status == "AIS_UNAVAILABLE"
    assert latest.candidate_vessel_count == 0
    assert latest.top_supported_hypothesis == "No vessel attribution is currently supported."
    assert "commercial data paywalls" in latest.body_markdown or "paywalled" in latest.body_markdown

    body_lower = latest.body_markdown.lower()
    assert "caused the spill" not in body_lower
    assert "culprit" not in body_lower


def test_case_003_positive_ranking_notification():
    """Verify Case 003 emits STRONGLY_SUPPORTED_HYPOTHESIS with exact required phrasing."""
    feed = build_authority_notifications("case_003_golden_ray")
    assert feed.case_id == "case_003_golden_ray"
    assert feed.latest_attribution_alert is not None

    latest = feed.latest_attribution_alert
    assert latest.alert_type == "STRONGLY_SUPPORTED_HYPOTHESIS"
    assert latest.attribution_status == "STRONGLY_SUPPORTED"
    assert latest.candidate_vessel_count == 25
    assert latest.severity == "ACTION_REQUIRED"

    # Strict phrasing check
    assert "is currently the highest-ranked hypothesis under the available evidence." in latest.top_supported_hypothesis
    assert "GOLDEN RAY" in latest.top_supported_hypothesis
    assert "538007762" in latest.top_supported_hypothesis

    # Verify absence of prejudicial statements
    body_lower = latest.body_markdown.lower()
    assert "this vessel caused the spill" not in body_lower
    assert "culprit" not in body_lower
    assert "guilty" not in body_lower


def test_api_case_notifications_endpoint():
    """Verify GET /api/cases/{case_id}/notifications returns valid feed."""
    resp = client.get("/api/cases/case_003_golden_ray/notifications")
    assert resp.status_code == 200
    data = resp.json()
    assert data["case_id"] == "case_003_golden_ray"
    assert data["total_alerts"] >= 3
    assert len(data["alerts"]) == data["total_alerts"]

    # Verify all alert types in feed
    types = [a["alert_type"] for a in data["alerts"]]
    assert "POTENTIAL_SPILL_DETECTED" in types
    assert "INVESTIGATION_READY" in types
    assert "STRONGLY_SUPPORTED_HYPOTHESIS" in types


def test_api_all_notifications_endpoint():
    """Verify GET /api/notifications returns aggregated alert feed sorted by time."""
    resp = client.get("/api/notifications")
    assert resp.status_code == 200
    alerts = resp.json()
    assert isinstance(alerts, list)
    assert len(alerts) >= 6

    # Verify specific alert lookup
    sample_id = alerts[0]["alert_id"]
    resp_single = client.get(f"/api/notifications/{sample_id}")
    assert resp_single.status_code == 200
    assert resp_single.json()["alert_id"] == sample_id


def test_api_notifications_error_handling():
    """Verify 400 path traversal and 404 missing alert."""
    # Path traversal
    resp_trav = client.get("/api/cases/..%2F..%2Fetc/notifications")
    assert resp_trav.status_code in [400, 404]

    # Nonexistent alert
    resp_missing = client.get("/api/notifications/alert_nonexistent_9999")
    assert resp_missing.status_code == 404
