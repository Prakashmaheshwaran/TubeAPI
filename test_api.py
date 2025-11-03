"""
Test script for YouTube Download API
Run this to verify the service is working correctly.
"""

import requests
import json
import os

BASE_URL = "http://localhost:8000"
API_KEY = os.getenv("API_PASSWORD", "test-password")  # Set this in your environment

def test_health():
    """Test health endpoint"""
    print("Testing /health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health check passed")
            print(f"  Status: {data['status']}")
            print(f"  yt-dlp available: {data['ytdlp_available']}")
            return True
        else:
            print(f"✗ Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"✗ Could not connect to {BASE_URL}")
        print("  Make sure the server is running with: python main.py")
        return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_formats():
    """Test formats endpoint"""
    print("\nTesting /formats endpoint...")
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"  # Short "Me at the zoo" video
    
    try:
        headers = {"X-API-Key": API_KEY}
        response = requests.get(f"{BASE_URL}/formats", params={"url": test_url}, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Format extraction passed")
            print(f"  Video ID: {data['video_id']}")
            print(f"  Title: {data['title']}")
            print(f"  Available formats: {len(data['formats'])}")
            return True
        else:
            print(f"✗ Format extraction failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def test_download_validation():
    """Test download endpoint validation"""
    print("\nTesting /download endpoint validation...")
    
    # Test with invalid URL
    try:
        headers = {"X-API-Key": API_KEY}
        response = requests.post(
            f"{BASE_URL}/download",
            headers=headers,
            json={"video_url": "https://example.com/not-youtube"}
        )
        if response.status_code == 400:
            print("✓ URL validation working (correctly rejected invalid URL)")
            return True
        else:
            print(f"✗ Expected 400 status code, got {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("YouTube Download API - Test Suite")
    print("=" * 60)
    print()
    
    results = []
    
    # Test 1: Health check
    results.append(test_health())
    
    # Test 2: Format extraction
    results.append(test_formats())
    
    # Test 3: Download validation
    results.append(test_download_validation())
    
    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✓ All tests passed! The API is working correctly.")
        print("\nYou can now:")
        print("  - Visit http://localhost:8000/docs for interactive API documentation")
        print("  - Use the API with HTTP clients")
        print("  - Check README.md for usage examples")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)

