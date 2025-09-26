# Gunicorn config for BlockShelf
import multiprocessing
import os

bind = "unix:/run/blockshelf/blockshelf.sock"  # matches systemd & nginx
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
threads = int(os.getenv("GUNICORN_THREADS", 1))
timeout = int(os.getenv("GUNICORN_TIMEOUT", 60))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", 30))
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 0))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", 0))
accesslog = os.getenv("GUNICORN_ACCESSLOG", "-")  # "-" = stdout
errorlog = os.getenv("GUNICORN_ERRORLOG", "-")
loglevel = os.getenv("GUNICORN_LOGLEVEL", "info")
