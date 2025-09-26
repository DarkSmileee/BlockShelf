import multiprocessing

# Use a unix socket for Nginx
bind = "unix:/run/blockshelf/blockshelf.sock"

# Reasonable defaults; tune as needed
workers = multiprocessing.cpu_count() * 2 + 1
timeout = 60
graceful_timeout = 30
keepalive = 5

# Logs to systemd/journal
accesslog = "-"
errorlog = "-"
loglevel = "info"
