#!/usr/bin/env python3
"""
Quick Test Script for Daraja MCP Server
Run this for a fast check of your setup
"""

import os
import sys
import requests
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_auth():
    """Quick authentication test"""
    print("🔐 Testing Daraja Authentication...")

    consumer_key = os.getenv("DARAJA_CONSUMER_KEY")
    consumer_secret = os.getenv("DARAJA_CONSUMER_SECRET")
    env = os.getenv("DARAJA_ENV", "sandbox")

    if not consumer_key or not consumer_secret:
        print("❌ Missing credentials in environment variables")
        return False

    base_url = "https://sandbox.safaricom.co.ke" if env == "sandbox" else "https://api.safaricom.co.ke"

    auth_string = f"{consumer_key}:{consumer_secret}"
    encoded_auth = base64.b64encode(auth_string.encode()).decode()

    try:
        response = requests.get(
            f"{base_url}/oauth/v1/generate?grant_type=client_credentials",
            headers={"Authorization": f"Basic {encoded_auth}"},
            timeout=10
        )

        if response.status_code == 200:
            print(f"✅ Authentication successful! ({env} environment)")
            return True
        else:
            print(f"❌ Authentication failed: {response.status_code}")
            print(f"   {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_callback_server():
    """Quick callback server test"""
    print("\n🌐 Testing Callback Server...")

    port = os.getenv("CALLBACK_PORT", "3000")

    try:
        response = requests.get(f"http://localhost:{port}/health", timeout=3)

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Callback server is running!")
            print(f"   Status: {data.get('status')}")
            print(f"   Callback URL: {data.get('callback_url')}")
            print(f"   Unread payments: {data.get('unread_payments')}")
            return True
        else:
            print(f"❌ Server returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to callback server")
        print("   Make sure server.py is running")
        return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def test_mock_callback():
    """Test callback with mock data"""
    print("\n📨 Testing Callback Endpoint...")

    port = os.getenv("CALLBACK_PORT", "3000")

    mock_data = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "quick-test-123",
                "CheckoutRequestID": "ws_CO_QUICKTEST",
                "ResultCode": 0,
                "ResultDesc": "Test successful",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 50},
                        {"Name": "MpesaReceiptNumber", "Value": "QUICKTEST123"},
                        {"Name": "TransactionDate", "Value": 20240108120000},
                        {"Name": "PhoneNumber", "Value": 254700000000}
                    ]
                }
            }
        }
    }

    try:
        response = requests.post(
            f"http://localhost:{port}/mpesa/callback",
            json=mock_data,
            timeout=5
        )

        if response.status_code == 200:
            print("✅ Callback endpoint working!")

            # Check if stored
            health = requests.get(f"http://localhost:{port}/health").json()
            if health.get("unread_payments", 0) > 0:
                print("✅ Payment notification stored!")

            return True
        else:
            print(f"❌ Callback failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False


def main():
    print("=" * 50)
    print("  DARAJA MCP - QUICK TEST")
    print("=" * 50)

    results = {
        "auth": test_auth(),
        "callback": test_callback_server(),
        "endpoint": test_mock_callback()
    }

    print("\n" + "=" * 50)
    print("  RESULTS")
    print("=" * 50)

    passed = sum(results.values())
    total = len(results)

    print(f"\nTests passed: {passed}/{total}")

    if all(results.values()):
        print("\n🎉 All tests passed! Your setup is working correctly.")
        print("\nNext steps:")
        print("1. Start ngrok: ngrok http 3000")
        print("2. Update PUBLIC_URL with ngrok HTTPS URL")
        print("3. Add MCP server to Claude Desktop config")
        print("4. Test with real STK push through Claude")
    else:
        print("\n⚠️  Some tests failed. Review the errors above.")

        if not results["auth"]:
            print("\n→ Fix authentication: Check your Daraja credentials")
        if not results["callback"]:
            print("\n→ Fix callback server: Make sure server.py is running")
            print("   Start with: python server.py")


if __name__ == "__main__":
    main()