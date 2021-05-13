import datetime
import logging
import random
import socket
import threading
from typing import Optional

from . import helpers, worker

logger = logging.getLogger(__name__)
job_manager: worker.JobManager = None


class HandlerRegistry:
    def __init__(self):
        self._handlers = []
        self._lock = threading.Lock()

    def register(self, handler):
        with self._lock:
            self._handlers.append(handler)

    def unregister(self, handler):
        with self._lock:
            self._handlers.remove(handler)

    def find(self, username: str) -> Optional["ClientHandler"]:
        for handler in self._handlers:
            if handler.username == username:
                return handler
        return None

    def all(self):
        return self._handlers


registry = HandlerRegistry()


class ClientHandler:
    def __init__(self, connection, username):
        self.connection = connection
        self.username = username

    def start(self):
        self.register_handler()
        thread = threading.Thread(target=self._loop, args=())
        thread.daemon = True
        thread.start()

    def register_handler(self) -> None:
        registry.register(self)

    def unregister_handler(self) -> None:
        registry.unregister(self)

    def _loop(self):
        self.send(f"Welcome! Your username is {self.username}")

        while True:
            data = self.connection.recv(1024)
            if len(data) == 0:
                self.unregister_handler()
                break

            self._handle_request(data)

    def _handle_request(self, data: bytes) -> None:
        data = data.decode("utf-8").strip()
        command, _, params = data.partition(" ")
        command = command.lower()

        if command not in {"w", "msg", "broadcast", "url", "fib"}:
            self.send(f"Invalid command: {command}")

        if command == "broadcast":
            self.handle_broadcast(params)

        if command == "w":
            self.handle_whois()

        if command == "msg":
            self.handle_msg(params)

        if command == "fib":
            self.handle_fib(params)

        if command == "url":
            self.handle_url(params)

    def handle_whois(self):
        users = [h.username for h in registry.all() if h != self]
        if users:
            message = "List of users: " + ", ".join(users)
        else:
            message = "No other user is connected."

        self.send(message)

    def handle_url(self, params):
        params_splitted = params.split(" ")
        if len(params_splitted) != 2:
            self.send("Invalid url paramenters.")

        other_user, url = params_splitted
        handler = registry.find(other_user)
        if not handler:
            self.send(f"User not found: {other_user}")
            return

        def callback(result, handler):
            handler.send(f"resource_size({url}) = {result}")

        job_manager.enqueue_job(
            job_func=helpers.get_remote_resource_length,
            job_func_kwargs={"url": url},
            callback_func=callback,
            callback_func_kwargs={"handler": handler},
        )

    def handle_fib(self, params) -> None:
        params_splitted = params.split(" ")
        if len(params_splitted) != 2:
            self.send("Invalid fib paramenters.")

        other_user, number = params_splitted
        handler = registry.find(other_user)
        if not handler:
            self.send(f"User not found: {other_user}")
            return

        number = int(number)

        def callback(result, handler):
            handler.send(f"fib({number}) = {result}")

        job_manager.enqueue_job(
            job_func=helpers.fibonacci,
            job_func_kwargs={"n": number},
            callback_func=callback,
            callback_func_kwargs={"handler": handler},
        )

    def handle_msg(self, message: str) -> None:
        other_user, _, message = message.partition(" ")
        handler = registry.find(other_user)
        if not handler:
            self.send(f"User not found: {other_user}")

        handler.send(message, sender=self.username)

    def handle_broadcast(self, message: str) -> None:
        for other_handler in registry.all():
            if other_handler == self:
                continue

            try:
                other_handler.send(message, sender=self.username)
            except Exception:
                pass

    def send(self, message: str, *, sender: str = None) -> None:
        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d %H:%M:%S.%f")

        if sender:
            message = f"[{timestamp}] {sender} {message}"
        else:
            message = f"[{timestamp}] {message}"

        if not message.endswith("\n"):
            message += "\n"

        self.connection.sendall(message.encode("utf-8"))


def get_next_username() -> str:
    return "u" + str(random.randint(1000, 9999))


def start():
    global job_manager
    job_manager = worker.JobManager()

    ip = "127.0.0.1"
    port = 12345
    logger.info("Binding to %s:%d", ip, port)
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((ip, port))
    server.listen(200)

    logger.info("Server started")

    while True:
        conn, addr = server.accept()
        username = get_next_username()
        logger.info("%s connected", username)

        handler = ClientHandler(conn, username)
        handler.start()

    server.close()
