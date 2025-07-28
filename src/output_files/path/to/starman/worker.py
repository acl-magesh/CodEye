import os
import sys
import socket
import errno
import time
import io
from email.utils import formatdate
from httptools import HttpRequestParser
from httptools.parser import HttpParserError

try:
    import setproctitle
except ImportError:
    setproctitle = None

class RequestHandler:
    def __init__(self, app, client_sock, client_addr, options, sockets):
        self.app = app
        self.client = client_sock
        self.addr = client_addr
        self.options = options
        self.sockets = sockets
        self.parser = HttpRequestParser(self)
        self.headers = []
        self.body = io.BytesIO()
        self.environ = {}
        self.response = {}

    def on_message_begin(self):
        self.headers = []
        self.body = io.BytesIO()
        self.environ = {
            'wsgi.version': (1, 0),
            'wsgi.url_scheme': 'http', # TODO: SSL
            'wsgi.input': self.body,
            'wsgi.errors': sys.stderr,
            'wsgi.multithread': False,
            'wsgi.multiprocess': True,
            'wsgi.run_once': False,
            'SERVER_SOFTWARE': f'Starman/{self.options.version}',
            'REQUEST_METHOD': '',
            'SCRIPT_NAME': '',
            'PATH_INFO': '',
            'QUERY_STRING': '',
            'SERVER_NAME': self.client.getsockname()[0],
            'SERVER_PORT': str(self.client.getsockname()[1]),
            'REMOTE_ADDR': self.addr[0],
            'REMOTE_PORT': str(self.addr[1]),
            'wsgix.informational': self.write_informational,
        }

    def on_url(self, url):
        self.environ['RAW_URI'] = url.decode('latin-1')
        path, _, query = url.partition(b'?')
        self.environ['PATH_INFO'] = path.decode('latin-1')
        self.environ['QUERY_STRING'] = query.decode('latin-1')

    def on_header(self, name, value):
        name = name.decode('latin-1').upper().replace('-', '_')
        if name not in ('CONTENT_TYPE', 'CONTENT_LENGTH'):
            name = f"HTTP_{name}"
        self.environ[name] = value.decode('latin-1')
        self.headers.append((name.replace('_', '-'), value))

    def on_body(self, body):
        self.body.write(body)

    def on_headers_complete(self):
        self.environ['REQUEST_METHOD'] = self.parser.get_method().decode('latin-1')
        
        # Handle Expect: 100-continue
        if self.environ.get('HTTP_EXPECT', '').lower() == '100-continue':
            self.client.sendall(b'HTTP/1.1 100 Continue\r\n\r\n')

    def on_message_complete(self):
        self.body.seek(0)
        self.handle_request()

    def handle_request(self):
        try:
            resp_iter = self.app(self.environ, self.start_response)
            self.write_response(resp_iter)
        except Exception:
            # TODO: Better error handling
            exc_info = sys.exc_info()
            if not self.response:
                self.start_response("500 Internal Server Error", [])
            self.write_response([b"Internal Server Error"])
            print(f"Error handling request: {exc_info}", file=sys.stderr)
        finally:
            if hasattr(resp_iter, 'close'):
                resp_iter.close()

    def start_response(self, status, headers, exc_info=None):
        if exc_info:
            try:
                if self.response:
                    raise exc_info[1].with_traceback(exc_info[2])
            finally:
                exc_info = None
        elif self.response:
            raise AssertionError("start_response called a second time without exc_info")

        self.response = {"status": status, "headers": headers}
        
        # Return a write callable, though we don't use it in this simple model
        return self.client.sendall

    def write_informational(self, status_code, headers):
        status_text = "Informational" # This is a simplification
        lines = [f"HTTP/1.1 {status_code} {status_text}"]
        for name, value in headers:
            lines.append(f"{name}: {value}")
        data = "\r\n".join(lines).encode('latin-1') + b'\r\n\r\n'
        self.client.sendall(data)

    def write_response(self, resp_iter):
        status = self.response['status']
        headers = self.response['headers']
        
        # Add required headers
        has_cl = any(h[0].lower() == 'content-length' for h in headers)
        has_date = any(h[0].lower() == 'date' for h in headers)
        
        if not has_date:
            headers.append(('Date', formatdate(time.time(), usegmt=True)))

        headers.append(('Server', f'Starman/{self.options.version}'))

        # Prepare headers for sending
        header_data = [f"HTTP/1.1 {status}".encode('latin-1')]
        for name, value in headers:
            header_data.append(f"{name}: {value}".encode('latin-1'))
        
        self.client.sendall(b'\r\n'.join(header_data) + b'\r\n\r\n')

        # Send body
        for chunk in resp_iter:
            if chunk:
                self.client.sendall(chunk)

        # If no content-length, we can't do keep-alive unless chunked
        # This implementation is simplified and doesn't do response chunking.

    def handle(self):
        try:
            while True:
                data = self.client.recv(65536)
                if not data:
                    break
                try:
                    self.parser.feed_data(data)
                except HttpParserError as e:
                    print(f"HTTP parse error: {e}", file=sys.stderr)
                    # Simplified: just close connection on parse error
                    break
                
                # Simplified keep-alive: break after one request if disabled
                if self.options.disable_keepalive:
                    break
        except socket.error as e:
            if e.errno not in (errno.EPIPE, errno.ECONNRESET):
                print(f"Socket error: {e}", file=sys.stderr)
        finally:
            self.client.close()

class Worker:
    def __init__(self, app, options, sockets):
        self.app = app
        self.options = options
        self.sockets = sockets
        self.requests_processed = 0
        self.pid = os.getpid()

    def run(self):
        if not self.options.preload_app:
            # This is where the app would be loaded per-worker
            pass
        
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        
        print(f"[{self.pid}] Worker started.")

        while self.requests_processed < self.options.max_requests:
            try:
                client, addr = self.sockets[0].accept() # simplified to one socket
                self.requests_processed += 1
                handler = RequestHandler(self.app, client, addr, self.options, self.sockets)
                handler.handle()
            except socket.error as e:
                if e.errno in (errno.EAGAIN, errno.ECONNABORTED, errno.EPROTO):
                    continue
                raise

        print(f"[{self.pid}] Worker exiting (max requests reached).")
