#!/usr/bin/env python3
"""
Comprehensive security test script for FastAPI backend
Tests rate limiting, security headers, input validation, and CORS
"""

import requests


def test_security_headers():
    """Test that security headers are properly set"""
    print("Testing Security Headers...")
    print("-" * 40)

    try:
        response = requests.get("http://localhost:8000/health", timeout=5)

        expected_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
            "X-DNS-Prefetch-Control",
            "Server",
        ]

        print(f"Status: {response.status_code}")
        print("Security Headers:")

        for header in expected_headers:
            value = response.headers.get(header, "MISSING")
            status = "✅" if value != "MISSING" else "❌"
            print(f"  {status} {header}: {value}")

        # Check CSP header
        csp = response.headers.get("Content-Security-Policy", "MISSING")
        csp_status = "✅" if csp != "MISSING" else "❌"
        print(f"  {csp_status} Content-Security-Policy: {csp[:50]}...")

        print()

    except Exception as e:  # noqa: BLE001
        print(f"Security headers test failed: {e}")
        print()


def test_rate_limiting():
    """Test rate limiting functionality"""
    print("Testing Rate Limiting...")
    print("-" * 40)

    # Test general endpoint rate limiting
    print("General endpoints (60/min):")
    for i in range(3):
        try:
            response = requests.get("http://localhost:8000/test-rate-limit", timeout=5)
            remaining = response.headers.get("X-RateLimit-Remaining", "N/A")
            print(f"  Request {i + 1}: Status {response.status_code}, Remaining: {remaining}")
        except Exception as e:  # noqa: BLE001
            print(f"  Request {i + 1} failed: {e}")

    # Test auth endpoint rate limiting
    print("\nAuth endpoints (5/min):")
    auth_data = {"username": "test@example.com", "password": "testpass"}

    for i in range(6):
        try:
            response = requests.post("http://localhost:8000/api/v1/auth/login", json=auth_data, timeout=5)
            remaining = response.headers.get("X-RateLimit-Remaining", "N/A")
            print(f"  Auth {i + 1}: Status {response.status_code}, Remaining: {remaining}")

            if response.status_code == 429:
                print("  ✅ Rate limiting working correctly!")
                break

        except Exception as e:  # noqa: BLE001
            print(f"  Auth {i + 1} failed: {e}")

    print()


def test_input_validation():
    """Test input validation against malicious payloads"""
    print("Testing Input Validation...")
    print("-" * 40)

    # Test malicious payloads
    malicious_payloads = [
        {"test": "<script>alert('xss')</script>"},
        {"test": "'; DROP TABLE users; --"},
        {"test": "../../../etc/passwd"},
        {"test": "javascript:alert(1)"},
        {"username": "admin", "password": "' OR '1'='1"},
    ]

    for i, payload in enumerate(malicious_payloads, 1):
        try:
            response = requests.post("http://localhost:8000/api/v1/auth/login", json=payload, timeout=5)

            status = "✅ BLOCKED" if response.status_code == 400 else "❌ ALLOWED"
            print(f"  Payload {i}: {status} (Status: {response.status_code})")

        except Exception as e:  # noqa: BLE001
            print(f"  Payload {i}: Error - {e}")

    print()


def test_cors_configuration():
    """Test CORS configuration"""
    print("Testing CORS Configuration...")
    print("-" * 40)

    try:
        # Make a preflight request
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Authorization",
        }

        response = requests.options("http://localhost:8000/api/v1/users/me", headers=headers, timeout=5)

        print(f"Preflight Status: {response.status_code}")

        cors_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods",
            "Access-Control-Allow-Headers",
            "Access-Control-Allow-Credentials",
        ]

        for header in cors_headers:
            value = response.headers.get(header, "MISSING")
            status = "✅" if value != "MISSING" else "❌"
            print(f"  {status} {header}: {value}")

        print()

    except Exception as e:  # noqa: BLE001
        print(f"CORS test failed: {e}")
        print()


def test_request_logging():
    """Test that request logging is working"""
    print("Testing Request Logging...")
    print("-" * 40)

    try:
        response = requests.get("http://localhost:8000/health", timeout=5)

        # Check for request ID header
        request_id = response.headers.get("X-Request-ID")
        if request_id:
            print(f"  ✅ Request ID generated: {request_id}")
        else:
            print("  ❌ Request ID missing")

        print(f"  Status: {response.status_code}")
        print("  Note: Check server logs for detailed request information")
        print()

    except Exception as e:  # noqa: BLE001
        print(f"Request logging test failed: {e}")
        print()


def main():
    """Run all security tests"""
    print("FastAPI Security Test Suite")
    print("=" * 60)
    print("Make sure your FastAPI server is running on http://localhost:8000")
    print("=" * 60)
    print()

    # Run all tests
    test_security_headers()
    test_rate_limiting()
    test_input_validation()
    test_cors_configuration()
    test_request_logging()

    print("Security testing completed!")
    print("Review the results above and check server logs for detailed information.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nTesting interrupted by user")
    except Exception as e:  # noqa: BLE001
        print(f"Test suite failed: {e}")
