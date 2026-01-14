"""
Daraja MCP Server - HTTP Version
Supports both stdio (local) and HTTP (remote) connections
"""

import os
import sys
import json
import base64
import requests
import asyncio
from datetime import datetime
from typing import Any, Optional
from threading import Thread
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment
load_dotenv()

# Import MCP components
from mcp.server import Server
from mcp.types import Tool, TextContent, Resource
from mcp.server.stdio import stdio_server


# Configuration
class DarajaConfig:
    def __init__(self):
        self.consumer_key = os.getenv("DARAJA_CONSUMER_KEY", "")
        self.consumer_secret = os.getenv("DARAJA_CONSUMER_SECRET", "")
        self.business_short_code = os.getenv("DARAJA_SHORTCODE", "")
        self.passkey = os.getenv("DARAJA_PASSKEY", "")
        self.environment = os.getenv("DARAJA_ENV", "sandbox")
        self.callback_port = int(os.getenv("CALLBACK_PORT", "3000"))
        self.mcp_port = int(os.getenv("MCP_PORT", "3000"))
        self.callback_host = os.getenv("CALLBACK_HOST", "0.0.0.0")
        self.public_url = os.getenv("PUBLIC_URL", f"http://localhost:{self.callback_port}")

        if self.environment == "production":
            self.base_url = "https://api.safaricom.co.ke"
        else:
            self.base_url = "https://sandbox.safaricom.co.ke"

    def get_auth_url(self):
        return f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"

    def get_stk_push_url(self):
        return f"{self.base_url}/mpesa/stkpush/v1/processrequest"

    def get_stk_query_url(self):
        return f"{self.base_url}/mpesa/stkpushquery/v1/query"

    def get_callback_url(self):
        return f"{self.public_url}/mpesa/callback"


# Payment Store
class PaymentStore:
    def __init__(self):
        self.payments = []
        self.max_payments = 100

    def add_payment(self, payment_data: dict):
        payment_data['received_at'] = datetime.now().isoformat()
        self.payments.insert(0, payment_data)
        if len(self.payments) > self.max_payments:
            self.payments = self.payments[:self.max_payments]

    def get_recent_payments(self, limit: int = 10):
        return self.payments[:limit]

    def get_payment_by_request_id(self, checkout_request_id: str):
        for payment in self.payments:
            if payment.get('CheckoutRequestID') == checkout_request_id:
                return payment
        return None


# Daraja API
class DarajaAPI:
    def __init__(self, config: DarajaConfig):
        self.config = config
        self.access_token = None
        self.token_expiry = None

    def get_access_token(self) -> str:
        if self.access_token and self.token_expiry:
            if datetime.now() < self.token_expiry:
                return self.access_token

        auth_string = f"{self.config.consumer_key}:{self.config.consumer_secret}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()

        headers = {"Authorization": f"Basic {encoded_auth}"}
        response = requests.get(self.config.get_auth_url(), headers=headers)

        if response.status_code == 200:
            data = response.json()
            self.access_token = data["access_token"]
            from datetime import timedelta
            self.token_expiry = datetime.now() + timedelta(seconds=3500)
            return self.access_token
        else:
            raise Exception(f"Failed to get access token: {response.text}")

    def generate_password(self, timestamp: str) -> str:
        password_string = f"{self.config.business_short_code}{self.config.passkey}{timestamp}"
        return base64.b64encode(password_string.encode()).decode()

    def stk_push(self, phone_number: str, amount: int, account_reference: str,
                 transaction_desc: str) -> dict:
        token = self.get_access_token()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = self.generate_password(timestamp)

        phone = phone_number.replace("+", "")
        if phone.startswith("0"):
            phone = "254" + phone[1:]

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        payload = {
            "BusinessShortCode": self.config.business_short_code,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",
            "Amount": amount,
            "PartyA": phone,
            "PartyB": self.config.business_short_code,
            "PhoneNumber": phone,
            "CallBackURL": self.config.get_callback_url(),
            "AccountReference": account_reference,
            "TransactionDesc": transaction_desc
        }

        response = requests.post(
            self.config.get_stk_push_url(),
            json=payload,
            headers=headers
        )

        return response.json()


# Initialize
config = DarajaConfig()
payment_store = PaymentStore()
daraja = DarajaAPI(config)

# Flask app for callbacks AND MCP HTTP endpoint
app = Flask(__name__)


@app.route('/mpesa/callback', methods=['POST'])
def mpesa_callback():
    try:
        data = request.json
        callback_data = data.get('Body', {}).get('stkCallback', {})

        result_code = callback_data.get('ResultCode')
        result_desc = callback_data.get('ResultDesc')
        merchant_request_id = callback_data.get('MerchantRequestID')
        checkout_request_id = callback_data.get('CheckoutRequestID')

        payment_info = {
            'MerchantRequestID': merchant_request_id,
            'CheckoutRequestID': checkout_request_id,
            'ResultCode': result_code,
            'ResultDesc': result_desc,
            'read': False
        }

        if result_code == 0:
            callback_metadata = callback_data.get('CallbackMetadata', {}).get('Item', [])
            for item in callback_metadata:
                name = item.get('Name')
                value = item.get('Value')
                if name == 'Amount':
                    payment_info['Amount'] = value
                elif name == 'MpesaReceiptNumber':
                    payment_info['MpesaReceiptNumber'] = value
                elif name == 'TransactionDate':
                    payment_info['TransactionDate'] = str(value)
                elif name == 'PhoneNumber':
                    payment_info['PhoneNumber'] = value

        payment_store.add_payment(payment_info)
        print(f"[CALLBACK] Payment received: {payment_info}")

        return jsonify({"ResultCode": 0, "ResultDesc": "Success"}), 200
    except Exception as e:
        print(f"[CALLBACK ERROR] {str(e)}")
        return jsonify({"ResultCode": 1, "ResultDesc": f"Error: {str(e)}"}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "callback_url": config.get_callback_url(),
        "unread_payments": len([p for p in payment_store.payments if not p.get('read', False)])
    }), 200


# MCP HTTP Endpoints
@app.route('/mcp/tools', methods=['GET'])
def list_tools():
    """List available MCP tools"""
    tools = [
        {
            "name": "stk_push",
            "description": "Initiate an STK Push payment request",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "phone_number": {"type": "string"},
                    "amount": {"type": "integer"},
                    "account_reference": {"type": "string"},
                    "transaction_desc": {"type": "string"}
                },
                "required": ["phone_number", "amount", "account_reference", "transaction_desc"]
            }
        },
        {
            "name": "get_recent_payments",
            "description": "Get recent payment notifications",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 10}
                }
            }
        }
    ]
    return jsonify({"tools": tools}), 200


@app.route('/mcp/call_tool', methods=['POST'])
def call_tool():
    """Execute an MCP tool"""
    data = request.json
    tool_name = data.get('name')
    arguments = data.get('arguments', {})

    try:
        if tool_name == "stk_push":
            result = daraja.stk_push(
                phone_number=arguments["phone_number"],
                amount=arguments["amount"],
                account_reference=arguments["account_reference"],
                transaction_desc=arguments["transaction_desc"]
            )
            return jsonify({"result": json.dumps(result, indent=2)}), 200

        elif tool_name == "get_recent_payments":
            limit = arguments.get("limit", 10)
            payments = payment_store.get_recent_payments(limit)
            return jsonify({"result": payments}), 200

        else:
            return jsonify({"error": f"Unknown tool: {tool_name}"}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "service": "Daraja MCP Server",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "mpesa_callback": "/mpesa/callback",
            "mcp_tools": "/mcp/tools",
            "mcp_call": "/mcp/call_tool"
        }
    }), 200


if __name__ == "__main__":
    print(f"🚀 Daraja MCP Server (HTTP Mode)")
    print(f"📡 Listening on port {config.callback_port}")
    print(f"🌐 Public URL: {config.public_url}")
    print(f"🔧 Environment: {config.environment}")

    app.run(
        host=config.callback_host,
        port=config.callback_port,
        debug=False
    )