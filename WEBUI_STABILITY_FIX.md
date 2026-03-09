# Web UI Stability Fix - March 9, 2026

## Problem
The web UI container kept crashing/going down repeatedly due to the following issue:

**Root Cause**: Docker Compose dependency chain deadlock
- The web container had a strict dependency: `depends_on: ollama: condition: service_healthy`
- The ollama container's health check was unreliable and would timeout
- When ollama didn't pass health checks, docker-compose would fail to start web
- This caused the web UI to never come up or repeatedly crash

## Solution Implemented

### 1. **Fixed docker-compose.yml** (Line 27-29)
Changed from:
```yaml
depends_on:
  ollama:
    condition: service_healthy
```

To:
```yaml
depends_on:
  - ollama
```

**Impact**: Web container now starts immediately without waiting for ollama health check. Flask handles LLM connection errors gracefully.

### 2. **Enhanced web_app.py**
- Added startup logging to stderr for debugging
- Added `@app.before_request` startup handler to initialize state files on first request
- Removed `debug=True` which caused auto-reloader issues
- Changed to production mode: `debug=False, use_reloader=False, threaded=True`

**Impact**: App starts consistently, handles initialization errors gracefully, no auto-reload crashes.

## Verification
✅ Containers start and stay up (tested 5+ times)
✅ Web UI responsive at http://localhost:5000
✅ State files initialize properly
✅ Flask logs show clean startup

## Testing
```bash
# Verify web UI is up
curl http://localhost:5000/

# Check logs
docker logs opentale-web
docker logs opentale-ollama

# Test stability (all should succeed)
for i in {1..5}; do curl -s http://localhost:5000/ > /dev/null && echo "✓ OK" || echo "✗ FAIL"; sleep 2; done
```

## Key Changes
- **docker-compose.yml**: Removed strict ollama health check dependency
- **web_app.py**: Added startup logging, graceful initialization, removed debug mode
- **Dockerfile**: No changes needed

## Files Modified
1. `docker-compose.yml` - Line 27-29
2. `web_app.py` - Lines 1-27 (startup logging), 77-91 (startup handler), 1380-1382 (main block)

## Current Status
✅ **FIXED** - Web UI stable and ready for testing
- ollama-web: Up and healthy
- opentale-web: Up and responsive
- Ready for end-to-end testing
