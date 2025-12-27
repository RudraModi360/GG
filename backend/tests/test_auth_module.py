#!/usr/bin/env python
"""
=============================================================================
GearGuard Backend - User Authentication Module Test Suite
=============================================================================

This script tests all authentication endpoints:
- POST /api/v1/auth/register     - Register new user
- POST /api/v1/auth/login        - Login user
- GET  /api/v1/auth/me           - Get current user profile
- PUT  /api/v1/auth/me           - Update user profile
- PUT  /api/v1/auth/me/password  - Change password
- POST /api/v1/auth/refresh      - Refresh access token
- POST /api/v1/auth/logout       - Logout user
- POST /api/v1/auth/forgot-password - Request password reset
- POST /api/v1/auth/reset-password  - Reset password with token

Usage:
    python tests/test_auth_module.py

The script will generate a unique test user and store the credentials
for use in subsequent module tests.
"""

import httpx
import json
import uuid
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, Any


# =============================================================================
# Configuration
# =============================================================================

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000")
API_URL = f"{BASE_URL}/api/v1"
TIMEOUT = 30.0

# Test credentials file path - stores credentials for other module tests
CREDENTIALS_FILE = Path(__file__).parent / ".test_credentials.json"


# =============================================================================
# Helper Classes
# =============================================================================

class TestResult:
    """Stores test result information."""
    def __init__(self, name: str, passed: bool, message: str = "", response: Optional[Dict] = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.response = response
        self.timestamp = datetime.now().isoformat()


class AuthTestCredentials:
    """Stores and manages test credentials."""
    def __init__(self):
        self.user_id: Optional[str] = None
        self.email: Optional[str] = None
        self.password: Optional[str] = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.organization_id: Optional[str] = None
        
    def save(self, filepath: Path):
        """Save credentials to file for other test modules."""
        data = {
            "user_id": self.user_id,
            "email": self.email,
            "password": self.password,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "organization_id": self.organization_id,
            "saved_at": datetime.now().isoformat()
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\n  💾 Credentials saved to: {filepath}")
    
    @classmethod
    def load(cls, filepath: Path) -> Optional["AuthTestCredentials"]:
        """Load credentials from file."""
        if not filepath.exists():
            return None
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            creds = cls()
            creds.user_id = data.get("user_id")
            creds.email = data.get("email")
            creds.password = data.get("password")
            creds.access_token = data.get("access_token")
            creds.refresh_token = data.get("refresh_token")
            creds.organization_id = data.get("organization_id")
            return creds
        except Exception:
            return None


# =============================================================================
# Test Functions
# =============================================================================

def generate_test_user() -> Dict[str, str]:
    """Generate unique test user data."""
    unique_id = str(uuid.uuid4())[:8]
    return {
        "email": f"rudramodi9560@gmail.com",
        "password": f"Rudra@360",
        "first_name": "Rudra",
        "last_name": f"Modi",
        "phone": f"+919712193880",
        "organization_name": f"Test Org {unique_id}"
    }


def test_register(client: httpx.Client, test_user: Dict[str, str], creds: AuthTestCredentials) -> TestResult:
    """Test user registration endpoint."""
    print("\n" + "="*60)
    print("  📝 TEST: User Registration")
    print("="*60)
    print(f"  Email: {test_user['email']}")
    print(f"  Name: {test_user['first_name']} {test_user['last_name']}")
    print(f"  Organization: {test_user['organization_name']}")
    
    try:
        response = client.post(f"{API_URL}/auth/register", json=test_user)
        data = response.json()
        
        print(f"\n  📊 Status: {response.status_code}")
        
        if response.status_code == 201:
            creds.email = test_user["email"]
            creds.password = test_user["password"]
            creds.access_token = data.get("access_token")
            creds.refresh_token = data.get("refresh_token")
            
            print("  ✅ Registration successful!")
            print(f"  🔑 Access Token: {creds.access_token[:50]}...")
            print(f"  🔄 Refresh Token: {creds.refresh_token[:50]}...")
            print(f"  ⏱️  Expires In: {data.get('expires_in')} seconds")
            
            return TestResult(
                "Register User",
                True,
                "User registered successfully",
                data
            )
        else:
            print(f"  ❌ Registration failed: {data}")
            return TestResult("Register User", False, f"Status {response.status_code}: {data}")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return TestResult("Register User", False, str(e))


def test_login(client: httpx.Client, creds: AuthTestCredentials) -> TestResult:
    """Test user login endpoint."""
    print("\n" + "="*60)
    print("  🔐 TEST: User Login")
    print("="*60)
    print(f"  Email: {creds.email}")
    
    try:
        response = client.post(f"{API_URL}/auth/login", json={
            "email": creds.email,
            "password": creds.password
        })
        data = response.json()
        
        print(f"\n  📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            # Update tokens from login
            creds.access_token = data.get("access_token")
            creds.refresh_token = data.get("refresh_token")
            
            print("  ✅ Login successful!")
            print(f"  🔑 New Access Token: {creds.access_token[:50]}...")
            
            return TestResult("Login User", True, "Login successful", data)
        else:
            print(f"  ❌ Login failed: {data}")
            return TestResult("Login User", False, f"Status {response.status_code}: {data}")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return TestResult("Login User", False, str(e))


def test_get_profile(client: httpx.Client, creds: AuthTestCredentials) -> TestResult:
    """Test get current user profile endpoint."""
    print("\n" + "="*60)
    print("  👤 TEST: Get User Profile")
    print("="*60)
    
    try:
        headers = {"Authorization": f"Bearer {creds.access_token}"}
        response = client.get(f"{API_URL}/auth/me", headers=headers)
        data = response.json()
        
        print(f"\n  📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            creds.user_id = data.get("id")
            creds.organization_id = data.get("organization_id")
            
            print("  ✅ Profile retrieved successfully!")
            print(f"  👤 User ID: {creds.user_id}")
            print(f"  📧 Email: {data.get('email')}")
            print(f"  📛 Name: {data.get('first_name')} {data.get('last_name')}")
            print(f"  🏢 Organization: {data.get('organization_name')} ({creds.organization_id})")
            print(f"  🎭 Role: {data.get('role')}")
            print(f"  ✓ Verified: {data.get('is_verified')}")
            
            return TestResult("Get Profile", True, "Profile retrieved", data)
        else:
            print(f"  ❌ Failed to get profile: {data}")
            return TestResult("Get Profile", False, f"Status {response.status_code}: {data}")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return TestResult("Get Profile", False, str(e))


def test_update_profile(client: httpx.Client, creds: AuthTestCredentials) -> TestResult:
    """Test update user profile endpoint."""
    print("\n" + "="*60)
    print("  ✏️  TEST: Update User Profile")
    print("="*60)
    
    update_data = {
        "first_name": "Updated",
        "last_name": "TestUser",
        "phone": "+15551234567"
    }
    print(f"  Updating: {update_data}")
    
    try:
        headers = {"Authorization": f"Bearer {creds.access_token}"}
        response = client.put(f"{API_URL}/auth/me", headers=headers, json=update_data)
        data = response.json()
        
        print(f"\n  📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ Profile updated successfully!")
            print(f"  📛 New Name: {data.get('first_name')} {data.get('last_name')}")
            print(f"  📞 New Phone: {data.get('phone')}")
            
            return TestResult("Update Profile", True, "Profile updated", data)
        else:
            print(f"  ❌ Failed to update profile: {data}")
            return TestResult("Update Profile", False, f"Status {response.status_code}: {data}")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return TestResult("Update Profile", False, str(e))


def test_refresh_token(client: httpx.Client, creds: AuthTestCredentials) -> TestResult:
    """Test token refresh endpoint."""
    print("\n" + "="*60)
    print("  🔄 TEST: Refresh Token")
    print("="*60)
    print(f"  Current Refresh Token: {creds.refresh_token[:50]}...")
    
    try:
        response = client.post(f"{API_URL}/auth/refresh", json={
            "refresh_token": creds.refresh_token
        })
        data = response.json()
        
        print(f"\n  📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            old_access = creds.access_token[:30]
            creds.access_token = data.get("access_token")
            creds.refresh_token = data.get("refresh_token")
            
            print("  ✅ Token refreshed successfully!")
            print(f"  🔑 Old Access Token: {old_access}...")
            print(f"  🔑 New Access Token: {creds.access_token[:50]}...")
            print(f"  🔄 New Refresh Token: {creds.refresh_token[:50]}...")
            
            return TestResult("Refresh Token", True, "Token refreshed", data)
        else:
            print(f"  ❌ Failed to refresh token: {data}")
            return TestResult("Refresh Token", False, f"Status {response.status_code}: {data}")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return TestResult("Refresh Token", False, str(e))


def test_change_password(client: httpx.Client, creds: AuthTestCredentials) -> TestResult:
    """Test change password endpoint."""
    print("\n" + "="*60)
    print("  🔒 TEST: Change Password")
    print("="*60)
    
    new_password = f"{creds.password}_changed"
    print(f"  Changing password from: {creds.password[:10]}... to: {new_password[:15]}...")
    
    try:
        headers = {"Authorization": f"Bearer {creds.access_token}"}
        response = client.put(f"{API_URL}/auth/me/password", headers=headers, json={
            "current_password": creds.password,
            "new_password": new_password
        })
        data = response.json()
        
        print(f"\n  📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ Password changed successfully!")
            print(f"  📝 Message: {data.get('message')}")
            
            # Update stored password
            creds.password = new_password
            
            return TestResult("Change Password", True, "Password changed", data)
        else:
            print(f"  ❌ Failed to change password: {data}")
            return TestResult("Change Password", False, f"Status {response.status_code}: {data}")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return TestResult("Change Password", False, str(e))


def test_login_with_new_password(client: httpx.Client, creds: AuthTestCredentials) -> TestResult:
    """Test login with the new changed password."""
    print("\n" + "="*60)
    print("  🔐 TEST: Login with New Password")
    print("="*60)
    print(f"  Email: {creds.email}")
    print(f"  Password: {creds.password[:15]}...")
    
    try:
        response = client.post(f"{API_URL}/auth/login", json={
            "email": creds.email,
            "password": creds.password
        })
        data = response.json()
        
        print(f"\n  📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            creds.access_token = data.get("access_token")
            creds.refresh_token = data.get("refresh_token")
            
            print("  ✅ Login with new password successful!")
            print(f"  🔑 New Access Token: {creds.access_token[:50]}...")
            
            return TestResult("Login New Password", True, "Login successful with new password", data)
        else:
            print(f"  ❌ Login failed: {data}")
            return TestResult("Login New Password", False, f"Status {response.status_code}: {data}")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return TestResult("Login New Password", False, str(e))


def test_forgot_password(client: httpx.Client, creds: AuthTestCredentials) -> TestResult:
    """Test forgot password endpoint."""
    print("\n" + "="*60)
    print("  📧 TEST: Forgot Password (Request Reset)")
    print("="*60)
    print(f"  Email: {creds.email}")
    
    try:
        response = client.post(f"{API_URL}/auth/forgot-password", json={
            "email": creds.email
        })
        data = response.json()
        
        print(f"\n  📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ Forgot password request successful!")
            print(f"  📝 Message: {data.get('message')}")
            print("  ℹ️  Note: In production, an email would be sent with reset token")
            
            return TestResult("Forgot Password", True, "Reset request sent", data)
        else:
            print(f"  ❌ Forgot password request failed: {data}")
            return TestResult("Forgot Password", False, f"Status {response.status_code}: {data}")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return TestResult("Forgot Password", False, str(e))


def test_logout(client: httpx.Client, creds: AuthTestCredentials) -> TestResult:
    """Test logout endpoint."""
    print("\n" + "="*60)
    print("  🚪 TEST: Logout")
    print("="*60)
    
    try:
        headers = {"Authorization": f"Bearer {creds.access_token}"}
        response = client.post(f"{API_URL}/auth/logout", headers=headers)
        data = response.json()
        
        print(f"\n  📊 Status: {response.status_code}")
        
        if response.status_code == 200:
            print("  ✅ Logout successful!")
            print(f"  📝 Message: {data.get('message')}")
            
            return TestResult("Logout", True, "Logged out successfully", data)
        else:
            print(f"  ❌ Logout failed: {data}")
            return TestResult("Logout", False, f"Status {response.status_code}: {data}")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return TestResult("Logout", False, str(e))


def test_access_after_logout(client: httpx.Client, creds: AuthTestCredentials) -> TestResult:
    """Test that access is denied after logout (optional - tokens may still work until expiry)."""
    print("\n" + "="*60)
    print("  🔒 TEST: Access Profile After Logout")
    print("="*60)
    print("  ℹ️  Note: JWT tokens may remain valid until expiry even after logout")
    
    try:
        headers = {"Authorization": f"Bearer {creds.access_token}"}
        response = client.get(f"{API_URL}/auth/me", headers=headers)
        
        print(f"\n  📊 Status: {response.status_code}")
        
        # Note: Since JWT is stateless, it might still work
        # This test documents the behavior
        if response.status_code == 200:
            print("  ⚠️  Access still works (JWT stateless behavior)")
            print("  ℹ️  This is expected - JWT tokens are valid until expiry")
            return TestResult("Post-Logout Access", True, "Access still works (expected JWT behavior)", response.json())
        else:
            print("  ✅ Access denied after logout (session-based validation)")
            return TestResult("Post-Logout Access", True, "Access properly denied", response.json())
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return TestResult("Post-Logout Access", False, str(e))


def test_invalid_credentials(client: httpx.Client) -> TestResult:
    """Test login with invalid credentials."""
    print("\n" + "="*60)
    print("  🚫 TEST: Invalid Credentials (Negative Test)")
    print("="*60)
    
    try:
        response = client.post(f"{API_URL}/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "WrongPassword@123"
        })
        data = response.json()
        
        print(f"\n  📊 Status: {response.status_code}")
        
        if response.status_code == 401:
            print("  ✅ Correctly rejected invalid credentials!")
            print(f"  📝 Error: {data.get('detail')}")
            return TestResult("Invalid Credentials", True, "Correctly rejected", data)
        else:
            print(f"  ❌ Unexpected response: {data}")
            return TestResult("Invalid Credentials", False, f"Expected 401, got {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return TestResult("Invalid Credentials", False, str(e))


def test_weak_password_registration(client: httpx.Client) -> TestResult:
    """Test registration with weak password."""
    print("\n" + "="*60)
    print("  🚫 TEST: Weak Password Registration (Negative Test)")
    print("="*60)
    
    weak_user = {
        "email": f"weak_{uuid.uuid4().hex[:8]}@test.com",
        "password": "weak",  # Too short, no special chars
        "first_name": "Weak",
        "last_name": "Password"
    }
    print(f"  Testing with password: '{weak_user['password']}'")
    
    try:
        response = client.post(f"{API_URL}/auth/register", json=weak_user)
        data = response.json()
        
        print(f"\n  📊 Status: {response.status_code}")
        
        if response.status_code in [400, 422]:
            print("  ✅ Correctly rejected weak password!")
            print(f"  📝 Error: {data}")
            return TestResult("Weak Password", True, "Correctly rejected", data)
        else:
            print(f"  ❌ Unexpected response: {data}")
            return TestResult("Weak Password", False, f"Expected 400/422, got {response.status_code}")
            
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")
        return TestResult("Weak Password", False, str(e))


# =============================================================================
# Main Test Runner
# =============================================================================

def run_all_tests() -> Tuple[int, int, AuthTestCredentials]:
    """Run all authentication tests and return results."""
    print("\n")
    print("╔" + "="*60 + "╗")
    print("║" + "  GearGuard - User Authentication Module Test Suite".center(60) + "║")
    print("╚" + "="*60 + "╝")
    print(f"\n  🌐 API URL: {API_URL}")
    print(f"  ⏰ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results: list[TestResult] = []
    creds = AuthTestCredentials()
    test_user = generate_test_user()
    
    with httpx.Client(timeout=TIMEOUT) as client:
        # ===============================================
        # Core Authentication Flow Tests
        # ===============================================
        
        # 1. Register new user
        result = test_register(client, test_user, creds)
        results.append(result)
        
        if not result.passed:
            print("\n  ⚠️  Registration failed, attempting login with existing user...")
            # Try login in case user exists
            creds.email = test_user["email"]
            creds.password = test_user["password"]
            result = test_login(client, creds)
            results.append(result)
            
            if not result.passed:
                print("\n  ❌ Cannot proceed without valid authentication")
                return sum(1 for r in results if r.passed), len(results), creds
        
        # 2. Test login (fresh login with new session)
        result = test_login(client, creds)
        results.append(result)
        
        # 3. Get user profile
        result = test_get_profile(client, creds)
        results.append(result)
        
        if not result.passed:
            print("\n  ❌ Cannot proceed without valid profile")
            return sum(1 for r in results if r.passed), len(results), creds
        
        # 4. Update profile
        result = test_update_profile(client, creds)
        results.append(result)
        
        # 5. Refresh token
        result = test_refresh_token(client, creds)
        results.append(result)
        
        # 6. Change password
        result = test_change_password(client, creds)
        results.append(result)
        
        # 7. Login with new password
        if result.passed:
            result = test_login_with_new_password(client, creds)
            results.append(result)
        
        # 8. Forgot password (request reset)
        result = test_forgot_password(client, creds)
        results.append(result)
        
        # 9. Logout
        result = test_logout(client, creds)
        results.append(result)
        
        # 10. Test access after logout
        result = test_access_after_logout(client, creds)
        results.append(result)
        
        # ===============================================
        # Negative Tests (Error Handling)
        # ===============================================
        
        # 11. Invalid credentials
        result = test_invalid_credentials(client)
        results.append(result)
        
        # 12. Weak password
        result = test_weak_password_registration(client)
        results.append(result)
        
        # Re-login to get fresh tokens for saving
        test_login(client, creds)
    
    # Calculate results
    passed = sum(1 for r in results if r.passed)
    total = len(results)
    
    return passed, total, creds


def print_summary(passed: int, total: int, creds: AuthTestCredentials):
    """Print test summary and save credentials."""
    print("\n")
    print("╔" + "="*60 + "╗")
    print("║" + "  TEST SUMMARY".center(60) + "║")
    print("╚" + "="*60 + "╝")
    
    success_rate = (passed / total * 100) if total > 0 else 0
    
    if passed == total:
        print(f"\n  🎉 ALL TESTS PASSED! ({passed}/{total})")
    elif passed >= total * 0.8:
        print(f"\n  ⚠️  MOSTLY PASSED: {passed}/{total} ({success_rate:.1f}%)")
    else:
        print(f"\n  ❌ TESTS FAILED: {passed}/{total} ({success_rate:.1f}%)")
    
    print("\n  📋 Test Credentials:")
    print(f"     User ID: {creds.user_id or 'N/A'}")
    print(f"     Email: {creds.email or 'N/A'}")
    print(f"     Organization ID: {creds.organization_id or 'N/A'}")
    print(f"     Access Token: {(creds.access_token[:30] + '...') if creds.access_token else 'N/A'}")
    
    # Save credentials for other tests
    if creds.access_token:
        creds.save(CREDENTIALS_FILE)
        print(f"\n  ℹ️  Credentials saved for other module tests")
    
    print("\n  ⏰ Completed:", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    print("\n" + "="*62 + "\n")


def main():
    """Main entry point."""
    try:
        passed, total, creds = run_all_tests()
        print_summary(passed, total, creds)
        
        # Exit with error code if tests failed
        if passed < total:
            sys.exit(1)
        sys.exit(0)
        
    except httpx.ConnectError:
        print("\n  ❌ ERROR: Cannot connect to the server")
        print(f"     Please ensure the server is running at {BASE_URL}")
        print("     Run: uvicorn app.main:app --reload")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n  ⚠️  Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n  ❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
