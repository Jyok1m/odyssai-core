import os

# Bind to all interfaces and use port from environment or default to 8080
bind = f"0.0.0.0:{os.environ.get('BACKEND_PORT', 9000)}"

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
