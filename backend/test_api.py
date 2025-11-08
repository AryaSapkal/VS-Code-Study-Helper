#!/usr/bin/env python3
"""
Quick API test script for the Study Helper Backend
"""
import requests
import json

def test_ml_api():
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Study Helper Backend API...")
    
    # Test 1: Root endpoint
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            print("✅ Root endpoint working")
            data = response.json()
            print(f"   ML Available: {data.get('ml_available', 'Unknown')}")
        else:
            print(f"❌ Root endpoint failed: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Server not running on localhost:8000")
        return
    
    # Test 2: ML Prediction endpoint
    test_signals = {
        "signals": {
            "idle_time_total": 45.2,
            "edit_events": 23,
            "error_events": 5,
            "edit_velocity": 3.1,
            "backspace_ratio": 0.3,
            "cursor_moves": 15,
            "cursor_distance": 200,
            "time_since_last_run": 30
        }
    }
    
    try:
        response = requests.post(
            f"{base_url}/predict-stuck",
            json=test_signals,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            result = response.json()
            print("✅ ML Prediction endpoint working")
            print(f"   Is Stuck: {result.get('is_stuck')}")
            print(f"   Confidence: {result.get('confidence')}")
            print(f"   Model Available: {result.get('model_available')}")
        else:
            print(f"❌ ML Prediction failed: {response.status_code}")
            print(f"   Response: {response.text}")
    except Exception as e:
        print(f"❌ ML Prediction error: {e}")
    
    print("🎉 API testing complete!")

if __name__ == "__main__":
    test_ml_api()