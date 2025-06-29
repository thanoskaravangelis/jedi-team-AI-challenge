#!/usr/bin/env python3
"""Example client for testing the Jedi Agent API."""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8000"


def test_health_check():
    """Test the health check endpoint."""
    print("Testing health check...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_query(query_text="What percentage of Gen Z uses social media?"):
    """Test a simple query."""
    print(f"\nTesting query: '{query_text}'")
    
    payload = {
        "query": query_text,
        "user_id": "test_user",
    }
    
    try:
        response = requests.post(f"{BASE_URL}/query", json=payload)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {result.get('response', 'No response')[:200]}...")
            print(f"Conversation ID: {result.get('conversation_id')}")
            return True, result.get('conversation_id')
        else:
            print(f"Error: {response.text}")
            return False, None
            
    except Exception as e:
        print(f"Error: {e}")
        return False, None


def test_streaming_query(query_text="Tell me about Gen Z social media preferences"):
    """Test streaming query endpoint."""
    print(f"\nTesting streaming query: '{query_text}'")
    
    payload = {
        "query": query_text,
        "user_id": "test_user",
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/query/stream",
            json=payload,
            headers={"Accept": "text/event-stream"},
            stream=True
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("Streaming response:")
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]  # Remove 'data: ' prefix
                        try:
                            event = json.loads(data)
                            event_type = event.get('type', 'unknown')
                            print(f"  [{event_type}]: {json.dumps(event, indent=2)}")
                        except json.JSONDecodeError:
                            print(f"  [raw]: {data}")
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_conversations(user_id="test_user"):
    """Test conversation listing."""
    print(f"\nTesting conversations for user: {user_id}")
    
    try:
        response = requests.get(f"{BASE_URL}/conversations/{user_id}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            conversations = response.json()
            print(f"Found {len(conversations)} conversations:")
            for conv in conversations:
                print(f"  - ID: {conv['id']}, Title: {conv.get('title', 'No title')}")
            return True, conversations
        else:
            print(f"Error: {response.text}")
            return False, []
            
    except Exception as e:
        print(f"Error: {e}")
        return False, []


def test_feedback(message_id, feedback_type="thumbs_up"):
    """Test feedback submission."""
    print(f"\nTesting feedback submission for message {message_id}")
    
    payload = {
        "message_id": message_id,
        "feedback_type": feedback_type,
        "comment": "Test feedback from API client"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/feedback", json=payload)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            print("Feedback submitted successfully")
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_analytics():
    """Test analytics endpoint."""
    print("\nTesting analytics...")
    
    try:
        response = requests.get(f"{BASE_URL}/analytics/tools")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            analytics = response.json()
            print("Analytics data:")
            print(json.dumps(analytics, indent=2))
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False


def interactive_test():
    """Interactive testing mode."""
    print("\n🤖 Interactive Jedi Agent Testing")
    print("=" * 40)
    
    while True:
        print("\nAvailable commands:")
        print("1. Test health check")
        print("2. Send query")
        print("3. Send streaming query")
        print("4. List conversations")
        print("5. Test analytics")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            test_health_check()
        
        elif choice == "2":
            query = input("Enter your query: ").strip()
            if query:
                success, conv_id = test_query(query)
                if success and conv_id:
                    # Ask if user wants to submit feedback
                    feedback = input("Submit feedback? (y/n): ").strip().lower()
                    if feedback == "y":
                        # Note: We'd need the message ID from the response
                        print("Feedback feature requires message ID from previous response")
        
        elif choice == "3":
            query = input("Enter your streaming query: ").strip()
            if query:
                test_streaming_query(query)
        
        elif choice == "4":
            user_id = input("Enter user ID (default: test_user): ").strip() or "test_user"
            test_conversations(user_id)
        
        elif choice == "5":
            test_analytics()
        
        elif choice == "6":
            print("Goodbye! 👋")
            break
        
        else:
            print("Invalid choice. Please try again.")


def run_full_test_suite():
    """Run a complete test suite."""
    print("🧪 Running Full Jedi Agent API Test Suite")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Health Check
    total_tests += 1
    if test_health_check():
        tests_passed += 1
    
    # Test 2: Simple Query
    total_tests += 1
    success, conv_id = test_query()
    if success:
        tests_passed += 1
    
    # Test 3: Conversations
    total_tests += 1
    if test_conversations()[0]:
        tests_passed += 1
    
    # Test 4: Analytics
    total_tests += 1
    if test_analytics():
        tests_passed += 1
    
    # Test 5: Streaming (optional, might be slow)
    print("\nSkipping streaming test (run manually if needed)")
    
    print("\n" + "=" * 50)
    print(f"Tests completed: {tests_passed}/{total_tests} passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! API is working correctly.")
    else:
        print("❌ Some tests failed. Check the API server and configuration.")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        interactive_test()
    else:
        run_full_test_suite()
        print("\nTo run interactive tests, use: python api_client.py interactive")
