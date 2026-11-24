#!/usr/bin/env python3
"""Read-only smoke check for a fresh, loopback-only Counsel dev installation.

Does not start services, submit documents, call AI, or change data.
"""
import http.client
import json
import sys


def get(port, path):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request("GET", path)
        response = conn.getresponse()
        if response.status != 200:
            raise RuntimeError(f"{port}{path}: expected HTTP 200, got {response.status}")
        body = response.read(1_048_577)
        if len(body) > 1_048_576:
            raise RuntimeError(f"{port}{path}: response exceeds smoke check limit")
        return body.decode("utf-8")
    finally:
        conn.close()


def main():
    try:
        health = json.loads(get(8000, "/health"))
        if health.get("status") != "healthy":
            raise RuntimeError("Backend is not reporting healthy status")
        print("PASS: backend health")
        branding = json.loads(get(8000, "/api/v1/branding"))
        expected = {
            "firm_name": "SmartProBono Counsel",
            "primary_color": "#0D766E",
            "secondary_color": "#10263D",
            "accent_color": "#51D5C5",
        }
        for field, value in expected.items():
            if branding.get(field) != value:
                raise RuntimeError(f"Fresh-install branding mismatch: {field}")
        print("PASS: backend default branding")
        html = get(3000, "/")
        if "<title>SmartProBono Counsel | Legal Workspace</title>" not in html:
            raise RuntimeError("Frontend title mismatch")
        print("PASS: frontend title")
    except (OSError, ValueError, RuntimeError, http.client.HTTPException) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    print("Loopback smoke checks passed; browser workflows and security remain separate gates.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
