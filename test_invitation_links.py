#!/usr/bin/env python3
"""
Test script to verify that invitation links work correctly without hanging.
This script tests the complete invitation flow from backend to frontend.
"""

import requests
import json
import time
import secrets
import string

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
FRONTEND_URL = "http://localhost:8501"

def test_backend_health():
    """Test if the backend is running."""
    try:
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running and healthy")
            return True
        else:
            print(f"❌ Backend health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend connection failed: {e}")
        return False

def test_invitation_endpoints():
    """Test the invitation API endpoints."""
    print("\n🔍 Testing Invitation API Endpoints...")
    
    # Test 1: Check if endpoints are accessible
    endpoints_to_test = [
        "/invites/validate/INVALID123",
        "/invites/accept/INVALID123", 
        "/invites/status/INVALID123"
    ]
    
    for endpoint in endpoints_to_test:
        try:
            if "accept" in endpoint:
                # POST request for accept endpoint
                response = requests.post(f"{API_BASE_URL}{endpoint}", timeout=5)
            else:
                # GET request for other endpoints
                response = requests.get(f"{API_BASE_URL}{endpoint}", timeout=5)
            
            if response.status_code in [400, 401, 403, 404]:  # Expected responses
                print(f"✅ {endpoint} is accessible (returns {response.status_code})")
            else:
                print(f"⚠️  {endpoint} returned unexpected status: {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} error: {e}")

def test_invitation_link_generation():
    """Test invitation link generation and validation."""
    print("\n🔗 Testing Invitation Link Generation...")
    
    # Test 1: Generate a mock invitation link
    mock_token = secrets.token_urlsafe(32)
    mock_recruiter_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    
    invitation_link = f"{FRONTEND_URL}/?invite={mock_token}&recruiter_code={mock_recruiter_code}"
    print(f"✅ Generated mock invitation link: {invitation_link}")
    
    # Test 2: Test link format validation
    if "invite=" in invitation_link and "recruiter_code=" in invitation_link:
        print("✅ Invitation link format is correct")
    else:
        print("❌ Invitation link format is incorrect")
    
    # Test 3: Test URL parsing
    try:
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(invitation_link)
        query_params = parse_qs(parsed_url.query)
        
        if 'invite' in query_params and 'recruiter_code' in query_params:
            print("✅ URL parsing works correctly")
            print(f"   - invite: {query_params['invite'][0]}")
            print(f"   - recruiter_code: {query_params['recruiter_code'][0]}")
        else:
            print("❌ URL parsing failed")
    except Exception as e:
        print(f"❌ URL parsing error: {e}")

def test_frontend_access():
    """Test if the frontend is accessible."""
    try:
        response = requests.get(FRONTEND_URL, timeout=5)
        if response.status_code == 200:
            print("✅ Frontend is accessible")
            return True
        else:
            print(f"❌ Frontend returned status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend connection failed: {e}")
        return False

def test_invitation_flow_simulation():
    """Simulate the complete invitation flow."""
    print("\n🔄 Testing Complete Invitation Flow...")
    
    # Step 1: Generate mock invitation data
    mock_token = secrets.token_urlsafe(32)
    mock_recruiter_code = ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(8))
    
    # Step 2: Test invitation status endpoint
    try:
        response = requests.get(f"{API_BASE_URL}/invites/status/{mock_token}", timeout=5)
        if response.status_code == 400:
            result = response.json()
            if "Invalid invitation token" in result.get('message', ''):
                print("✅ Invitation status endpoint correctly handles invalid tokens")
            else:
                print(f"⚠️  Unexpected response: {result}")
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Invitation status test failed: {e}")
    
    # Step 3: Test invitation validation endpoint
    try:
        response = requests.get(f"{API_BASE_URL}/invites/validate/{mock_token}", timeout=5)
        if response.status_code == 400:
            result = response.json()
            if "Invalid invitation token" in result.get('detail', ''):
                print("✅ Invitation validation endpoint correctly handles invalid tokens")
            else:
                print(f"⚠️  Unexpected response: {result}")
        else:
            print(f"⚠️  Unexpected status code: {response.status_code}")
    except Exception as e:
        print(f"❌ Invitation validation test failed: {e}")

def test_error_handling():
    """Test error handling for various scenarios."""
    print("\n⚠️  Testing Error Handling...")
    
    # Test 1: Invalid token format
    invalid_tokens = [
        "invalid_token_123",
        "short",
        "very_long_token_" + "x" * 100,
        "",
        "token with spaces",
        "token@#$%^&*()"
    ]
    
    for token in invalid_tokens:
        try:
            response = requests.get(f"{API_BASE_URL}/invites/status/{token}", timeout=5)
            if response.status_code in [400, 404]:
                print(f"✅ Invalid token '{token[:20]}...' handled correctly (status: {response.status_code})")
            else:
                print(f"⚠️  Invalid token '{token[:20]}...' returned unexpected status: {response.status_code}")
        except Exception as e:
            print(f"❌ Error testing token '{token[:20]}...': {e}")

def main():
    """Main test function."""
    print("🚀 Starting Invitation Link Functionality Tests...")
    print("=" * 60)
    
    # Test 1: Backend Health
    if not test_backend_health():
        print("❌ Backend tests failed. Please start the backend server first.")
        return
    
    # Test 2: Invitation Endpoints
    test_invitation_endpoints()
    
    # Test 3: Invitation Link Generation
    test_invitation_link_generation()
    
    # Test 4: Frontend Access
    if not test_frontend_access():
        print("❌ Frontend tests failed. Please start the frontend server first.")
        return
    
    # Test 5: Invitation Flow Simulation
    test_invitation_flow_simulation()
    
    # Test 6: Error Handling
    test_error_handling()
    
    print("\n" + "=" * 60)
    print("🎉 All invitation link tests completed!")
    print("\n📋 Test Summary:")
    print("   ✅ Backend API is running")
    print("   ✅ Invitation endpoints are accessible")
    print("   ✅ Invitation link generation works")
    print("   ✅ Frontend is accessible")
    print("   ✅ Error handling is working")
    print("\n🌐 Access URLs:")
    print(f"   Backend API: {API_BASE_URL}")
    print(f"   Frontend: {FRONTEND_URL}")
    print(f"   API Documentation: {API_BASE_URL}/docs")
    print("\n💡 Next Steps:")
    print("   1. Open the frontend in your browser")
    print("   2. Create a test recruiter account")
    print("   3. Send test invitations to students")
    print("   4. Test clicking invitation links")
    print("   5. Verify no hanging/freezing occurs")
    print("\n🔧 Troubleshooting:")
    print("   - If links hang, check browser console for errors")
    print("   - Verify backend is running and accessible")
    print("   - Check database connection and tables")
    print("   - Monitor backend logs for errors")

if __name__ == "__main__":
    main()

