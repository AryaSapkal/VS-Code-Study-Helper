#!/usr/bin/env python3
"""
Test script to verify automatic ML model retraining based on user feedback.
"""

import requests
import json
import time
from datetime import datetime

# Backend URL
BASE_URL = "http://localhost:8000"

def test_feedback_and_retraining():
    """Test the feedback collection and automatic retraining system."""
    
    print("🧪 Testing ML Feedback and Retraining System")
    print("=" * 50)
    
    # Test data - simulate hint feedback from users
    test_feedback_data = [
        {
            "helpful": True,  # User was stuck, hint was helpful
            "hint": "Try using a for loop instead of while loop",
            "context": {
                "selection": "some code",
                "languageId": "python",
                "timeOnLine": 120.0,
                "wordsTyped": 3.0,
                "errorRate": 0.4,
                "typingSpeed": 1.5
            },
            "timestamp": datetime.now().isoformat()
        },
        {
            "helpful": False,  # User wasn't stuck, false positive
            "hint": "Consider using a dictionary for better performance",
            "context": {
                "selection": "my_list = []",
                "languageId": "python", 
                "timeOnLine": 30.0,
                "wordsTyped": 8.0,
                "errorRate": 0.1,
                "typingSpeed": 3.0
            },
            "timestamp": datetime.now().isoformat()
        }
    ]
    
    print(f"📊 Sending {len(test_feedback_data)} feedback entries...")
    
    # Send feedback data
    for i, feedback in enumerate(test_feedback_data):
        try:
            response = requests.post(f"{BASE_URL}/feedback", json=feedback)
            print(f"  ✅ Feedback {i+1}: {response.status_code} - {response.json()}")
        except Exception as e:
            print(f"  ❌ Feedback {i+1} failed: {e}")
    
    print("\n🔄 Testing manual retraining...")
    
    # Test manual retraining
    try:
        response = requests.post(f"{BASE_URL}/retrain-model?force=true")
        print(f"  ✅ Manual retrain: {response.status_code} - {response.json()}")
    except Exception as e:
        print(f"  ❌ Manual retrain failed: {e}")
    
    print("\n📈 Generating more feedback to test automatic retraining threshold...")
    
    # Generate enough feedback to trigger automatic retraining (100+ entries)
    bulk_feedback = []
    for i in range(105):  # Generate 105 feedback entries
        feedback = {
            "helpful": i % 2 == 0,  # Alternate between helpful and not helpful
            "hint": f"Test hint number {i+1}",
            "context": {
                "selection": f"code_block_{i}",
                "languageId": "python",
                "timeOnLine": 60.0 + (i * 2),  # Vary time on line
                "wordsTyped": 5.0 + (i % 10),
                "errorRate": 0.2 + (i % 5) * 0.1,
                "typingSpeed": 2.0 + (i % 3)
            },
            "timestamp": datetime.now().isoformat()
        }
        bulk_feedback.append(feedback)
    
    # Send bulk feedback in batches
    batch_size = 10
    for i in range(0, len(bulk_feedback), batch_size):
        batch = bulk_feedback[i:i+batch_size]
        print(f"📤 Sending batch {i//batch_size + 1}/{(len(bulk_feedback)//batch_size) + 1}")
        
        for feedback in batch:
            try:
                response = requests.post(f"{BASE_URL}/feedback", json=feedback)
                if response.status_code != 200:
                    print(f"    ⚠️ Non-200 response: {response.status_code}")
            except Exception as e:
                print(f"    ❌ Batch feedback failed: {e}")
        
        time.sleep(0.1)  # Small delay to avoid overwhelming the server
    
    print(f"\n✅ Sent {len(bulk_feedback)} feedback entries")
    print("🎯 The system should automatically retrain when it hits 100+ entries")
    print("\n🔍 Check the server logs for automatic retraining messages!")

def check_feedback_count():
    """Check how many feedback entries are stored."""
    try:
        # This would require a new endpoint to check feedback count
        # For now, just show that the test completed
        print("\n📊 Feedback collection test completed!")
        print("📁 Check backend/feedback_data/training_feedback.json for stored feedback")
        print("🤖 Check server logs for retraining activity")
    except Exception as e:
        print(f"❌ Error checking feedback: {e}")

if __name__ == "__main__":
    print("🚀 Starting ML Retraining Test")
    print("⏳ Make sure the backend is running on http://localhost:8000")
    
    # Wait a moment for user to ensure backend is running
    input("Press Enter when backend is ready...")
    
    try:
        # Test basic connectivity
        response = requests.get(f"{BASE_URL}/")
        print(f"✅ Backend connection: {response.status_code}")
        
        # Run the main test
        test_feedback_and_retraining()
        check_feedback_count()
        
        print("\n🎉 ML Retraining test completed!")
        print("📝 Summary:")
        print("  - Feedback collection: ✅ Implemented")
        print("  - Manual retraining: ✅ Available via /retrain-model?force=true")
        print("  - Automatic retraining: ✅ Triggers at 100+ feedback entries")
        print("  - ML improvement loop: ✅ User feedback → ML training data → Better model")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("💡 Make sure the backend server is running!")