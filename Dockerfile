# Daraja MCP Server - HTTP (gunicorn)
# Use server_http.py for containerized / cloud deployment

FROM python:3.12-slim

# Avoid interactive prompts
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Default port; override when running (e.g. -e PORT=8080)
ENV PORT=3000

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (HTTP server only; server.py is for local stdio/Claude Desktop)
COPY server_http.py .

EXPOSE 3000

# Use PORT so it can be overridden at runtime
CMD ["sh", "-c", "gunicorn server_http:app --bind 0.0.0.0:${PORT:-3000} --workers 2"]
