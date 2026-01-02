import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000"

def test_backend():
    print("1. Checking Health...")
    try:
        r = requests.get(f"{BASE_URL}/health")
        print(f"   Status: {r.status_code}, Body: {r.json()}")
    except Exception as e:
        print(f"   Failed to connect: {e}")
        return

    print("\n2. Triggering Analysis (Capture)...")
    try:
        # analyze=true triggers the background task
        r = requests.get(f"{BASE_URL}/capture?analyze=true")
        print(f"   Status: {r.status_code}")
        # We don't print the whole body since it has a huge base64 image
        data = r.json()
        print(f"   Window: {data.get('window')}")
    except Exception as e:
        print(f"   Failed: {e}")

    print("\n3. Waiting for Analysis (5s)...")
    time.sleep(5)

    print("\n4. Checking Updates (Reaction)...")
    try:
        r = requests.get(f"{BASE_URL}/updates")
        print(f"   Response: {r.json()}")
    except Exception as e:
        print(f"   Failed: {e}")

    print("\n5. Testing Chat...")
    try:
        payload = {"message": "Hello Thea, what do you see?"}
        r = requests.post(f"{BASE_URL}/chat", json=payload)
        print(f"   Response: {r.json()}")
    except Exception as e:
        print(f"   Failed: {e}")

if __name__ == "__main__":
    test_backend()
