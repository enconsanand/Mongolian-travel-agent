#!/usr/bin/env python3
"""
Simple script to test rate limiting functionality
Run this script while your FastAPI server is running to verify rate limiting
"""

import time

import requests


def test_rate_limiting():
    """Test rate limiting by making multiple requests"""

    base_url = "http://localhost:8000"

    print("Rate Limiting Test")
    print("==================")
    print("Make sure your FastAPI server is running on http://localhost:8000")
    print()

    # Test 1: General endpoint rate limiting
    print("Testing general endpoint rate limiting (60 requests/minute)...")

    for i in range(5):
        try:
            response = requests.get(f"{base_url}/api/v1/users/me", timeout=5)
            print(f"Request {i + 1}: Status {response.status_code}")

            # Print rate limit headers if available
            if "X-RateLimit-Remaining" in response.headers:
                print(f"  Rate limit remaining: {response.headers['X-RateLimit-Remaining']}")
                print(f"  Rate limit: {response.headers.get('X-RateLimit-Limit', 'N/A')}")

            if response.status_code == 429:
                print(f"  Rate limited! Response: {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"Request {i + 1} failed: {e}")

        time.sleep(0.1)  # Small delay between requests

    print()

    # Test 2: Auth endpoint rate limiting (more restrictive)
    print("Testing auth endpoint rate limiting (5 requests/minute)...")

    auth_data = {"username": "test@example.com", "password": "testpass"}

    for i in range(7):  # Try more than the limit to trigger rate limiting
        try:
            response = requests.post(f"{base_url}/api/v1/auth/login", json=auth_data, timeout=5)
            print(f"Auth request {i + 1}: Status {response.status_code}")

            # Print rate limit headers if available
            if "X-RateLimit-Remaining" in response.headers:
                print(f"  Rate limit remaining: {response.headers['X-RateLimit-Remaining']}")
                print(f"  Rate limit: {response.headers.get('X-RateLimit-Limit', 'N/A')}")

            if response.status_code == 429:
                print("  ✅ Rate limited! This is expected after 5 requests")
                print(f"  Response: {response.text}")
                break

        except requests.exceptions.RequestException as e:
            print(f"Auth request {i + 1} failed: {e}")

        time.sleep(0.1)

    print()
    print("Rate limiting test completed!")
    print("Expected behavior:")
    print("- General endpoints: Allow 60 requests per minute")
    print("- Auth endpoints: Allow 5 requests per minute")
    print("- Rate limited requests return HTTP 429 status")


if __name__ == "__main__":
    try:
        test_rate_limiting()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:  # noqa: BLE001
        print(f"Test failed: {e}")
