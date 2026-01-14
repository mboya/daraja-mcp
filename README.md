# Safaricom Daraja MCP Server

A Model Context Protocol (MCP) server that integrates Safaricom's M-PESA Daraja API with Claude, enabling natural language payment processing and real-time transaction notifications.

## 🌟 Features

- **STK Push Payments**: Initiate M-PESA payment requests through natural language
- **Real-time Callbacks**: Automatic payment notification handling with Flask server
- **Payment Tracking**: Store and query payment history with read/unread status
- **Natural Language Interface**: Interact with M-PESA through Claude conversations
- **Sandbox Testing**: Full support for Daraja sandbox environment
- **Automated Testing**: Comprehensive test suite for validation

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Getting Daraja Credentials](#getting-daraja-credentials)
- [Usage](#usage)
- [Testing](#testing)
- [Integrating with Claude Desktop](#integrating-with-claude-desktop)
- [Available Tools](#available-tools)
- [Callback Setup](#callback-setup)
- [Troubleshooting](#troubleshooting)
- [Security Best Practices](#security-best-practices)
- [Production Deployment](#production-deployment)
- [API Reference](#api-reference)
- [Contributing](#contributing)
- [License](#license)

## Prerequisites

- **Python 3.10+** installed on your system
- **Daraja API Account** - Register at [developer.safaricom.co.ke](https://developer.safaricom.co.ke/)
- **ngrok** (optional, for testing callbacks) - Download from [ngrok.com](https://ngrok.com/)
- **Claude Desktop** (optional, for MCP integration)

## Installation

### 1. Clone the Repository

```bash
# Clone the repository
git clone <repository-url>
cd daraja-mcp

# Or if you already have the repository, navigate to it
cd daraja-mcp
```

### 2. Set Up Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

You should see `(venv)` in your terminal prompt.

### 3. Install Dependencies

```bash
# Install all required packages from requirements.txt
pip install -r requirements.txt
```

This will install:
- `mcp` - Model Context Protocol server
- `requests` - HTTP library for API calls
- `flask` - Web framework for callback server
- `python-dotenv` - Environment variable management
- `gunicorn` - WSGI HTTP server (for production deployment)

### 4. Configure Environment Variables

Create a `.env` file in the project root directory (see Configuration section below for the template). This is the only file you need to create - all other project files are already included in the repository.

**Note:** See the "Choosing Between server.py and server_http.py" section below for guidance on which server file to use.

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Daraja API Credentials
DARAJA_CONSUMER_KEY=your_consumer_key_here
DARAJA_CONSUMER_SECRET=your_consumer_secret_here
DARAJA_SHORTCODE=174379
DARAJA_PASSKEY=your_passkey_here

# Environment (sandbox or production)
DARAJA_ENV=sandbox

# Callback Server Configuration
CALLBACK_PORT=3000
CALLBACK_HOST=0.0.0.0
PUBLIC_URL=http://localhost:3000
```

**Important:** Never commit `.env` to version control!

### Project Files

The repository already includes all necessary files:

- `server.py` - MCP server for local Claude Desktop integration (stdio)
- `server_http.py` - MCP server for cloud/production deployment (HTTP)
- `test_daraja.py` - Comprehensive test suite
- `quick_test.py` - Quick validation script
- `requirements.txt` - Python dependencies (already configured)
- `.gitignore` - Git ignore rules (already configured)
- `Procfile` - Railway deployment configuration
- `railway.json` - Railway platform settings
- `README.md` - This documentation

**You only need to create the `.env` file** with your Daraja API credentials (see template above).

## Getting Daraja Credentials

### 1. Register on Daraja Portal

1. Visit [developer.safaricom.co.ke](https://developer.safaricom.co.ke/)
2. Create an account
3. Verify your email

### 2. Create an App

1. Navigate to "My Apps" → "Create New App"
2. Select APIs:
   - Lipa Na M-PESA Online
   - M-PESA Express (STK Push)
3. Submit your app
4. Get your credentials:
   - Consumer Key
   - Consumer Secret
   - Passkey (in app details)

### 3. Sandbox Test Credentials

For testing, use these sandbox values:

- **Business Short Code:** 174379 (default sandbox)
- **Passkey:** Check your app details on Daraja portal
- **Test Phone Numbers:** 254708374149 (check Daraja docs for updated test numbers)
- **Test PIN:** Varies by sandbox version (usually simulated automatically)

### 4. Production Credentials

1. Test thoroughly in sandbox
2. Apply for production access through Daraja portal
3. Complete KYC and business verification
4. Receive production credentials
5. Update `.env` with production values and set `DARAJA_ENV=production`

## Usage

### Starting the Server

#### For Local Development (Claude Desktop)

```bash
# Activate virtual environment
source venv/bin/activate

# Run the stdio server for Claude Desktop
python server.py
```

**Expected output:**
```
🚀 Daraja MCP Server starting...
📡 Callback server running on 0.0.0.0:3000
🌐 Public callback URL: http://localhost:3000/mpesa/callback
🔧 Environment: sandbox
```

#### For Production/Cloud Deployment

```bash
# Activate virtual environment
source venv/bin/activate

# Run the HTTP server (for Railway, Heroku, etc.)
python server_http.py

# Or use gunicorn for production (as configured in Procfile)
gunicorn server_http:app --bind 0.0.0.0:$PORT --workers 2
```

**Expected output:**
```
🚀 Daraja MCP Server (HTTP Mode)
📡 Listening on port 3000
🌐 Public URL: http://localhost:3000
🔧 Environment: sandbox
```

### Server Components

The MCP server runs two components simultaneously:

1. **MCP Protocol Server** - Communicates with Claude via stdio
2. **Flask Callback Server** - Receives M-PESA payment notifications on port 3000

### Choosing Between `server.py` and `server_http.py`

This project includes two server implementations for different use cases:

#### `server.py` - For Local Claude Desktop Integration (stdio)

**Use this when:**
- Running the MCP server locally on your machine
- Integrating with Claude Desktop application
- Developing and testing locally
- Using stdio (standard input/output) for MCP communication

**Features:**
- Communicates with Claude Desktop via stdio protocol
- Runs Flask callback server in a background thread
- Full MCP tool implementation with all features
- Best for local development and testing

**Usage:**
```bash
python server.py
```

#### `server_http.py` - For Remote Deployment (HTTP)

**Use this when:**
- Deploying to cloud platforms (Railway, Heroku, AWS, etc.)
- Running in production environments
- Need HTTP-based MCP endpoints
- Using gunicorn or similar WSGI servers

**Features:**
- Single Flask app combining MCP HTTP endpoints and callbacks
- Exposes `/mcp/tools` and `/mcp/call_tool` endpoints
- Works with gunicorn for production deployment
- Compatible with Railway's Procfile configuration

**Usage:**
```bash
# For production with gunicorn (as configured in Procfile)
gunicorn server_http:app --bind 0.0.0.0:$PORT --workers 2

# For local testing
python server_http.py
```

**Railway Deployment:**
The `Procfile` is configured to use `server_http.py` with gunicorn:
```
web: gunicorn server_http:app --bind 0.0.0.0:$PORT --workers 2
```

**Summary:**
- **Local development with Claude Desktop** → Use `server.py`
- **Cloud/production deployment** → Use `server_http.py`

## Testing

### Quick Test (Recommended for daily checks)

```bash
# Terminal 1: Start server
source venv/bin/activate
python server.py

# Terminal 2: Run quick test
source venv/bin/activate
python quick_test.py
```

**Expected output:**
```
🔐 Testing Daraja Authentication...
✅ Authentication successful! (sandbox environment)

🌐 Testing Callback Server...
✅ Callback server is running!

📨 Testing Callback Endpoint...
✅ Callback endpoint working!

Tests passed: 3/3
🎉 All tests passed!
```

### Comprehensive Test Suite

```bash
python test_daraja.py
```

This runs 8 test phases:
1. Environment variable validation
2. Python dependency checks
3. Daraja API authentication
4. MCP server startup
5. Callback server health
6. Callback endpoint processing
7. ngrok availability
8. STK push format validation

### Manual Testing

#### Test Authentication
```bash
curl -X GET "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials" \
  -H "Authorization: Basic $(echo -n 'KEY:SECRET' | base64)"
```

#### Test Callback Server
```bash
curl http://localhost:3000/health
```

#### Test Callback Endpoint
```bash
curl -X POST http://localhost:3000/mpesa/callback \
  -H "Content-Type: application/json" \
  -d '{
    "Body": {
      "stkCallback": {
        "ResultCode": 0,
        "ResultDesc": "Success"
      }
    }
  }'
```

## Integrating with Claude Desktop

### 1. Locate Configuration File

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

### 2. Add MCP Server Configuration

```json
{
  "mcpServers": {
    "daraja": {
      "command": "/absolute/path/to/daraja-mcp/venv/bin/python",
      "args": ["/absolute/path/to/daraja-mcp/server.py"],
      "env": {
        "DARAJA_CONSUMER_KEY": "your_consumer_key",
        "DARAJA_CONSUMER_SECRET": "your_consumer_secret",
        "DARAJA_SHORTCODE": "174379",
        "DARAJA_PASSKEY": "your_passkey",
        "DARAJA_ENV": "sandbox",
        "CALLBACK_PORT": "3000",
        "PUBLIC_URL": "https://your-ngrok-url.ngrok.io"
      }
    }
  }
}
```

**Important:** 
- Use absolute paths (not relative)
- Use virtual environment's Python: `venv/bin/python`
- Update PUBLIC_URL with your ngrok HTTPS URL

### 3. Restart Claude Desktop

Completely quit and reopen Claude Desktop to load the MCP server.

### 4. Verify Integration

In Claude Desktop, ask:
```
"Is the Daraja callback server working?"
```

Claude should respond with server status information.

## Available Tools

Once configured, Claude can use these tools:

### 1. `stk_push`
Initiate an STK Push payment request.

**Example:**
```
"Send a payment request for 500 KES to 0712345678 for order #INV-001"
```

**Parameters:**
- `phone_number` - Customer phone (254XXXXXXXXX or 07XXXXXXXX)
- `amount` - Amount in KES (minimum 1)
- `account_reference` - Reference like invoice/order number
- `transaction_desc` - Description of transaction

### 2. `stk_query`
Check the status of a payment request.

**Example:**
```
"Check the status of checkout request ws_CO_12345"
```

**Parameters:**
- `checkout_request_id` - ID returned from STK push

### 3. `get_recent_payments`
View recent payment notifications.

**Example:**
```
"Show me the last 10 payments"
```

**Parameters:**
- `limit` - Number of payments to retrieve (default: 10, max: 50)

### 4. `get_payment_details`
Get details of a specific payment.

**Example:**
```
"Show me details for receipt QAR7I8K3LM"
```

**Parameters:**
- `checkout_request_id` - Or -
- `mpesa_receipt` - M-PESA receipt number

### 5. `mark_payment_read`
Mark a notification as read.

**Example:**
```
"Mark payment ws_CO_12345 as read"
```

### 6. `get_notification_summary`
Get summary of all notifications.

**Example:**
```
"How many unread payments do I have?"
```

### 7. `get_callback_status`
Check if callback server is running.

**Example:**
```
"Is the callback server working?"
```

## Callback Setup

### Why You Need ngrok (or Similar Tunneling Service)

**The Problem:**
- M-PESA Daraja API requires **HTTPS callbacks** (not HTTP)
- Safaricom's servers need to reach your callback endpoint from the internet
- Your local development server (`localhost:3000`) is not accessible from the internet
- Firewalls and NAT prevent external access to your local machine

**The Solution:**
ngrok creates a secure tunnel that:
- ✅ Exposes your local server to the internet via HTTPS
- ✅ Provides a public URL that Safaricom can reach
- ✅ Automatically handles SSL/TLS encryption
- ✅ Allows real-time testing without deploying to production
- ✅ Shows all incoming requests in a web interface for debugging

**How It Works:**
```
Safaricom Servers → ngrok HTTPS URL → ngrok Tunnel → Your Local Server (localhost:3000)
```

### Local Testing with ngrok

#### 1. Install ngrok

```bash
# macOS
brew install ngrok

# Linux (using snap)
sudo snap install ngrok

# Windows
# Download from https://ngrok.com/download
# Or use Chocolatey: choco install ngrok

# Or download directly from https://ngrok.com/download
```

**Sign up for free:** Visit [ngrok.com](https://ngrok.com/) and create an account to get your authtoken.

#### 2. Authenticate ngrok (First Time Only)

```bash
ngrok config add-authtoken YOUR_AUTHTOKEN_HERE
```

#### 3. Start ngrok Tunnel

```bash
# Forward HTTPS traffic to your local port 3000
ngrok http 3000
```

**Output:**
```
Session Status                online
Account                       Your Name (Plan: Free)
Version                       3.x.x
Region                        United States (us)
Latency                       45ms
Web Interface                 http://127.0.0.1:4040
Forwarding                    https://abc123.ngrok.io -> http://localhost:3000

Connections                   ttl     opn     rt1     rt5     p50     p90
                              0       0       0.00    0.00    0.00    0.00
```

**Important:** Copy the `Forwarding` HTTPS URL (e.g., `https://abc123.ngrok.io`)

#### 4. Update Configuration

Update `PUBLIC_URL` in your `.env` file:
```bash
PUBLIC_URL=https://abc123.ngrok.io
```

Or update Claude Desktop config with the ngrok URL.

**Note:** Free ngrok URLs change each time you restart ngrok. For a static URL, upgrade to a paid plan or use ngrok's reserved domains feature.

#### 5. Restart Server

```bash
# Stop the server (Ctrl+C)
# Restart with new PUBLIC_URL
python server.py
```

#### 6. Verify ngrok is Working

**Check ngrok web interface:**
- Open http://localhost:4040 in your browser
- You'll see all requests being forwarded through ngrok
- Useful for debugging callback issues

**Test the tunnel:**
```bash
# Test health endpoint through ngrok
curl https://abc123.ngrok.io/health

# Should return:
# {"status":"healthy","callback_url":"https://abc123.ngrok.io/mpesa/callback",...}
```

#### 7. Keep ngrok Running

**Important:** Keep the ngrok terminal window open while testing. If you close it, the tunnel stops and Safaricom won't be able to reach your callback endpoint.

**Pro Tip:** Run ngrok in a separate terminal or use a process manager like `tmux` or `screen`:
```bash
# Using tmux
tmux new -s ngrok
ngrok http 3000
# Press Ctrl+B then D to detach (keeps running in background)
```

### ngrok Alternatives

If you prefer other tunneling services:

- **Cloudflare Tunnel (cloudflared)** - Free, no account needed for basic use
  ```bash
  cloudflared tunnel --url http://localhost:3000
  ```

- **localtunnel** - Simple npm-based tunnel
  ```bash
  npx localtunnel --port 3000
  ```

- **serveo** - SSH-based tunnel (no installation)
  ```bash
  ssh -R 80:localhost:3000 serveo.net
  ```

However, ngrok is recommended because:
- Most reliable and stable
- Best documentation and community support
- Web interface for request inspection
- Easy to use and configure

### Production Callback Setup

For production, deploy to a server with:

1. **Public HTTPS endpoint** (SSL certificate required)
2. **Static IP or domain name**
3. **Firewall rules** allowing incoming HTTPS traffic
4. **Monitoring and logging**

**Popular options:**
- AWS EC2 with Elastic IP
- DigitalOcean Droplet
- Heroku with SSL
- Google Cloud Run
- **Railway** (recommended - see deployment guide below)

**Example nginx configuration:**
```nginx
server {
    listen 443 ssl;
    server_name api.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location /mpesa/ {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Railway Deployment (Quick Start)

Railway is an excellent choice for deploying this MCP server because it:
- ✅ Provides HTTPS endpoints automatically
- ✅ Handles SSL certificates
- ✅ Easy environment variable configuration
- ✅ Automatic deployments from Git
- ✅ Free tier available for testing

#### Railway Deployment Steps

1. **Create Railway Account**
   - Visit [railway.app](https://railway.app)
   - Sign up with GitHub/GitLab

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo" (or upload code)

3. **Configure Environment Variables**
   In Railway dashboard, add these environment variables:
   ```
   DARAJA_CONSUMER_KEY=your_consumer_key
   DARAJA_CONSUMER_SECRET=your_consumer_secret
   DARAJA_SHORTCODE=174379
   DARAJA_PASSKEY=your_passkey
   DARAJA_ENV=sandbox
   CALLBACK_PORT=3000
   CALLBACK_HOST=0.0.0.0
   PUBLIC_URL=https://your-app-name.railway.app
   ```

4. **Deploy**
   - Railway will automatically detect `Procfile` and `railway.json`
   - The `Procfile` uses `server_http.py` with gunicorn
   - Railway will build and deploy automatically

5. **Get Your Public URL**
   - Railway provides a public HTTPS URL (e.g., `https://your-app.railway.app`)
   - Update `PUBLIC_URL` environment variable with this URL
   - Railway will restart the service automatically

6. **Verify Deployment**
   ```bash
   # Test health endpoint
   curl https://your-app.railway.app/health
   
   # Should return:
   # {"status":"healthy","callback_url":"https://your-app.railway.app/mpesa/callback",...}
   ```

**Important Notes:**
- Railway automatically provides HTTPS, so no ngrok needed in production
- The `PUBLIC_URL` must match your Railway app URL exactly
- Use `server_http.py` (configured in `Procfile`) for Railway deployments
- Railway handles port binding automatically via `$PORT` environment variable

## Troubleshooting

### Common Issues

#### 1. "Failed to get access token"

**Causes:**
- Invalid Consumer Key or Secret
- Wrong environment (sandbox vs production)
- Network connectivity issues

**Solutions:**
```bash
# Test authentication manually
python -c "
from dotenv import load_dotenv
import os, base64, requests
load_dotenv()
key = os.getenv('DARAJA_CONSUMER_KEY')
secret = os.getenv('DARAJA_CONSUMER_SECRET')
auth = base64.b64encode(f'{key}:{secret}'.encode()).decode()
r = requests.get('https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials',
                 headers={'Authorization': f'Basic {auth}'})
print(r.json())
"
```

#### 2. "Callback server not responding"

**Solutions:**
```bash
# Check if port 3000 is available
lsof -i :3000

# Kill any process using the port
kill -9 <PID>

# Restart server
python server.py
```

#### 3. "MCP server not found in Claude"

**Solutions:**
- Verify config file path is correct
- Use absolute paths in configuration
- Ensure virtual environment Python path is correct
- Check Claude Desktop logs: Help → View Logs
- Restart Claude Desktop completely

#### 4. "No callbacks received"

**Solutions:**
- Verify ngrok is running: `curl https://your-url.ngrok.io/health`
- Check PUBLIC_URL environment variable
- Ensure ngrok URL is HTTPS (required by Safaricom)
- View ngrok request logs: http://localhost:4040
- Check firewall settings

#### 5. "Invalid phone number"

**Solutions:**
- Use format: 254XXXXXXXXX (not +254 or 07XX)
- Sandbox: Use test numbers from Daraja portal
- Remove spaces, dashes, or special characters

### Debug Commands

```bash
# Check server process
ps aux | grep server.py

# Test callback health
curl http://localhost:3000/health

# Test ngrok forwarding
curl https://your-ngrok-url.ngrok.io/health

# View Python errors
tail -f server.log

# Check Claude logs
# macOS: ~/Library/Logs/Claude/
# Windows: %APPDATA%\Claude\logs\
```

### Getting Help

1. Check Daraja API documentation: [developer.safaricom.co.ke/Documentation](https://developer.safaricom.co.ke/Documentation)
2. Review ngrok request inspector: http://localhost:4040
3. Check Claude Desktop logs
4. Verify all environment variables are set correctly
5. Test each component independently

## Security Best Practices

### 1. Credential Management

- ✅ **Never commit credentials** to version control
- ✅ Use `.env` files with `.gitignore`
- ✅ Rotate credentials regularly
- ✅ Use different credentials for sandbox and production
- ✅ Store production secrets in secure vaults (AWS Secrets Manager, etc.)

### 2. Network Security

- ✅ Use HTTPS for all callbacks (required by Safaricom)
- ✅ Implement webhook signature verification
- ✅ Restrict callback endpoint to Safaricom IPs
- ✅ Use firewall rules to limit access
- ✅ Enable rate limiting

### 3. Application Security

- ✅ Validate all input data
- ✅ Sanitize phone numbers and amounts
- ✅ Implement request logging
- ✅ Add authentication for sensitive operations
- ✅ Use environment-specific configurations

### 4. Data Privacy

- ✅ Don't log sensitive data (PINs, full card numbers)
- ✅ Mask phone numbers in logs
- ✅ Implement data retention policies
- ✅ Comply with data protection regulations
- ✅ Encrypt data at rest and in transit

### 5. Monitoring

- ✅ Set up error alerting
- ✅ Monitor callback success rates
- ✅ Track failed transactions
- ✅ Log all API calls
- ✅ Implement health checks

## Production Deployment

### Pre-deployment Checklist

- [ ] Thoroughly tested in sandbox environment
- [ ] Obtained production credentials from Daraja
- [ ] Set up production server with SSL/TLS
- [ ] Configured firewall and security groups
- [ ] Implemented proper logging and monitoring
- [ ] Set up error alerting
- [ ] Documented deployment process
- [ ] Created backup and recovery plan
- [ ] Tested with small amounts first
- [ ] Configured auto-restart on failure

### Deployment Steps

#### 1. Prepare Server

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python
sudo apt install python3.10 python3.10-venv -y

# Install nginx (for reverse proxy)
sudo apt install nginx -y

# Install supervisor (for process management)
sudo apt install supervisor -y
```

#### 2. Deploy Application

```bash
# Create application directory
sudo mkdir -p /opt/daraja-mcp
sudo chown $USER:$USER /opt/daraja-mcp
cd /opt/daraja-mcp

# Clone or copy application files
# Set up virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create production .env
nano .env
# Add production credentials
```

#### 3. Configure Supervisor

Create `/etc/supervisor/conf.d/daraja-mcp.conf`:

```ini
[program:daraja-mcp]
command=/opt/daraja-mcp/venv/bin/python /opt/daraja-mcp/server.py
directory=/opt/daraja-mcp
user=www-data
autostart=true
autorestart=true
stderr_logfile=/var/log/daraja-mcp/error.log
stdout_logfile=/var/log/daraja-mcp/access.log
environment=PRODUCTION="true"
```

#### 4. Configure nginx

Create `/etc/nginx/sites-available/daraja-mcp`:

```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 5. Start Services

```bash
# Reload supervisor
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start daraja-mcp

# Enable and restart nginx
sudo ln -s /etc/nginx/sites-available/daraja-mcp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Check status
sudo supervisorctl status daraja-mcp
curl https://api.yourdomain.com/health
```

### Monitoring and Maintenance

```bash
# View logs
sudo tail -f /var/log/daraja-mcp/error.log

# Restart service
sudo supervisorctl restart daraja-mcp

# Check resource usage
htop

# Monitor nginx access
sudo tail -f /var/log/nginx/access.log
```

## API Reference

### Daraja API Endpoints

#### Authentication
```
GET https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials
Authorization: Basic <base64(consumer_key:consumer_secret)>
```

#### STK Push
```
POST https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "BusinessShortCode": "174379",
  "Password": "<base64(shortcode+passkey+timestamp)>",
  "Timestamp": "20240108143022",
  "TransactionType": "CustomerPayBillOnline",
  "Amount": 100,
  "PartyA": "254712345678",
  "PartyB": "174379",
  "PhoneNumber": "254712345678",
  "CallBackURL": "https://your-domain.com/callback",
  "AccountReference": "Order123",
  "TransactionDesc": "Payment for Order123"
}
```

#### STK Query
```
POST https://api.safaricom.co.ke/mpesa/stkpushquery/v1/query
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "BusinessShortCode": "174379",
  "Password": "<base64(shortcode+passkey+timestamp)>",
  "Timestamp": "20240108143022",
  "CheckoutRequestID": "ws_CO_08012024123456789"
}
```

### MCP Server Endpoints

#### Health Check
```
GET http://localhost:3000/health

Response:
{
  "status": "healthy",
  "callback_url": "http://localhost:3000/mpesa/callback",
  "unread_payments": 0
}
```

#### M-PESA Callback
```
POST http://localhost:3000/mpesa/callback
Content-Type: application/json

{
  "Body": {
    "stkCallback": {
      "MerchantRequestID": "29115-34620561-1",
      "CheckoutRequestID": "ws_CO_08012024123456789",
      "ResultCode": 0,
      "ResultDesc": "The service request is processed successfully.",
      "CallbackMetadata": {
        "Item": [
          {"Name": "Amount", "Value": 100},
          {"Name": "MpesaReceiptNumber", "Value": "QAR7I8K3LM"},
          {"Name": "TransactionDate", "Value": 20240108143022},
          {"Name": "PhoneNumber", "Value": 254712345678}
        ]
      }
    }
  }
}
```

## Project Structure

```
daraja-mcp/
├── venv/                       # Virtual environment (not in git)
├── server.py                   # MCP server for local Claude Desktop (stdio)
├── server_http.py              # MCP server for cloud deployment (HTTP)
├── test_daraja.py             # Comprehensive test suite
├── quick_test.py              # Quick validation script
├── Procfile                   # Railway deployment configuration
├── railway.json               # Railway platform configuration
├── .env                       # Environment variables (not in git)
├── .gitignore                 # Git ignore rules
├── requirements.txt           # Python dependencies
├── README.md                  # This file
└── docs/                      # Additional documentation
    ├── DEPLOYMENT.md          # Deployment guide
    ├── API.md                 # API documentation
    └── TROUBLESHOOTING.md     # Extended troubleshooting
```

**Key Files:**
- `server.py` - Use for local development with Claude Desktop (stdio protocol)
- `server_http.py` - Use for cloud deployments like Railway (HTTP endpoints)
- `Procfile` - Defines how Railway runs the application (uses `server_http.py`)
- `railway.json` - Railway platform configuration (builder, replicas, restart policy)

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Clone repo
git clone https://github.com/yourusername/daraja-mcp.git
cd daraja-mcp

# Set up environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
python test_daraja.py
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Safaricom Daraja API](https://developer.safaricom.co.ke/) - M-PESA API platform
- [Anthropic MCP](https://modelcontextprotocol.io/) - Model Context Protocol
- [Flask](https://flask.palletsprojects.com/) - Web framework for callbacks
- [ngrok](https://ngrok.com/) - Secure tunneling for local development

## Support

- **Documentation:** [developer.safaricom.co.ke/Documentation](https://developer.safaricom.co.ke/Documentation)
- **Daraja Support:** support@safaricom.co.ke
- **MCP Documentation:** [modelcontextprotocol.io](https://modelcontextprotocol.io/)
- **Issues:** [GitHub Issues](https://github.com/yourusername/daraja-mcp/issues)

## Changelog

### v1.0.0 (2024-01-08)
- Initial release
- STK Push implementation
- Real-time callback handling
- Payment notification storage
- Automated testing suite
- Claude Desktop integration
- Comprehensive documentation

---

**Made with ❤️ for the M-PESA ecosystem**

For questions or support, please open an issue on GitHub or contact the maintainers.