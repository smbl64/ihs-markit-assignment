import datetime
import logging
import queue
import socket
import threading
from typing import Optional

from . import commands, worker

# A list of user ids for generating unique usernames.
# This list is finite, but I've chosen this approach for
# ease of testing. In production environment, a UUID or
# a timestamp should be used.
all_user_ids = queue.deque(range(1000, 10000))

logger = logging.getLogger(__name__)

job_manager: worker.JobManager = None


class ServerCommandContext(commands.CommandContext):
    def __init__(self, message, current_handler, handlers_registry, job_manager):
        self.message = message
        self.current_handler = current_handler
        self.handlers_registry = handlers_registry
        self.job_manager = job_manager

    def get_message(self):
        return self.message

    def get_all_usernames(self):
        return [h.username for h in self.handlers_registry.all()]

    def get_current_username(self):
        return self.current_handler.username

    def send_message(self, message: str) -> bool:
        return self.current_handler.send(message)

    def send_message_to_other_user(
        self, receipient: str, message: str, *, sender: str = None
    ) -> bool:
        handler = self.handlers_registry.find(receipient)
        if not handler:
            return False

        return handler.send(message, sender=sender)

    def is_user_online(self, username: str) -> bool:
        return self.handlers_registry.find(username) is not None

    def run_in_background(
        self, *, job_func, job_func_kwargs, callback_func, callback_func_kwargs
    ) -> None:
        self.job_manager.enqueue_job(
            job_func=job_func,
            job_func_kwargs=job_func_kwargs,
            callback_func=callback_func,
            callback_func_kwargs=callback_func_kwargs,
        )


class HandlerRegistry:
    """
    A class which keeps track of online users and their handler classes.
    """

    def __init__(self):
        self._handlers = dict()
        self._lock = threading.Lock()

    def register(self, handler):
        with self._lock:
            self._handlers[handler.username] = handler

    def unregister(self, handler):
        with self._lock:
            self._handlers.pop(handler.username)

    def find(self, username: str) -> Optional["ClientHandler"]:
        return self._handlers.get(username, None)

    def all(self):
        return self._handlers.values()


registry = HandlerRegistry()


class ClientHandler:
    def __init__(self, connection, username):
        self.connection = connection
        self.username = username

    def start(self):
        registry.register(self)
        thread = threading.Thread(target=self._loop, args=())
        thread.daemon = True
        thread.start()

    def _loop(self):
        self.send(f"Welcome! Your username is {self.username}")

        while True:
            data = self.connection.recv(1024)
            if len(data) == 0:
                self.connection.close()
                registry.unregister(self)
                self.unregister_handler()
                break

            self._handle_request(data)

    def _handle_request(self, data: bytes) -> None:
        data = data.decode("utf-8").strip()
        command_name, _, message = data.partition(" ")
        command_name = command_name.lower()

        context = ServerCommandContext(message, self, registry, job_manager)
        commands.handle_command(command_name, context)

    def send(self, message: str, *, sender: str = None) -> bool:
        # Check to see if socket is already closed
        if self.connection.fileno() < 0:
            return False

        now = datetime.datetime.now()
        timestamp = now.strftime("%Y%m%d %H:%M:%S.%f")

        if sender:
            message = f"[{timestamp}] {sender} {message}"
        else:
            message = f"[{timestamp}] {message}"

        if not message.endswith("\n"):
            message += "\n"

        return self.connection.send(message.encode("utf-8")) > 0


def get_next_username() -> str:
    return "u" + str(all_user_ids.popleft())


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
