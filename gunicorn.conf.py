"""
Gunicorn configuration for BlockShelf.

All settings can be overridden via environment variables for flexibility
across different deployment environments (development, staging, production).

Environment Variables:
    GUNICORN_BIND - Bind address (default: unix socket)
    GUNICORN_WORKERS - Number of worker processes (default: CPU * 2 + 1)
    GUNICORN_WORKER_CLASS - Worker class (default: sync)
    GUNICORN_TIMEOUT - Worker timeout in seconds (default: 60)
    GUNICORN_GRACEFUL_TIMEOUT - Graceful shutdown timeout (default: 30)
    GUNICORN_KEEPALIVE - Keep-alive timeout (default: 5)
    GUNICORN_MAX_REQUESTS - Max requests per worker before restart (default: 1000)
    GUNICORN_MAX_REQUESTS_JITTER - Random jitter for max_requests (default: 50)
    GUNICORN_LOG_LEVEL - Logging level (default: info)
    GUNICORN_ACCESS_LOG - Access log file (default: -)
    GUNICORN_ERROR_LOG - Error log file (default: -)
"""

import multiprocessing
import os


def get_env_int(key: str, default: int) -> int:
    """Get integer from environment variable with fallback."""
    try:
        return int(os.getenv(key, default))
    except (ValueError, TypeError):
        return default


def get_env_str(key: str, default: str) -> str:
    """Get string from environment variable with fallback."""
    return os.getenv(key, default)


# =============================================================================
# Server Socket
# =============================================================================

# Bind address - can be TCP or Unix socket
# Examples:
#   TCP: 0.0.0.0:8000 or 127.0.0.1:8000
#   Unix: unix:/run/blockshelf/blockshelf.sock
bind = get_env_str('GUNICORN_BIND', 'unix:/run/blockshelf/blockshelf.sock')

# Backlog - number of pending connections
backlog = get_env_int('GUNICORN_BACKLOG', 2048)

# =============================================================================
# Worker Processes
# =============================================================================

# Number of worker processes
# Default: (CPU cores * 2) + 1
# Formula based on Gunicorn recommendations for I/O-bound applications
workers = get_env_int('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1)

# Worker class
# Options: sync, gevent, eventlet, tornado, gthread
# Default: sync (good for CPU-bound, use gevent/eventlet for I/O-bound)
worker_class = get_env_str('GUNICORN_WORKER_CLASS', 'sync')

# Threads per worker (only for gthread worker class)
threads = get_env_int('GUNICORN_THREADS', 1)

# Worker connections (for async workers like gevent)
worker_connections = get_env_int('GUNICORN_WORKER_CONNECTIONS', 1000)

# =============================================================================
# Worker Lifecycle
# =============================================================================

# Worker timeout - workers silent for more than this are killed and restarted
# Increase if you have long-running requests
timeout = get_env_int('GUNICORN_TIMEOUT', 60)

# Graceful timeout - time to wait for workers to finish during graceful shutdown
graceful_timeout = get_env_int('GUNICORN_GRACEFUL_TIMEOUT', 30)

# Keep-alive - seconds to wait for requests on a Keep-Alive connection
keepalive = get_env_int('GUNICORN_KEEPALIVE', 5)

# Max requests per worker before restart (prevents memory leaks)
# Set to 0 to disable
max_requests = get_env_int('GUNICORN_MAX_REQUESTS', 1000)

# Random jitter added to max_requests (prevents all workers restarting at once)
max_requests_jitter = get_env_int('GUNICORN_MAX_REQUESTS_JITTER', 50)

# =============================================================================
# Logging
# =============================================================================

# Access log
# Use '-' for stdout, or a file path
accesslog = get_env_str('GUNICORN_ACCESS_LOG', '-')

# Error log
# Use '-' for stderr, or a file path
errorlog = get_env_str('GUNICORN_ERROR_LOG', '-')

# Log level
# Options: debug, info, warning, error, critical
loglevel = get_env_str('GUNICORN_LOG_LEVEL', 'info')

# Access log format
# See: https://docs.gunicorn.org/en/stable/settings.html#access-log-format
access_log_format = get_env_str(
    'GUNICORN_ACCESS_LOG_FORMAT',
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'
)

# =============================================================================
# Process Naming
# =============================================================================

# Process name prefix (shows in ps/top)
proc_name = get_env_str('GUNICORN_PROC_NAME', 'blockshelf')

# =============================================================================
# Server Mechanics
# =============================================================================

# Daemonize - run in background (usually handled by systemd)
daemon = False

# PID file location
pidfile = get_env_str('GUNICORN_PIDFILE', '/run/blockshelf/blockshelf.pid')

# User/group to run workers as (None = don't change)
user = get_env_str('GUNICORN_USER', None)
group = get_env_str('GUNICORN_GROUP', None)

# Umask for file creation
umask = get_env_int('GUNICORN_UMASK', 0)

# Working directory
chdir = get_env_str('GUNICORN_CHDIR', os.getcwd())

# =============================================================================
# Server Hooks
# =============================================================================

def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting BlockShelf with Gunicorn")
    server.log.info(f"Workers: {workers}, Bind: {bind}")
    server.log.info(f"Worker class: {worker_class}, Timeout: {timeout}s")


def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading BlockShelf workers")


def when_ready(server):
    """Called just after the server is started."""
    server.log.info("BlockShelf is ready to accept connections")


def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.debug(f"Worker {worker.pid} spawned")


def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Forking new master process")


def worker_int(worker):
    """Called just after a worker received the SIGINT or SIGQUIT signal."""
    worker.log.info(f"Worker {worker.pid} received INT/QUIT signal")


def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.warning(f"Worker {worker.pid} aborted (timeout?)")


def pre_request(worker, req):
    """Called just before a worker processes a request."""
    pass


def post_request(worker, req, environ, resp):
    """Called after a worker processes a request."""
    pass


def child_exit(server, worker):
    """Called just after a worker has been exited."""
    server.log.debug(f"Worker {worker.pid} exited")


def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    pass


def nworkers_changed(server, new_value, old_value):
    """Called just after num_workers has been changed."""
    server.log.info(f"Workers changed from {old_value} to {new_value}")


def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("Shutting down BlockShelf")


# =============================================================================
# SSL (if using HTTPS directly with Gunicorn - usually handled by Nginx)
# =============================================================================

# SSL certificate file
keyfile = get_env_str('GUNICORN_KEYFILE', None)

# SSL key file
certfile = get_env_str('GUNICORN_CERTFILE', None)

# SSL version
ssl_version = get_env_str('GUNICORN_SSL_VERSION', None)

# SSL ciphers
ciphers = get_env_str('GUNICORN_CIPHERS', None)

# =============================================================================
# Security
# =============================================================================

# Limit request line size (prevents DOS)
limit_request_line = get_env_int('GUNICORN_LIMIT_REQUEST_LINE', 4094)

# Limit request header field size
limit_request_field_size = get_env_int('GUNICORN_LIMIT_REQUEST_FIELD_SIZE', 8190)

# Limit number of request header fields
limit_request_fields = get_env_int('GUNICORN_LIMIT_REQUEST_FIELDS', 100)

# =============================================================================
# Performance Tuning
# =============================================================================

# Preload application code before worker processes are forked
# Saves RAM but makes reload harder (set to True for production)
preload_app = get_env_str('GUNICORN_PRELOAD_APP', 'false').lower() in ('true', '1', 'yes')

# Enable sendfile (can improve performance for static files)
sendfile = get_env_str('GUNICORN_SENDFILE', 'true').lower() in ('true', '1', 'yes')

# Reuse TCP port (can improve restart performance)
reuse_port = get_env_str('GUNICORN_REUSE_PORT', 'false').lower() in ('true', '1', 'yes')
