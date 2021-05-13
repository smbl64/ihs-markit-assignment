from collections import namedtuple

from . import helpers

CommandContext = namedtuple(
    "CommandContext", ["message", "current_handler", "handlers_registry", "job_manager"]
)

command_registry = dict()


def handle_command(command_name: str, context: CommandContext) -> None:
    if command_name not in command_registry:
        context.handler.send(f"Unknown command: {command_name}")
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
        h.username
        for h in context.handlers_registry.all()
        if h != context.current_handler
    ]
    if users:
        message = "Online users: " + ", ".join(users)
    else:
        message = "No other user is connected."

    context.current_handler.send(message)


@command("msg")
def msg_command(context: CommandContext):
    other_user, _, message = context.message.partition(" ")
    handler = context.handlers_registry.find(other_user)
    if not handler:
        context.current_handler.send(f"User not found: {other_user}")

    if handler.send(message, sender=context.current_handler.username):
        context.current_handler.send(f"Message is delivered to {handler.username}")
    else:
        context.current_handler.send(f"Cannot deliver the message to {handler.username}")


@command("broadcast")
def broadcast_command(context: CommandContext):
    for other_handler in context.handlers_registry.all():
        if other_handler == context.current_handler:
            continue

        try:
            other_handler.send(context.message, sender=context.current_handler.username)
        except Exception:
            pass


@command("url")
def url_command(context: CommandContext):
    params_splitted = context.message.split(" ")
    if len(params_splitted) != 2:
        context.current_handler.send("Invalid url paramenters.")

    other_user, url = params_splitted
    handler = context.handlers_registry.find(other_user)
    if not handler:
        context.current_handler.send(f"User not found: {other_user}")
        return

    def callback(result, handler):
        if handler.send(f"resource_size({url}) = {result}"):
            context.current_handler.send(f"URL size is delivered to {handler.username}")
        else:
            context.current_handler.send(
                f"Cannot deliver url size to {handler.username}"
            )

    context.job_manager.enqueue_job(
        job_func=helpers.get_remote_resource_length,
        job_func_kwargs={"url": url},
        callback_func=callback,
        callback_func_kwargs={"handler": handler},
    )


@command("fib")
def fib_command(context: CommandContext):
    params_splitted = context.message.split(" ")
    if len(params_splitted) != 2:
        context.current_handler.send("Invalid fib paramenters.")

    other_user, number = params_splitted
    handler = context.handlers_registry.find(other_user)
    if not handler:
        context.current_handler.send(f"User not found: {other_user}")
        return

    number = int(number)

    def callback(result, handler):
        if handler.send(f"fib({number}) = {result}"):
            context.current_handler.send(
                f"Fib result is delivered to {handler.username}"
            )
        else:
            context.current_handler.send(
                f"Cannot deliver fib result to {handler.username}"
            )

    context.job_manager.enqueue_job(
        job_func=helpers.fibonacci,
        job_func_kwargs={"n": number},
        callback_func=callback,
        callback_func_kwargs={"handler": handler},
    )
