from abc import ABC, abstractmethod

from . import helpers


class CommandContext(ABC):
    @abstractmethod
    def get_message(self):
        """
        Get the supplying message that is received with the command.
        """
        pass

    @abstractmethod
    def get_all_usernames(self):
        """
        List all online usernames.
        """
        pass

    @abstractmethod
    def get_current_username(self):
        """
        Get current username.
        """
        pass

    @abstractmethod
    def send_message(self, message: str) -> bool:
        """
        Send a message to the current user.
        """
        pass

    @abstractmethod
    def send_message_to_other_user(
        self, receipient: str, message: str, *, sender: str = None
    ) -> bool:
        """
        Send a message to another user.

        Optionally, the sender can also be specified.
        """
        pass

    @abstractmethod
    def is_user_online(self, username: str) -> bool:
        """
        Check whether a specific user is online.
        """
        pass

    @abstractmethod
    def run_in_background(
        self, *, job_func, job_func_kwargs, callback_func, callback_func_kwargs
    ) -> None:
        """
        Schedule a job to be run in the background.

        :param job_func: The function to call for the job.
        :param job_func_kwargs: An optional dictionary representing the kwargs for
            the job function.
        :param callback_func: The function to call when the job is finished.
        :param callback_func_kwargs: An optional dictionary of kwargs to send to the
            callback function.
        """
        pass


command_registry = dict()


def handle_command(command_name: str, context: CommandContext) -> None:
    if command_name not in command_registry:
        context.send_message(f"Unknown command: {command_name}")
        return

    command_registry[command_name](context)


def command(command_name):
    """
    A decorator to mark functions as command handlers and register
    them in the registry.
    """
    def wrapper(func):
        command_registry[command_name] = func

        return func

    return wrapper


@command("w")
def whois_command(context: CommandContext):
    users = [
        u for u in context.get_all_usernames() if u != context.get_current_username()
    ]

    if users:
        message = "Online users: " + ", ".join(users)
    else:
        message = "No other user is connected."

    context.send_message(message)


@command("msg")
def msg_command(context: CommandContext):
    other_user, _, message = context.get_message().partition(" ")
    if not context.is_user_online(other_user):
        context.current_handler.send(f"User not found: {other_user}")

    if context.send_message_to_other_user(
        other_user, message, sender=context.get_current_username()
    ):
        context.send_message(f"Message is delivered to {other_user}")
    else:
        context.send_message(f"Cannot deliver the message to {other_user}")


@command("broadcast")
def broadcast_command(context: CommandContext):
    for username in context.get_all_usernames():
        if username == context.get_current_username():
            continue

        try:
            context.send_message_to_other_user(
                username, context.get_message(), sender=context.get_current_username()
            )
        except Exception:
            pass


@command("url")
def url_command(context: CommandContext):
    params_splitted = context.get_message().split(" ")
    if len(params_splitted) != 2:
        context.send_message("Invalid url paramenters.")
        return

    other_user, url = params_splitted
    if not context.is_user_online(other_user):
        context.send_message(f"User not found: {other_user}")
        return

    def callback(result, other_user):
        if context.send_message_to_other_user(
            other_user, f"resource_size({url}) = {result}"
        ):
            context.send_message(f"URL size is delivered to {other_user}")
        else:
            context.send_message(f"Cannot deliver url size to {other_user}")

    context.run_in_background(
        job_func=helpers.get_remote_resource_length,
        job_func_kwargs={"url": url},
        callback_func=callback,
        callback_func_kwargs={"other_user": other_user},
    )


@command("fib")
def fib_command(context: CommandContext):
    params_splitted = context.get_message().split(" ")
    if len(params_splitted) != 2:
        context.send_message("Invalid fib paramenters.")
        return

    other_user, number = params_splitted
    if not context.is_user_online(other_user):
        context.send_message(f"User not found: {other_user}")
        return

    number = int(number)

    def callback(result, other_user):
        if context.send_message_to_other_user(other_user, f"fib({number}) = {result}"):
            context.send_message(f"Fib result is delivered to {other_user}")
        else:
            context.send_message(f"Cannot deliver fib result to {other_user}")

    context.job_manager.enqueue_job(
        job_func=helpers.fibonacci,
        job_func_kwargs={"n": number},
        callback_func=callback,
        callback_func_kwargs={"other_user": other_user},
    )
