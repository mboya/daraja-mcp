# Docker

Run the Daraja MCP HTTP server in a container and publish it to Docker Hub.

## Build

From the project root:

```bash
# Build with default tag
docker build -t daraja-mcp .

# Build with your Docker Hub username and tag
docker build -t YOUR_DOCKERHUB_USERNAME/daraja-mcp:latest .
```

## Run locally

```bash
# Run on port 3000 (default)
docker run -p 3000:3000 --env-file .env daraja-mcp

# Run on a different host port
docker run -p 8080:3000 -e PORT=3000 --env-file .env daraja-mcp
```

Pass Daraja credentials via env or `--env-file`:

```bash
docker run -p 3000:3000 \
  -e DARAJA_CONSUMER_KEY=your_key \
  -e DARAJA_CONSUMER_SECRET=your_secret \
  -e DARAJA_SHORTCODE=174379 \
  -e DARAJA_PASSKEY=your_passkey \
  -e DARAJA_ENV=sandbox \
  -e CALLBACK_PORT=3000 \
  -e PUBLIC_URL=https://your-public-url.example.com \
  daraja-mcp
```

**Note:** `PUBLIC_URL` must be the URL where the container is reachable (e.g. your host or a reverse proxy), so M-PESA callbacks work.

## Push to Docker Hub

1. Log in:

   ```bash
   docker login
   ```

2. Tag the image with your Docker Hub username and repository name:

   ```bash
   docker tag daraja-mcp YOUR_DOCKERHUB_USERNAME/daraja-mcp:latest
   # Or add a version tag
   docker tag daraja-mcp YOUR_DOCKERHUB_USERNAME/daraja-mcp:1.0.0
   ```

3. Push:

   ```bash
   docker push YOUR_DOCKERHUB_USERNAME/daraja-mcp:latest
   docker push YOUR_DOCKERHUB_USERNAME/daraja-mcp:1.0.0   # if you created a version tag
   ```

Replace `YOUR_DOCKERHUB_USERNAME` with your Docker Hub username (e.g. `mboya`).

## Pull and run from Docker Hub

```bash
docker pull YOUR_DOCKERHUB_USERNAME/daraja-mcp:latest
docker run -p 3000:3000 --env-file .env YOUR_DOCKERHUB_USERNAME/daraja-mcp:latest
```

## Image details

- **Base:** `python:3.12-slim`
- **Entrypoint:** `gunicorn server_http:app --bind 0.0.0.0:${PORT:-3000} --workers 2`
- **Port:** 3000 (set `PORT` to change it)
- **Secrets:** Never bake credentials into the image; use `-e` or `--env-file` at runtime.
