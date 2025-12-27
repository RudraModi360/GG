#!/usr/bin/env python
"""
Simple test to register a new user.
"""
import httpx

BASE_URL = "http://localhost:8000"
API_URL = f"{BASE_URL}/api/v1"

# User to register
TEST_USER = {
    "email": "rudramodi9560@gmail.com",
    "password": "Rudra@123456",  # Must be 8+ chars with uppercase, lowercase, digit, special char
    "first_name": "Rudra",
    "last_name": "Modi",
    "phone": "+919712193880",
    "organization_name": "Rudra's Organization"
}

def main():
    print("="*60)
    print("  Register New User")
    print("="*60)
    print(f"\n  Email: {TEST_USER['email']}")
    print(f"  Name: {TEST_USER['first_name']} {TEST_USER['last_name']}")
    
    with httpx.Client(timeout=30.0) as client:
        # Register
        print("\n  Sending registration request...")
        r = client.post(f"{API_URL}/auth/register", json=TEST_USER)
        
        print(f"\n  Status: {r.status_code}")
        print(f"  Response: {r.json()}")
        
        if r.status_code == 201:
            data = r.json()
            print("\n  ✅ Registration successful!")
            print(f"  Access Token: {data.get('access_token', 'N/A')[:50]}...")
        else:
            print("\n  ❌ Registration failed!")
            
            # Try login instead (user may already exist)
            print("\n  Trying to login instead...")
            r = client.post(f"{API_URL}/auth/login", json={
                "email": TEST_USER["email"],
                "password": TEST_USER["password"]
            })
            print(f"  Login Status: {r.status_code}")
            print(f"  Login Response: {r.json()}")
            
            if r.status_code == 200:
                print("\n  ✅ Login successful! User already exists.")

if __name__ == "__main__":
    main()
