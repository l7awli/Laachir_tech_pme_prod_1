#!/bin/sh
# Use PORT injected by Railway/Render, fall back to 8000 for local Docker
PORT=${PORT:-8000}
exec gunicorn --bind "0.0.0.0:${PORT}" --workers 2 --threads 2 --timeout 120 wsgi:app
