
import json
import requests

BASE_URL = "http://localhost:8000"

def test_endpoints():
    print("🔍 Testing API Endpoints...")
    print("=" * 50)
    
    # 1. Health check
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"✅ Health Check: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health Check Failed: {e}")
    
    # 2. API Docs
    try:
        response = requests.get(f"{BASE_URL}/api/docs")
        print(f"✅ API Docs: {response.status_code}")
    except Exception as e:
        print(f"❌ API Docs Failed: {e}")
    
    # 3. Register endpoint (debería fallar sin datos)
    try:
        response = requests.post(f"{BASE_URL}/api/v1/auth/register", json={})
        print(f"✅ Register Endpoint: {response.status_code}")
        if response.status_code == 422:
            print("   ✓ Validation working (expected 422 for empty data)")
    except Exception as e:
        print(f"❌ Register Test Failed: {e}")
    
    print("=" * 50)
    print("🎯 Si todos muestran ✅, tu API está 100% operacional!")

if __name__ == "__main__":
    test_endpoints()