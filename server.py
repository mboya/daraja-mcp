"""
Safaricom Daraja MCP Server with Callback Handler
Provides M-PESA integration tools for Claude with real-time notifications
"""

import os
import sys
import json
import base64
import requests
from datetime import datetime
from typing import Any
import asyncio
from threading import Thread
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Load environment variables from .env before any config is read
load_dotenv()

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
        self.callback_host = os.getenv("CALLBACK_HOST", "localhost")
        self.public_url = os.getenv("PUBLIC_URL", f"http://localhost:{self.callback_port}")
        
        # URLs based on environment
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
    
    def get_b2c_url(self):
        return f"{self.base_url}/mpesa/b2c/v1/paymentrequest"
    
    def get_callback_url(self):
        return f"{self.public_url}/mpesa/callback"
    
    def get_timeout_url(self):
        return f"{self.public_url}/mpesa/timeout"

# Payment notifications store
class PaymentStore:
    def __init__(self):
        self.payments = []
        self.max_payments = 100  # Keep last 100 payments
    
    def add_payment(self, payment_data: dict):
        """Add a new payment notification"""
        payment_data['received_at'] = datetime.now().isoformat()
        self.payments.insert(0, payment_data)
        
        # Keep only recent payments
        if len(self.payments) > self.max_payments:
            self.payments = self.payments[:self.max_payments]
    
    def get_recent_payments(self, limit: int = 10):
        """Get recent payments"""
        return self.payments[:limit]
    
    def get_payment_by_request_id(self, checkout_request_id: str):
        """Find payment by CheckoutRequestID"""
        for payment in self.payments:
            if payment.get('CheckoutRequestID') == checkout_request_id:
                return payment
        return None
    
    def get_payment_by_transaction_id(self, mpesa_receipt: str):
        """Find payment by M-PESA receipt number"""
        for payment in self.payments:
            if payment.get('MpesaReceiptNumber') == mpesa_receipt:
                return payment
        return None
    
    def get_unread_count(self):
        """Count unread notifications"""
        return sum(1 for p in self.payments if not p.get('read', False))
    
    def mark_as_read(self, checkout_request_id: str):
        """Mark a payment notification as read"""
        for payment in self.payments:
            if payment.get('CheckoutRequestID') == checkout_request_id:
                payment['read'] = True
                return True
        return False

class DarajaAPI:
    def __init__(self, config: DarajaConfig):
        self.config = config
        self.access_token = None
        self.token_expiry = None
    
    def get_access_token(self) -> str:
        """Generate OAuth access token"""
        if self.access_token and self.token_expiry:
            if datetime.now() < self.token_expiry:
                return self.access_token
        
        auth_string = f"{self.config.consumer_key}:{self.config.consumer_secret}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_auth}"
        }
        
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
        """Generate password for STK Push"""
        password_string = f"{self.config.business_short_code}{self.config.passkey}{timestamp}"
        return base64.b64encode(password_string.encode()).decode()
    
    def stk_push(self, phone_number: str, amount: int, account_reference: str, 
                 transaction_desc: str) -> dict:
        """Initiate STK Push payment request"""
        token = self.get_access_token()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = self.generate_password(timestamp)
        
        # Format phone number
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
    
    def stk_query(self, checkout_request_id: str) -> dict:
        """Query STK Push transaction status"""
        token = self.get_access_token()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        password = self.generate_password(timestamp)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "BusinessShortCode": self.config.business_short_code,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id
        }
        
        response = requests.post(
            self.config.get_stk_query_url(),
            json=payload,
            headers=headers
        )
        
        return response.json()

# Flask app for callbacks
def create_callback_app(payment_store: PaymentStore):
    app = Flask(__name__)
    
    @app.route('/mpesa/callback', methods=['POST'])
    def mpesa_callback():
        """Handle M-PESA STK Push callback"""
        try:
            data = request.json
            
            # Extract callback data
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
            
            # If successful, extract payment details
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
            
            # Store the payment notification
            payment_store.add_payment(payment_info)
            
            print(f"[CALLBACK] Payment received: {payment_info}")
            
            return jsonify({
                "ResultCode": 0,
                "ResultDesc": "Success"
            }), 200
            
        except Exception as e:
            print(f"[CALLBACK ERROR] {str(e)}")
            return jsonify({
                "ResultCode": 1,
                "ResultDesc": f"Error: {str(e)}"
            }), 500
    
    @app.route('/mpesa/timeout', methods=['POST'])
    def mpesa_timeout():
        """Handle timeout callback"""
        try:
            data = request.json
            print(f"[TIMEOUT] {json.dumps(data, indent=2)}")
            
            return jsonify({
                "ResultCode": 0,
                "ResultDesc": "Success"
            }), 200
        except Exception as e:
            print(f"[TIMEOUT ERROR] {str(e)}")
            return jsonify({
                "ResultCode": 1,
                "ResultDesc": f"Error: {str(e)}"
            }), 500
    
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        return jsonify({
            "status": "healthy",
            "callback_url": config.get_callback_url(),
            "unread_payments": payment_store.get_unread_count()
        }), 200

    @app.route('/favicon.ico', methods=['GET'])
    def favicon():
        """Avoid 404 when browsers request favicon"""
        return "", 204

    return app

# Initialize components
config = DarajaConfig()
payment_store = PaymentStore()
daraja = DarajaAPI(config)
callback_app = create_callback_app(payment_store)

# Start Flask server in background thread
def run_flask():
    callback_app.run(
        host=config.callback_host,
        port=config.callback_port,
        debug=False,
        use_reloader=False
    )

flask_thread = Thread(target=run_flask, daemon=True)
flask_thread.start()

# Initialize MCP Server
app = Server("daraja-mcp")

@app.list_resources()
async def list_resources() -> list[Resource]:
    """List available resources"""
    return [
        Resource(
            uri="payment://recent",
            name="Recent Payments",
            mimeType="application/json",
            description="Recent M-PESA payment notifications"
        ),
        Resource(
            uri="payment://unread",
            name="Unread Notifications",
            mimeType="application/json",
            description="Unread payment notifications"
        )
    ]

@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content"""
    if uri == "payment://recent":
        payments = payment_store.get_recent_payments(20)
        return json.dumps({
            "total": len(payments),
            "unread": payment_store.get_unread_count(),
            "payments": payments
        }, indent=2)
    
    elif uri == "payment://unread":
        all_payments = payment_store.get_recent_payments(100)
        unread = [p for p in all_payments if not p.get('read', False)]
        return json.dumps({
            "total": len(unread),
            "payments": unread
        }, indent=2)
    
    else:
        return json.dumps({"error": "Unknown resource"})

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Daraja API tools"""
    return [
        Tool(
            name="stk_push",
            description="Initiate an STK Push (Lipa Na M-PESA) payment request. Callback notifications will be received automatically.",
            inputSchema={
                "type": "object",
                "properties": {
                    "phone_number": {
                        "type": "string",
                        "description": "Customer phone number in format 254XXXXXXXXX or 07XXXXXXXX"
                    },
                    "amount": {
                        "type": "integer",
                        "description": "Amount to charge in KES (must be at least 1)"
                    },
                    "account_reference": {
                        "type": "string",
                        "description": "Account reference (e.g., invoice number, order ID)"
                    },
                    "transaction_desc": {
                        "type": "string",
                        "description": "Description of the transaction"
                    }
                },
                "required": ["phone_number", "amount", "account_reference", "transaction_desc"]
            }
        ),
        Tool(
            name="stk_query",
            description="Check the status of an STK Push transaction using the CheckoutRequestID",
            inputSchema={
                "type": "object",
                "properties": {
                    "checkout_request_id": {
                        "type": "string",
                        "description": "The CheckoutRequestID returned from the STK Push request"
                    }
                },
                "required": ["checkout_request_id"]
            }
        ),
        Tool(
            name="get_recent_payments",
            description="Get recent payment notifications received via callback",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent payments to retrieve (default: 10, max: 50)",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="get_payment_details",
            description="Get details of a specific payment by CheckoutRequestID or M-PESA receipt number",
            inputSchema={
                "type": "object",
                "properties": {
                    "checkout_request_id": {
                        "type": "string",
                        "description": "CheckoutRequestID to look up"
                    },
                    "mpesa_receipt": {
                        "type": "string",
                        "description": "M-PESA receipt number to look up"
                    }
                }
            }
        ),
        Tool(
            name="mark_payment_read",
            description="Mark a payment notification as read",
            inputSchema={
                "type": "object",
                "properties": {
                    "checkout_request_id": {
                        "type": "string",
                        "description": "CheckoutRequestID to mark as read"
                    }
                },
                "required": ["checkout_request_id"]
            }
        ),
        Tool(
            name="get_notification_summary",
            description="Get summary of payment notifications (total, unread count, etc.)",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_callback_status",
            description="Check if the callback server is running and get its URL",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls"""
    
    if name == "stk_push":
        try:
            result = daraja.stk_push(
                phone_number=arguments["phone_number"],
                amount=arguments["amount"],
                account_reference=arguments["account_reference"],
                transaction_desc=arguments["transaction_desc"]
            )
            
            response_text = json.dumps(result, indent=2)
            if result.get('ResponseCode') == '0':
                response_text += f"\n\n✅ Payment request sent successfully!\nCheckoutRequestID: {result.get('CheckoutRequestID')}\n\nWaiting for customer to complete payment. You'll be notified automatically when payment is received."
            
            return [TextContent(type="text", text=response_text)]
        except Exception as e:
            return [TextContent(type="text", text=f"Error initiating STK Push: {str(e)}")]
    
    elif name == "stk_query":
        try:
            result = daraja.stk_query(checkout_request_id=arguments["checkout_request_id"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        except Exception as e:
            return [TextContent(type="text", text=f"Error querying STK status: {str(e)}")]
    
    elif name == "get_recent_payments":
        limit = arguments.get("limit", 10)
        limit = min(limit, 50)
        payments = payment_store.get_recent_payments(limit)
        
        summary = f"📊 Recent Payments ({len(payments)} total, {payment_store.get_unread_count()} unread)\n\n"
        
        for payment in payments:
            status_icon = "🆕" if not payment.get('read', False) else "✅"
            result_code = payment.get('ResultCode')
            
            if result_code == 0:
                summary += f"{status_icon} SUCCESSFUL PAYMENT\n"
                summary += f"   Amount: KES {payment.get('Amount', 'N/A')}\n"
                summary += f"   Receipt: {payment.get('MpesaReceiptNumber', 'N/A')}\n"
                summary += f"   Phone: {payment.get('PhoneNumber', 'N/A')}\n"
                summary += f"   Date: {payment.get('TransactionDate', 'N/A')}\n"
            else:
                summary += f"{status_icon} FAILED/CANCELLED\n"
                summary += f"   Reason: {payment.get('ResultDesc', 'N/A')}\n"
            
            summary += f"   CheckoutRequestID: {payment.get('CheckoutRequestID', 'N/A')}\n"
            summary += f"   Received: {payment.get('received_at', 'N/A')}\n\n"
        
        return [TextContent(type="text", text=summary if payments else "No payments received yet.")]
    
    elif name == "get_payment_details":
        checkout_id = arguments.get("checkout_request_id")
        receipt = arguments.get("mpesa_receipt")
        
        payment = None
        if checkout_id:
            payment = payment_store.get_payment_by_request_id(checkout_id)
        elif receipt:
            payment = payment_store.get_payment_by_transaction_id(receipt)
        
        if payment:
            return [TextContent(type="text", text=json.dumps(payment, indent=2))]
        else:
            return [TextContent(type="text", text="Payment not found.")]
    
    elif name == "mark_payment_read":
        checkout_id = arguments["checkout_request_id"]
        success = payment_store.mark_as_read(checkout_id)
        
        if success:
            return [TextContent(type="text", text=f"✅ Marked payment {checkout_id} as read.")]
        else:
            return [TextContent(type="text", text=f"❌ Payment {checkout_id} not found.")]
    
    elif name == "get_notification_summary":
        total = len(payment_store.payments)
        unread = payment_store.get_unread_count()
        
        summary = {
            "total_notifications": total,
            "unread_notifications": unread,
            "read_notifications": total - unread,
            "callback_url": config.get_callback_url()
        }
        
        return [TextContent(type="text", text=json.dumps(summary, indent=2))]
    
    elif name == "get_callback_status":
        try:
            # Test if Flask server is running
            response = requests.get(f"http://localhost:{config.callback_port}/health", timeout=2)
            status = response.json()
            
            return [TextContent(
                type="text",
                text=f"✅ Callback server is running!\n\n{json.dumps(status, indent=2)}\n\nMake sure this URL is accessible from Safaricom's servers."
            )]
        except Exception as e:
            return [TextContent(
                type="text",
                text=f"❌ Callback server issue: {str(e)}"
            )]
    
    else:
        return [TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    """Run the MCP server"""
    print(f"🚀 Daraja MCP Server starting...")
    print(f"📡 Callback server running on {config.callback_host}:{config.callback_port}")
    print(f"🌐 Public callback URL: {config.get_callback_url()}")
    print(f"🔧 Environment: {config.environment}")
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )

if __name__ == "__main__":
    # Suppress traceback on Ctrl+C so async cancellation doesn't flood the terminal
    _orig_excepthook = sys.excepthook
    def _quiet_exit_excepthook(etype, value, tb):
        if etype is KeyboardInterrupt or etype is asyncio.CancelledError:
            sys.exit(0)
        _orig_excepthook(etype, value, tb)
    sys.excepthook = _quiet_exit_excepthook

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, asyncio.CancelledError):
        sys.exit(0)
