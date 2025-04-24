# Basic (your current version - works for development)
web: uvicorn app:app --host 0.0.0.0 --port $PORT --workers 1

# Production-Ready Version (recommended)
web: gunicorn -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY:-4} -b :${PORT:-8000} --max-requests 1000 --max-requests-jitter 50 --timeout 120 app:app

# Worker Processes (optional - for background tasks)
worker: python -m worker.tasks

# Monitoring (optional)
healthcheck: python -m healthcheck
