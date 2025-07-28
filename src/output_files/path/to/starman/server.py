import os
import sys
import socket
import signal
import time
import errno
import pwd
import grp
from .worker import Worker

try:
    import setproctitle
except ImportError:
    setproctitle = None

class Server:
    SIGNALS = {
        signal.SIGHUP: 'handle_hup',
        signal.SIGQUIT: 'handle_quit',
        signal.SIGTERM: 'handle_quit',
        signal.SIGINT: 'handle_quit',
        signal.SIGTTIN: 'handle_ttin',
        signal.SIGTTOU: 'handle_ttou',
    }

    def __init__(self, app, options):
        self.app = app
        self.options = options
        self.sockets = []
        self.workers = {}
        self.running = True
        self.worker_count = self.options.workers
        self.pid = os.getpid()

        # Signal flags
        self._hup_received = False
        self._quit_received = False
        self._ttin_received = False
        self._ttou_received = False

    def run(self):
        self.set_proc_title("master")
        self.setup_sockets()
        self.setup_privileges()

        if self.options.preload_app:
            print(f"[{self.pid}] Pre-loading application.")
            # App is already loaded by cli.py
            pass
        
        self.setup_signal_handlers()
        self.master_loop()
        print(f"[{self.pid}] Master process exiting.")
        self.close_sockets()

    def setup_sockets(self):
        server_starter_fd = os.environ.get('SERVER_STARTER_PORT')
        if server_starter_fd:
            host, port, fd = server_starter_fd.split('=')
            print(f"[{self.pid}] Binding to socket from server_starter (fd: {fd})")
            s = socket.fromfd(int(fd), socket.AF_INET, socket.SOCK_STREAM)
            s.listen(self.options.backlog)
            self.sockets.append(s)
            return

        for listen_addr in self.options.listen:
            if ':' in listen_addr:
                host, port = listen_addr.rsplit(':', 1)
                addr = (host, int(port))
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            else:
                addr = listen_addr
                try:
                    os.remove(addr)
                except OSError as e:
                    if e.errno != errno.ENOENT:
                        raise
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)

            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(addr)
            s.listen(self.options.backlog)
            self.sockets.append(s)
            print(f"[{self.pid}] Listening at {listen_addr} ({s.fileno()})")

    def setup_privileges(self):
        if self.options.group:
            try:
                gid = int(self.options.group)
            except ValueError:
                gid = grp.getgrnam(self.options.group).gr_gid
            os.setgid(gid)
            print(f"[{self.pid}] Switched to group {self.options.group}")
        if self.options.user:
            try:
                uid = int(self.options.user)
            except ValueError:
                uid = pwd.getpwnam(self.options.user).pw_uid
            os.setuid(uid)
            print(f"[{self.pid}] Switched to user {self.options.user}")

    def setup_signal_handlers(self):
        for sig, handler_name in self.SIGNALS.items():
            signal.signal(sig, getattr(self, handler_name))

    def master_loop(self):
        self.spawn_workers()
        while self.running:
            try:
                self.check_signals()
                self.reap_workers()
                self.maintain_worker_count()
                time.sleep(1)
            except InterruptedError:
                continue
            except KeyboardInterrupt:
                self.running = False

    def check_signals(self):
        if self._hup_received:
            self._hup_received = False
            self.graceful_restart()
        if self._quit_received:
            self._quit_received = False
            self.running = False
        if self._ttin_received:
            self._ttin_received = False
            self.worker_count += 1
            print(f"[{self.pid}] Increasing worker count to {self.worker_count}")
        if self._ttou_received:
            self._ttou_received = False
            if self.worker_count > 1:
                self.worker_count -= 1
                print(f"[{self.pid}] Decreasing worker count to {self.worker_count}")

    def graceful_restart(self):
        print(f"[{self.pid}] HUP received. Restarting workers.")
        self.kill_workers(signal.SIGTERM)
        self.reap_workers(block=True)
        self.spawn_workers()

    def kill_workers(self, sig):
        for pid in list(self.workers.keys()):
            try:
                os.kill(pid, sig)
            except OSError as e:
                if e.errno == errno.ESRCH:
                    self.workers.pop(pid, None)

    def spawn_workers(self):
        while len(self.workers) < self.worker_count:
            self.spawn_worker()

    def spawn_worker(self):
        pid = os.fork()
        if pid == 0:  # Child
            self.set_proc_title("worker")
            try:
                worker = Worker(self.app, self.options, self.sockets)
                worker.run()
            except Exception as e:
                print(f"Worker {os.getpid()} exited with error: {e}", file=sys.stderr)
            finally:
                os._exit(0)
        else:  # Parent
            self.workers[pid] = time.time()
            print(f"[{self.pid}] Spawned worker {pid}")

    def reap_workers(self, block=False):
        options = 0 if not block else os.WNOHANG
        try:
            while True:
                pid, status = os.waitpid(-1, options)
                if pid == 0 and not block:
                    break
                if pid in self.workers:
                    del self.workers[pid]
                    print(f"[{self.pid}] Reaped worker {pid} (status: {status})")
                if block and not self.workers:
                    break
        except OSError as e:
            if e.errno != errno.ECHILD:
                raise

    def maintain_worker_count(self):
        diff = self.worker_count - len(self.workers)
        if diff > 0:
            for _ in range(diff):
                self.spawn_worker()
        elif diff < 0:
            pids_to_kill = list(self.workers.keys())[:abs(diff)]
            for pid in pids_to_kill:
                self.kill_workers(signal.SIGTERM)
    
    def close_sockets(self):
        for s in self.sockets:
            s.close()
    
    def set_proc_title(self, role):
        if setproctitle and self.options.set_proctitle:
            setproctitle.setproctitle(f"starman: {role} process")
            
    # Signal handlers
    def handle_hup(self, sig, frame):
        self._hup_received = True

    def handle_quit(self, sig, frame):
        self._quit_received = True

    def handle_ttin(self, sig, frame):
        self._ttin_received = True
    
    def handle_ttou(self, sig, frame):
        self._ttou_received = True
