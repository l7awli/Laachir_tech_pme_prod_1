# gunicorn_config.py - Gunicorn server configuration
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
threads = 2
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "logs/access.log"
errorlog = "logs/error.log"
loglevel = "info"

# Development
reload = False
daemon = False

# SSL (optional)
# certfile = "/etc/ssl/certs/your-cert.pem"
# keyfile = "/etc/ssl/private/your-key.pem"

