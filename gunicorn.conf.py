import os
import multiprocessing

# Bind (Fly.io/Heroku-like)
PORT = os.getenv("PORT") or os.getenv("BACKEND_PORT") or "9000"
bind = f"0.0.0.0:{PORT}"

# ASGI vs WSGI -> ODYSSAI_APP_TYPE=ASGI|WSGI
APP_TYPE = os.getenv("ODYSSAI_APP_TYPE", "ASGI").upper()
worker_class = "uvicorn.workers.UvicornWorker" if APP_TYPE == "ASGI" else "gthread"

# Concurrence
CPU = multiprocessing.cpu_count() or 2
workers = int(os.getenv("WEB_CONCURRENCY", max(2, CPU // 2)))
threads = int(os.getenv("WEB_THREADS", "4")) if worker_class == "gthread" else 1  # threads ignorés en ASGI

# Timeouts
timeout = int(os.getenv("WEB_TIMEOUT", "180"))
graceful_timeout = 30
keepalive = int(os.getenv("WEB_KEEPALIVE", "10"))

# Logs
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")

# Divers prod
proc_name = "odyssai"
preload_app = os.getenv("PRELOAD_APP", "true").lower() == "true"
max_requests = int(os.getenv("MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("MAX_REQUESTS_JITTER", "100"))
worker_tmp_dir = "/dev/shm"
