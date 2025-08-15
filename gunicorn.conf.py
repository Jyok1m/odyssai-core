import os

# Bind to all interfaces and use port from environment or default to 9000
# Fly.io sets PORT environment variable, fallback to BACKEND_PORT or 9000
port = os.environ.get('PORT', os.environ.get('BACKEND_PORT', 9000))
bind = f"0.0.0.0:{port}"

# Number of worker processes
workers = 2

# Worker class
worker_class = "sync"

# Timeout for requests
timeout = 30

# Keep alive
keepalive = 2

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

# Process naming
proc_name = "odyssai"

# Preload application
preload_app = True
