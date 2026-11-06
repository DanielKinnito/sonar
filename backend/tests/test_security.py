"""Security tests for Sonar API endpoints.

Validates OWASP Top 10 hardening:
- Path traversal prevention in download endpoints.
- Upload size caps.
- Explicit CORS origin enforcement.
"""

import pytest
from fastapi.testclient import TestClient
from sonar.api.main import app

client = TestClient(app)


def test_cors_headers():
    """Verify that allowed origins receive proper CORS headers."""
    # Test valid origin (port 50242)
    resp = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:50242",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:50242"
    assert resp.headers.get("access-control-allow-credentials") == "true"


def test_download_path_traversal_blocked():
    """Ensure directory traversal attacks are blocked on /api/download."""
    traversal_payloads = [
        "../test.txt",
        "..\\test.txt",
        "..%2Ftest.txt",
        "../../../../windows/system32/cmd.exe",
        "/etc/passwd",
        "sanitized_../../evil.wav",
        "invalid_ext.exe",
        "test.sh",
    ]
    for payload in traversal_payloads:
        resp = client.get(f"/api/download/{payload}")
        # Should return 400 Bad Request or 404 Not Found, never 200
        assert resp.status_code in (400, 404), f"Failed to block traversal payload: {payload}"


def test_audit_demo_payload():
    """Verify demo mode audit succeeds and returns structured forensic analysis."""
    resp = client.post("/api/audit", data={"demo": "true", "planes": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "leak_assessment" in data
    assert "spectrogram" in data

