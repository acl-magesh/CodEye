import argparse
import os
import sys
import importlib
from .server import Server
from . import __version__

def load_app(app_uri):
    """Loads a WSGI application from a URI string like 'module:variable'."""
    try:
        module_str, app_str = app_uri.split(":", 1)
    except ValueError:
        raise ValueError("Application URI must be in the format 'module:variable'")

    try:
        module = importlib.import_module(module_str)
        app = getattr(module, app_str)
        return app
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Could not load application '{app_uri}': {e}")

def main():
    parser = argparse.ArgumentParser(
        description="Starman: A high-performance preforking WSGI server.",
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument('app_uri', help='WSGI application URI (e.g., myapp:app)')
    parser.add_argument('-l', '--listen', action='append',
                        help='Listen on a TCP host:port or a UNIX socket path. '
                             'Can be specified multiple times. Defaults to 0.0.0.0:5000.')
    parser.add_argument('--host', default='0.0.0.0',
                        help='Host to bind (default: 0.0.0.0). Deprecated: use --listen.')
    parser.add_argument('--port', type=int, default=5000,
                        help='Port to bind (default: 5000). Deprecated: use --listen.')
    parser.add_argument('-w', '--workers', type=int, default=5,
                        help='Number of worker processes (default: 5).')
    parser.add_argument('--preload-app', action='store_true',
                        help='Load application in master process before forking.')
    parser.add_argument('--max-requests', type=int, default=1000,
                        help='Max requests a worker will process before restarting (default: 1000).')
    parser.add_argument('--timeout', type=int, default=30,
                        help='Worker timeout in seconds (default: 30).')
    parser.add_argument('--keepalive-timeout', type=int, default=5,
                        help='Keep-alive connection timeout (default: 5).')
    parser.add_argument('--read-timeout', type=int, default=5,
                        help='Timeout for reading a request from a new connection (default: 5).')
    parser.add_argument('--disable-keepalive', action='store_true', help='Disable keep-alive connections.')
    parser.add_argument('--backlog', type=int, default=1024, help='Listen backlog size (default: 1024).')
    parser.add_argument('--user', help='Switch to user after binding port.')
    parser.add_argument('--group', help='Switch to group after binding port.')
    parser.add_argument('--pid', help='Path to PID file.')
    parser.add_argument('--error-log', help='Path to error log file.')
    parser.add_argument('--daemonize', action='store_true', help='Daemonize the server process.')
    parser.add_argument('--disable-proctitle', action='store_false', dest='set_proctitle',
                        help='Disable setting process titles.')
    parser.add_argument('-v', '--version', action='version', version=f'Starman {__version__}')

    args = parser.parse_args()

    if not args.listen:
        args.listen = [f"{args.host}:{args.port}"]

    if args.daemonize:
        if os.fork() != 0:
            os._exit(0)
        os.setsid()
        if os.fork() != 0:
            os._exit(0)
        
        # Redirect stdio
        sys.stdout.flush()
        sys.stderr.flush()
        with open(os.devnull, 'rb') as dn:
            os.dup2(dn.fileno(), sys.stdin.fileno())
        
        log_path = args.error_log if args.error_log else os.devnull
        log_fd = open(log_path, 'ab')
        os.dup2(log_fd.fileno(), sys.stdout.fileno())
        os.dup2(log_fd.fileno(), sys.stderr.fileno())

    if args.pid:
        with open(args.pid, 'w') as f:
            f.write(str(os.getpid()))

    # Setting PLACK_ENV to deployment is a Starman tradition
    os.environ.setdefault('STARMAN_ENV', 'deployment')

    try:
        app = load_app(args.app_uri)
    except (ValueError, ImportError) as e:
        sys.stderr.write(f"Error: {e}\n")
        sys.exit(1)

    server = Server(app, args)
    server.run()

if __name__ == '__main__':
    main()
