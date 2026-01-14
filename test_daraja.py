#!/usr/bin/env python3
"""
Automated Testing Script for Daraja MCP Server
Tests all components: authentication, callback server, MCP integration
"""

import os
import sys
import time
import json
import base64
import requests
import subprocess
from datetime import datetime
from typing import Tuple, Optional
from dotenv import load_dotenv
import signal


# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a section header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message"""
    print(f"{Colors.GREEN}✅ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message"""
    print(f"{Colors.RED}❌ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message"""
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.RESET}")


class DarajaTestSuite:
    def __init__(self):
        load_dotenv()

        self.consumer_key = os.getenv("DARAJA_CONSUMER_KEY")
        self.consumer_secret = os.getenv("DARAJA_CONSUMER_SECRET")
        self.shortcode = os.getenv("DARAJA_SHORTCODE", "174379")
        self.passkey = os.getenv("DARAJA_PASSKEY")
        self.environment = os.getenv("DARAJA_ENV", "sandbox")
        self.callback_port = os.getenv("CALLBACK_PORT", "3000")
        self.public_url = os.getenv("PUBLIC_URL", f"http://localhost:{self.callback_port}")

        self.base_url = "https://sandbox.safaricom.co.ke" if self.environment == "sandbox" else "https://api.safaricom.co.ke"
        self.server_process = None
        self.ngrok_process = None

        self.test_results = {
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "total": 0
        }

    def record_result(self, passed: bool, warning: bool = False):
        """Record test result"""
        self.test_results["total"] += 1
        if warning:
            self.test_results["warnings"] += 1
        elif passed:
            self.test_results["passed"] += 1
        else:
            self.test_results["failed"] += 1

    def print_summary(self):
        """Print test summary"""
        print_header("TEST SUMMARY")
        total = self.test_results["total"]
        passed = self.test_results["passed"]
        failed = self.test_results["failed"]
        warnings = self.test_results["warnings"]

        print(f"Total Tests: {total}")
        print_success(f"Passed: {passed}")
        if failed > 0:
            print_error(f"Failed: {failed}")
        if warnings > 0:
            print_warning(f"Warnings: {warnings}")

        if failed == 0:
            print_success("\n🎉 All critical tests passed!")
        else:
            print_error(f"\n⚠️  {failed} test(s) failed. Please review the errors above.")

    def test_environment_variables(self) -> bool:
        """Test if all required environment variables are set"""
        print_header("Phase 1: Environment Variables")

        required_vars = {
            "DARAJA_CONSUMER_KEY": self.consumer_key,
            "DARAJA_CONSUMER_SECRET": self.consumer_secret,
            "DARAJA_SHORTCODE": self.shortcode,
            "DARAJA_PASSKEY": self.passkey
        }

        all_set = True
        for var_name, var_value in required_vars.items():
            if var_value:
                print_success(f"{var_name} is set")
            else:
                print_error(f"{var_name} is NOT set")
                all_set = False

        print_info(f"Environment: {self.environment}")
        print_info(f"Base URL: {self.base_url}")
        print_info(f"Callback Port: {self.callback_port}")
        print_info(f"Public URL: {self.public_url}")

        self.record_result(all_set)
        return all_set

    def test_daraja_authentication(self) -> Tuple[bool, Optional[str]]:
        """Test Daraja API authentication"""
        print_header("Phase 2: Daraja Authentication")

        try:
            auth_string = f"{self.consumer_key}:{self.consumer_secret}"
            encoded_auth = base64.b64encode(auth_string.encode()).decode()

            headers = {"Authorization": f"Basic {encoded_auth}"}

            print_info("Requesting access token...")
            response = requests.get(
                f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials",
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                expires_in = data.get("expires_in")

                print_success(f"Authentication successful!")
                print_info(f"Token expires in: {expires_in} seconds")
                print_info(f"Token (first 20 chars): {token[:20]}...")

                self.record_result(True)
                return True, token
            else:
                print_error(f"Authentication failed: {response.status_code}")
                print_error(f"Response: {response.text}")
                self.record_result(False)
                return False, None

        except Exception as e:
            print_error(f"Authentication error: {str(e)}")
            self.record_result(False)
            return False, None

    def test_python_dependencies(self) -> bool:
        """Test if required Python packages are installed"""
        print_header("Phase 3: Python Dependencies")

        required_packages = ["mcp", "requests", "flask", "dotenv"]
        all_installed = True

        for package in required_packages:
            try:
                __import__(package if package != "dotenv" else "dotenv")
                print_success(f"{package} is installed")
            except ImportError:
                print_error(f"{package} is NOT installed")
                print_info(f"Install with: pip install {package if package != 'dotenv' else 'python-dotenv'}")
                all_installed = False

        self.record_result(all_installed)
        return all_installed

    def start_mcp_server(self) -> bool:
        """Start the MCP server"""
        print_header("Phase 4: MCP Server")

        print_info("Starting MCP server...")

        try:
            # Check if server.py exists
            if not os.path.exists("server.py"):
                print_error("server.py not found in current directory")
                self.record_result(False)
                return False

            # Start the server
            self.server_process = subprocess.Popen(
                [sys.executable, "server.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Wait a bit for server to start
            time.sleep(3)

            # Check if process is still running
            if self.server_process.poll() is None:
                print_success("MCP server started successfully")
                self.record_result(True)
                return True
            else:
                stdout, stderr = self.server_process.communicate()
                print_error("MCP server failed to start")
                print_error(f"Error: {stderr}")
                self.record_result(False)
                return False

        except Exception as e:
            print_error(f"Failed to start MCP server: {str(e)}")
            self.record_result(False)
            return False

    def test_callback_server(self) -> bool:
        """Test callback server health"""
        print_header("Phase 5: Callback Server")

        print_info("Testing callback server health endpoint...")

        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                response = requests.get(
                    f"http://localhost:{self.callback_port}/health",
                    timeout=5
                )

                if response.status_code == 200:
                    data = response.json()
                    print_success("Callback server is healthy!")
                    print_info(f"Status: {data.get('status')}")
                    print_info(f"Callback URL: {data.get('callback_url')}")
                    print_info(f"Unread payments: {data.get('unread_payments')}")

                    self.record_result(True)
                    return True
                else:
                    print_warning(f"Attempt {attempt + 1}/{max_attempts}: Server returned {response.status_code}")

            except requests.exceptions.ConnectionError:
                print_warning(f"Attempt {attempt + 1}/{max_attempts}: Connection refused, retrying...")
            except Exception as e:
                print_warning(f"Attempt {attempt + 1}/{max_attempts}: {str(e)}")

            if attempt < max_attempts - 1:
                time.sleep(2)

        print_error("Callback server is not responding")
        self.record_result(False)
        return False

    def test_callback_endpoint(self) -> bool:
        """Test callback endpoint with mock data"""
        print_header("Phase 6: Callback Endpoint")

        print_info("Sending test callback data...")

        # Mock M-PESA callback data
        mock_callback = {
            "Body": {
                "stkCallback": {
                    "MerchantRequestID": "test-merchant-123",
                    "CheckoutRequestID": "ws_CO_TEST123456789",
                    "ResultCode": 0,
                    "ResultDesc": "The service request is processed successfully.",
                    "CallbackMetadata": {
                        "Item": [
                            {"Name": "Amount", "Value": 100},
                            {"Name": "MpesaReceiptNumber", "Value": "TEST123ABC"},
                            {"Name": "TransactionDate", "Value": 20240108143022},
                            {"Name": "PhoneNumber", "Value": 254712345678}
                        ]
                    }
                }
            }
        }

        try:
            response = requests.post(
                f"http://localhost:{self.callback_port}/mpesa/callback",
                json=mock_callback,
                timeout=5
            )

            if response.status_code == 200:
                data = response.json()
                print_success("Callback endpoint processed request successfully!")
                print_info(f"Response: {json.dumps(data, indent=2)}")

                # Wait a moment for processing
                time.sleep(1)

                # Check if payment was stored
                health_response = requests.get(f"http://localhost:{self.callback_port}/health")
                health_data = health_response.json()

                if health_data.get("unread_payments", 0) > 0:
                    print_success("Payment notification stored successfully!")
                    self.record_result(True)
                    return True
                else:
                    print_warning("Payment may not have been stored")
                    self.record_result(True, warning=True)
                    return True
            else:
                print_error(f"Callback failed: {response.status_code}")
                print_error(f"Response: {response.text}")
                self.record_result(False)
                return False

        except Exception as e:
            print_error(f"Callback test failed: {str(e)}")
            self.record_result(False)
            return False

    def test_ngrok_available(self) -> bool:
        """Test if ngrok is available"""
        print_header("Phase 7: ngrok (Optional)")

        print_info("Checking if ngrok is installed...")

        try:
            result = subprocess.run(
                ["ngrok", "version"],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                version = result.stdout.strip()
                print_success(f"ngrok is installed: {version}")
                print_info("You can start ngrok with: ngrok http 3000")
                self.record_result(True, warning=True)
                return True
            else:
                print_warning("ngrok command failed")
                print_info("Install ngrok from: https://ngrok.com/download")
                self.record_result(True, warning=True)
                return False

        except FileNotFoundError:
            print_warning("ngrok is not installed")
            print_info("ngrok is required for testing callbacks from Safaricom")
            print_info("Install from: https://ngrok.com/download")
            self.record_result(True, warning=True)
            return False
        except Exception as e:
            print_warning(f"Could not check ngrok: {str(e)}")
            self.record_result(True, warning=True)
            return False

    def test_stk_push_format(self, access_token: str) -> bool:
        """Test STK push request format (without actual execution)"""
        print_header("Phase 8: STK Push Format Validation")

        print_info("Validating STK push request format...")

        try:
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            password_string = f"{self.shortcode}{self.passkey}{timestamp}"
            password = base64.b64encode(password_string.encode()).decode()

            payload = {
                "BusinessShortCode": self.shortcode,
                "Password": password,
                "Timestamp": timestamp,
                "TransactionType": "CustomerPayBillOnline",
                "Amount": 1,
                "PartyA": "254708374149",
                "PartyB": self.shortcode,
                "PhoneNumber": "254708374149",
                "CallBackURL": f"{self.public_url}/mpesa/callback",
                "AccountReference": "TEST001",
                "TransactionDesc": "Test Payment"
            }

            print_success("STK push payload generated successfully")
            print_info("Sample payload:")
            print(json.dumps({k: v for k, v in payload.items() if k != "Password"}, indent=2))

            print_warning("Note: Not executing actual STK push to avoid charges")
            print_info("To test actual STK push, use the MCP server through Claude")

            self.record_result(True, warning=True)
            return True

        except Exception as e:
            print_error(f"STK push format validation failed: {str(e)}")
            self.record_result(False)
            return False

    def cleanup(self):
        """Clean up processes"""
        print_header("Cleanup")

        if self.server_process:
            print_info("Stopping MCP server...")
            self.server_process.terminate()
            try:
                self.server_process.wait(timeout=5)
                print_success("MCP server stopped")
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                print_warning("MCP server force killed")

        if self.ngrok_process:
            print_info("Stopping ngrok...")
            self.ngrok_process.terminate()
            try:
                self.ngrok_process.wait(timeout=5)
                print_success("ngrok stopped")
            except subprocess.TimeoutExpired:
                self.ngrok_process.kill()
                print_warning("ngrok force killed")

    def run_all_tests(self):
        """Run all tests"""
        print(f"{Colors.BOLD}{Colors.BLUE}")
        print("=" * 60)
        print("  DARAJA MCP SERVER - AUTOMATED TEST SUITE")
        print("=" * 60)
        print(f"{Colors.RESET}\n")

        try:
            # Phase 1: Environment
            if not self.test_environment_variables():
                print_error("\n❌ Environment variables not properly configured")
                print_info("Please set all required environment variables and try again")
                return

            # Phase 2: Dependencies
            if not self.test_python_dependencies():
                print_error("\n❌ Missing required Python packages")
                print_info("Install with: pip install mcp requests flask python-dotenv")
                return

            # Phase 3: Authentication
            auth_success, token = self.test_daraja_authentication()
            if not auth_success:
                print_error("\n❌ Daraja authentication failed")
                print_info("Check your Consumer Key and Consumer Secret")
                return

            # Phase 4: Start server
            if not self.start_mcp_server():
                print_error("\n❌ Failed to start MCP server")
                return

            # Phase 5: Test callback server
            if not self.test_callback_server():
                print_error("\n❌ Callback server not responding")
                return

            # Phase 6: Test callback endpoint
            self.test_callback_endpoint()

            # Phase 7: Check ngrok
            self.test_ngrok_available()

            # Phase 8: Validate STK format
            if token:
                self.test_stk_push_format(token)

        except KeyboardInterrupt:
            print_warning("\n\nTests interrupted by user")
        except Exception as e:
            print_error(f"\n\nUnexpected error: {str(e)}")
        finally:
            self.cleanup()
            self.print_summary()


def main():
    """Main function"""
    test_suite = DarajaTestSuite()

    # Handle Ctrl+C gracefully
    def signal_handler(sig, frame):
        print_warning("\n\nReceived interrupt signal, cleaning up...")
        test_suite.cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Run tests
    test_suite.run_all_tests()


if __name__ == "__main__":
    main()