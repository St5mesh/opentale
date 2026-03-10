# Docker Setup for OpenTale

This application can be run entirely in Docker using Docker Compose, which orchestrates both the Flask app and the Ollama LLM server.

## Quick Start with Docker Compose

### Prerequisites
- Docker: [Download Docker Desktop](https://www.docker.com/products/docker-desktop)
- Docker Compose: (included with Docker Desktop)

### Launch the Application

```bash
docker-compose up
```

On first run:
1. Docker will build the Flask image
2. Ollama container will start
3. A default model (`gemma:latest`) will be automatically pulled and loaded
4. Flask app will wait for Ollama to be ready, then start

Access the app at: **http://localhost:5000**

### What's Running

- **Flask Web App** on `http://localhost:5000`
- **Ollama LLM Server** on `http://localhost:11434`
- **Shared Network**: `opentale-network` allows containers to communicate
- **Volume**: `ollama_data` persists downloaded models between restarts
- **Volume**: `./book_output` persists generated content on your host machine

## Detailed Configuration

### Using Different Models

Edit `docker-compose.yml` to change the default model:

```yaml
services:
  web:
    environment:
      - LLM_MODEL=mistral:latest  # Change this to your preferred model
```

Then restart:
```bash
docker-compose up --build
```

### Configuring LLM Parameters

You can override LLM settings via environment variables in `docker-compose.yml`:

```yaml
services:
  web:
    environment:
      - LLM_URL=http://ollama:11434/v1
      - LLM_MODEL=gemma:latest
      - LLM_TEMPERATURE=0.8          # Higher = more creative
      - LLM_TIMEOUT=900              # Timeout in seconds
```

## Managing Containers

### View running containers
```bash
docker-compose ps
```

### View logs
```bash
# All services
docker-compose logs -f

# Only Flask app
docker-compose logs -f web

# Only Ollama
docker-compose logs -f ollama
```

### Stop containers (keep volumes)
```bash
docker-compose stop
```

### Restart containers
```bash
docker-compose restart
```

### Remove everything (including containers and network, but keep volumes)
```bash
docker-compose down
```

### Remove everything including volumes
```bash
docker-compose down -v
```

## Advanced Usage

### Building Just the Flask Image

```bash
docker build -t opentale:latest .
```

### Running Flask App Only (with external Ollama)

If you already have Ollama running elsewhere (e.g., on your host or another machine):

```bash
docker run -p 5000:5000 \
  -v $(pwd)/book_output:/app/book_output \
  -e LLM_URL=http://192.168.1.100:11434/v1 \
  opentale:latest
```

### Accessing Ollama from Host Machine

While containers are running, you can also use Ollama directly from your host:

```bash
# List available models
curl http://localhost:11434/api/tags

# Run a prompt
curl http://localhost:11434/api/generate -d '{
  "model": "gemma:latest",
  "prompt": "Hello, world!",
  "stream": false
}'
```

## Troubleshooting

### "Connection refused" error

**Issue**: Flask app can't reach Ollama
- **Check**: `docker-compose ps` - Is ollama container running?
- **Check**: `docker-compose logs ollama` - Are there errors in Ollama?
- **Solution**: Restart: `docker-compose restart`

### "Model not found" error

**Issue**: The model name doesn't exist on Ollama
- **Check**: `docker exec opentale-ollama ollama list`
- **Solution**: Pull the model first:
  ```bash
  docker exec opentale-ollama ollama pull gemma:latest
  ```
- Then update `LLM_MODEL` in docker-compose.yml and restart

### Slow first startup

**Issue**: First `docker-compose up` is very slow
- **Reason**: Ollama is downloading and initializing the model (can take 5-15 minutes depending on model size and internet speed)
- **Check**: `docker-compose logs ollama` to monitor progress
- **Tip**: Use a smaller model initially: `mistral:latest` (4GB) instead of `gemma:latest` (5GB)

### Out of disk space

**Issue**: Model download fails or containers won't start
- **Check**: `docker system df`
- **Solution**: Clean up unused Docker data:
  ```bash
  docker system prune -a
  docker volume prune
  ```

### Port already in use

**Issue**: "Address already in use" error on 5000 or 11434
- **Solution**: Specify different ports in docker-compose.yml:
  ```yaml
  services:
    web:
      ports:
        - "5001:5000"  # Use 5001 on host instead
    ollama:
      ports:
        - "11435:11434"  # Use 11435 on host instead
  ```

## Volume Persistence

### book_output Directory

All generated content (chapters, outlines, characters) is saved to `./book_output` on your host machine. This persists even if containers are removed.

To backup your work:
```bash
zip -r book_output_backup.zip book_output/
```

### Ollama Models

Models are stored in Docker named volume `ollama_data`. They persist across restarts:

```bash
# View volume details
docker volume inspect opentale_ollama_data

# Backup models
docker run --rm -v opentale_ollama_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/ollama_backup.tar.gz -C /data .
```

## Performance Tuning

### Memory and CPU Limits

By default, Docker uses available resources. To limit for safety:

```yaml
services:
  ollama:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 8G
        reservations:
          cpus: '1'
          memory: 4G
```

### GPU Acceleration (Optional)

If you have an NVIDIA GPU and want Ollama to use it:

```yaml
services:
  ollama:
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

Requires: NVIDIA Docker runtime installed

## Production Deployment

### Security Considerations

- The app has **no authentication** - don't expose to untrusted networks
- Add reverse proxy (nginx) with authentication for public deployment
- Use HTTPS/TLS termination
- Run behind a firewall

### Example: Production with Nginx

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:latest
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - web

  web:
    build: .
    depends_on:
      ollama:
        condition: service_healthy
    volumes:
      - ./book_output:/app/book_output

  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama

volumes:
  ollama_data:
```

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_URL` | `http://ollama:11434/v1` | Ollama API endpoint |
| `LLM_MODEL` | `gemma:latest` | Model to use |
| `LLM_TEMPERATURE` | `0.7` | Generation creativity (0.0-1.0) |
| `LLM_TIMEOUT` | `600` | Request timeout in seconds |
| `FLASK_ENV` | `production` | Flask environment |

## Getting Help

- Check logs: `docker-compose logs -f`
- Rebuild images: `docker-compose build --no-cache`
- Reset everything: `docker-compose down -v && docker-compose up`
